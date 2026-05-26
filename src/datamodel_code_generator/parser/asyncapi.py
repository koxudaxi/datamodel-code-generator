"""AsyncAPI specification parser.

Extracts AsyncAPI message schemas and delegates Schema Object handling to the
OpenAPI/JSON Schema parser stack.
"""

from __future__ import annotations

import re
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from typing_extensions import Unpack

from datamodel_code_generator import Error, YamlValue, load_data, snooper_to_methods
from datamodel_code_generator.deprecations import warn_deprecated
from datamodel_code_generator.enums import AsyncAPIVersion
from datamodel_code_generator.parser.avro import convert_avro_schema_data
from datamodel_code_generator.parser.jsonschema import get_model_by_path, unescape_json_pointer_segment
from datamodel_code_generator.parser.openapi import OpenAPIParser
from datamodel_code_generator.reference import is_url

if TYPE_CHECKING:
    from collections.abc import Iterator
    from urllib.parse import ParseResult

    from datamodel_code_generator._types import AsyncAPIParserConfigDict
    from datamodel_code_generator.config import AsyncAPIParserConfig
    from datamodel_code_generator.parser.schema_version import OpenAPISchemaFeatures


OPERATION_NAMES: tuple[str, ...] = ("publish", "subscribe")
NAME_PART_PATTERN = re.compile(r"[A-Za-z0-9]+")
ASYNCAPI_SCHEMA_FORMATS: frozenset[str] = frozenset({
    "application/vnd.aai.asyncapi",
    "application/vnd.aai.asyncapi+json",
    "application/vnd.aai.asyncapi+yaml",
})
JSON_SCHEMA_FORMATS: frozenset[str] = frozenset({
    "application/schema+json",
    "application/schema+yaml",
})
OPENAPI_SCHEMA_FORMATS: frozenset[str] = frozenset({
    "application/vnd.oai.openapi",
    "application/vnd.oai.openapi+json",
    "application/vnd.oai.openapi+yaml",
})
AVRO_SCHEMA_FORMATS: frozenset[str] = frozenset({
    "application/vnd.apache.avro",
    "application/vnd.apache.avro+json",
    "application/vnd.apache.avro+yaml",
})
PROTOBUF_SCHEMA_FORMATS: frozenset[str] = frozenset({"application/vnd.google.protobuf"})
RAML_SCHEMA_FORMATS: frozenset[str] = frozenset({"application/raml+yaml"})


@dataclass(frozen=True)
class AsyncAPIContext:
    """Resolver context for an AsyncAPI document."""

    raw_obj: dict[str, Any]
    root_parts: list[str]
    base_path: Path | None
    base_url: str | None


@dataclass(frozen=True)
class AsyncAPIResolvedRef:
    """Resolved AsyncAPI reference with parser path and document context."""

    value: YamlValue
    path: list[str]
    context: AsyncAPIContext


@dataclass(frozen=True)
class AsyncAPISchema:
    """AsyncAPI schema candidate with the context needed to parse it."""

    name: str
    raw_schema: YamlValue
    path: list[str]
    context: AsyncAPIContext
    parse_as_file: bool = False


def _iter_mapping_items(value: Any) -> list[tuple[str, Any]]:
    return list(value.items()) if isinstance(value, dict) else []


def _make_model_name(*parts: object) -> str:
    words: list[str] = []
    for part in parts:
        words.extend(word[:1].upper() + word[1:] for word in NAME_PART_PATTERN.findall(str(part)))
    return "".join(words) or "AsyncAPIModel"


def _schema_format_media_type(schema_format: str) -> str:
    return schema_format.split(";", maxsplit=1)[0].strip().lower()


def _is_multi_format_schema_object(raw_schema: YamlValue) -> bool:
    if not isinstance(raw_schema, dict) or "schema" not in raw_schema:
        return False
    if "schemaFormat" in raw_schema:
        return True
    fixed_keys = {key for key in raw_schema if isinstance(key, str) and not key.startswith("x-")}
    return fixed_keys == {"schema"}


def _unsupported_schema_format_error(schema_format: str, path: list[str]) -> Error:
    msg = (
        f"Unsupported AsyncAPI schemaFormat {schema_format!r} at {'/'.join(path)}. "
        "Supported embedded schema formats are AsyncAPI Schema Object, JSON Schema, "
        "OpenAPI Schema Object, and Avro. Protocol Buffers, RAML, and custom schema "
        "formats are not supported inside AsyncAPI documents."
    )
    return Error(msg)


def _schema_format_kind(schema_format: str | None, path: list[str]) -> str:
    if schema_format is None:
        return "asyncapi"
    media_type = _schema_format_media_type(schema_format)
    if media_type in ASYNCAPI_SCHEMA_FORMATS:
        return "asyncapi"
    if media_type in JSON_SCHEMA_FORMATS:
        return "jsonschema"
    if media_type in OPENAPI_SCHEMA_FORMATS:
        return "openapi"
    if media_type in AVRO_SCHEMA_FORMATS:
        return "avro"
    if media_type in PROTOBUF_SCHEMA_FORMATS | RAML_SCHEMA_FORMATS:
        raise _unsupported_schema_format_error(schema_format, path)
    raise _unsupported_schema_format_error(schema_format, path)


@snooper_to_methods()
class AsyncAPIParser(OpenAPIParser):
    """Parser for AsyncAPI 2.x and 3.x documents."""

    SCHEMA_PATHS: ClassVar[list[str]] = ["#/components/schemas"]
    _config_class_name: ClassVar[str] = "AsyncAPIParserConfig"

    def __init__(
        self,
        source: str | Path | list[Path] | ParseResult,
        *,
        config: AsyncAPIParserConfig | None = None,
        **options: Unpack[AsyncAPIParserConfigDict],
    ) -> None:
        """Initialize the AsyncAPI parser."""
        super().__init__(source=source, config=config, **options)  # type: ignore[arg-type]

    @property
    def schema_features(self) -> OpenAPISchemaFeatures:
        """Get Schema Object features based on config or detected AsyncAPI version."""
        from datamodel_code_generator.parser.schema_version import (  # noqa: PLC0415
            OpenAPISchemaFeatures,
            detect_asyncapi_version,
        )

        config_version = getattr(self.config, "asyncapi_version", None)
        if config_version is not None and config_version != AsyncAPIVersion.Auto:
            return OpenAPISchemaFeatures.from_asyncapi_version(config_version)
        version = detect_asyncapi_version(self.raw_obj) if self.raw_obj else AsyncAPIVersion.Auto
        return OpenAPISchemaFeatures.from_asyncapi_version(version)

    def _collect_discriminator_schemas(self) -> None:
        """Collect discriminator metadata from component schemas."""
        schemas = self.raw_obj.get("components", {}).get("schemas", {})
        if not isinstance(schemas, dict):
            return
        for schema_name, schema in schemas.items():
            if not isinstance(schema, dict):
                continue
            discriminator = schema.get("discriminator")
            if discriminator and not schema.get("oneOf") and not schema.get("anyOf"):
                self._discriminator_schemas[f"#/components/schemas/{schema_name}"] = discriminator

    def _current_asyncapi_context(self) -> AsyncAPIContext:
        return AsyncAPIContext(
            raw_obj=self.raw_obj,
            root_parts=list(self.model_resolver.current_root),
            base_path=self.model_resolver.current_base_path,
            base_url=self.model_resolver.base_url,
        )

    @contextmanager
    def _asyncapi_context(self, context: AsyncAPIContext) -> Iterator[None]:
        previous_raw_obj = self.raw_obj
        self.raw_obj = context.raw_obj
        try:
            with (
                self.model_resolver.current_base_path_context(context.base_path),
                self.model_resolver.base_url_context(context.base_url),
                self.model_resolver.current_root_context(context.root_parts),
            ):
                yield
        finally:
            self.raw_obj = previous_raw_obj

    def _schema(
        self,
        name: str,
        raw_schema: YamlValue,
        path: list[str],
        context: AsyncAPIContext | None = None,
        *,
        parse_as_file: bool = False,
    ) -> AsyncAPISchema:
        return AsyncAPISchema(
            name=name,
            raw_schema=raw_schema,
            path=path,
            context=context or self._current_asyncapi_context(),
            parse_as_file=parse_as_file,
        )

    def _schema_context_for_converted_schema(
        self,
        converted_schema: dict[str, YamlValue],
        path: list[str],
    ) -> AsyncAPIContext:
        current_context = self._current_asyncapi_context()
        return AsyncAPIContext(
            raw_obj=converted_schema,
            root_parts=[*current_context.root_parts, "#/asyncapi-schemas", *path],
            base_path=current_context.base_path,
            base_url=current_context.base_url,
        )

    def _iter_schema_format_schemas(
        self,
        name: str,
        raw_schema: YamlValue,
        path: list[str],
        inherited_schema_format: str | None = None,
    ) -> list[AsyncAPISchema]:
        schema_format = inherited_schema_format
        if isinstance(raw_schema, dict) and "schemaFormat" in raw_schema and "schema" not in raw_schema:
            msg = f"AsyncAPI Multi Format Schema Object requires a schema field at {'/'.join(path)}"
            raise Error(msg)
        if _is_multi_format_schema_object(raw_schema):
            assert isinstance(raw_schema, dict)
            raw_schema_format = raw_schema.get("schemaFormat")
            if raw_schema_format is not None and not isinstance(raw_schema_format, str):
                msg = f"AsyncAPI schemaFormat must be a string at {'/'.join(path)}"
                raise Error(msg)
            schema_format = raw_schema_format or schema_format
            raw_schema = raw_schema["schema"]
            path = [*path, "schema"]

        match _schema_format_kind(schema_format, path):
            case "asyncapi" | "jsonschema" | "openapi":
                if not isinstance(raw_schema, (dict, bool)):
                    msg = (
                        f"AsyncAPI schemaFormat {schema_format or 'default AsyncAPI schema'!r} "
                        f"requires a schema object at {'/'.join(path)}"
                    )
                    raise Error(msg)
                return [self._schema(name, raw_schema, path)]
            case "avro":
                converted_schema = convert_avro_schema_data(raw_schema)
                converted_schema.setdefault("title", name)
                context = self._schema_context_for_converted_schema(converted_schema, path)
                return [self._schema(name, converted_schema, context.root_parts, context, parse_as_file=True)]
            case _:  # pragma: no cover
                raise _unsupported_schema_format_error(schema_format or "", path)

    def _resolve_asyncapi_ref(self, ref: str) -> AsyncAPIResolvedRef:
        """Resolve an AsyncAPI Reference Object to raw data and a parser path."""
        resolved_ref = self.model_resolver.resolve_ref(ref)
        file_part, fragment = ([*resolved_ref.split("#", 1), ""])[:2]
        raw_doc = self._get_ref_body(file_part) if file_part else self.raw_obj
        if file_part:
            root_parts = [file_part] if is_url(file_part) else file_part.split("/")
            base_path = None if is_url(file_part) else Path(file_part).parent
            base_url = file_part if is_url(file_part) else None
        else:
            root_parts = list(self.model_resolver.current_root)
            base_path = self.model_resolver.current_base_path
            base_url = self.model_resolver.base_url
        context = AsyncAPIContext(
            raw_obj=raw_doc,
            root_parts=root_parts,
            base_path=base_path,
            base_url=base_url,
        )
        if not fragment:
            return AsyncAPIResolvedRef(raw_doc, root_parts or [resolved_ref], context)
        pointer = [p for p in fragment.split("/") if p]
        path_pointer = [unescape_json_pointer_segment(p) for p in pointer]
        if not path_pointer:
            return AsyncAPIResolvedRef(raw_doc, [*root_parts, "#/"], context)
        return AsyncAPIResolvedRef(
            get_model_by_path(raw_doc, pointer),
            [*root_parts, f"#/{path_pointer[0]}", *path_pointer[1:]],
            context,
        )

    def _iter_message_payload_schemas(
        self,
        message: Any,
        name: str,
        path: list[str],
        seen_paths: set[tuple[str, ...]] | None = None,
    ) -> list[AsyncAPISchema]:
        seen_paths = seen_paths or set()
        if not isinstance(message, dict):
            return []
        if ref := message.get("$ref"):
            if not isinstance(ref, str):
                return []
            resolved = self._resolve_asyncapi_ref(ref)
            resolved_path = resolved.path
            resolved_key = tuple(resolved_path)
            if resolved_key in seen_paths:
                return []
            ref_name = resolved_path[-1] if resolved_path else name
            with self._asyncapi_context(resolved.context):
                return self._iter_message_payload_schemas(
                    resolved.value,
                    _make_model_name(ref_name),
                    resolved_path,
                    seen_paths | {resolved_key},
                )
        if isinstance(one_of := message.get("oneOf"), list):
            schemas: list[AsyncAPISchema] = []
            for index, item in enumerate(one_of, start=1):
                schemas.extend(
                    self._iter_message_payload_schemas(
                        item,
                        _make_model_name(name, "Message", index),
                        [*path, "oneOf", str(index - 1)],
                        seen_paths,
                    )
                )
            return schemas

        schemas = []
        payload_schema_format = message.get("schemaFormat")
        if payload_schema_format is not None and not isinstance(payload_schema_format, str):
            msg = f"AsyncAPI message schemaFormat must be a string at {'/'.join(path)}"
            raise Error(msg)
        if "payload" in message:
            schemas.extend(
                self._iter_schema_format_schemas(
                    _make_model_name(name, "Payload"),
                    message["payload"],
                    [*path, "payload"],
                    payload_schema_format,
                )
            )
        if "headers" in message:
            schemas.extend(
                self._iter_schema_format_schemas(
                    _make_model_name(name, "Headers"),
                    message["headers"],
                    [*path, "headers"],
                )
            )
        elif "traits" in message:
            schemas.extend(
                self._iter_message_trait_header_schemas(
                    message["traits"],
                    _make_model_name(name, "Headers"),
                    [*path, "traits"],
                    seen_paths,
                )
            )
        return schemas

    def _iter_message_trait_header_schemas(
        self,
        traits: Any,
        name: str,
        path: list[str],
        seen_paths: set[tuple[str, ...]] | None = None,
    ) -> list[AsyncAPISchema]:
        seen_paths = seen_paths or set()
        trait_items = traits if isinstance(traits, list) else [traits]
        schemas: list[AsyncAPISchema] = []
        for index, trait in enumerate(trait_items):
            if not isinstance(trait, dict):
                continue
            trait_path = [*path, str(index)] if isinstance(traits, list) else path
            if ref := trait.get("$ref"):
                if not isinstance(ref, str):
                    continue
                resolved = self._resolve_asyncapi_ref(ref)
                resolved_key = tuple(resolved.path)
                if resolved_key in seen_paths:
                    continue
                with self._asyncapi_context(resolved.context):
                    schemas.extend(
                        self._iter_message_trait_header_schemas(
                            resolved.value,
                            name,
                            resolved.path,
                            seen_paths | {resolved_key},
                        )
                    )
                continue
            if "headers" not in trait:
                continue
            if schemas:
                msg = f"Multiple AsyncAPI message traits define headers for {'/'.join(path)}"
                raise Error(msg)
            schemas.extend(
                self._iter_schema_format_schemas(
                    name,
                    trait["headers"],
                    [*trait_path, "headers"],
                )
            )
        return schemas

    def _iter_operation_message_schemas(
        self,
        message: Any,
        name: str,
        path: list[str],
    ) -> list[AsyncAPISchema]:
        if isinstance(message, list):
            schemas: list[AsyncAPISchema] = []
            for index, item in enumerate(message, start=1):
                schemas.extend(
                    self._iter_operation_message_schemas(
                        item,
                        _make_model_name(name, "Message", index),
                        [*path, str(index - 1)],
                    )
                )
            return schemas
        return self._iter_message_payload_schemas(message, name, path)

    def _iter_operation_reply_schemas(
        self,
        reply: Any,
        name: str,
        path: list[str],
        seen_paths: set[tuple[str, ...]] | None = None,
    ) -> list[AsyncAPISchema]:
        seen_paths = seen_paths or set()
        if not isinstance(reply, dict):
            return []
        if ref := reply.get("$ref"):
            if not isinstance(ref, str):
                return []
            resolved = self._resolve_asyncapi_ref(ref)
            resolved_key = tuple(resolved.path)
            if resolved_key in seen_paths:
                return []
            with self._asyncapi_context(resolved.context):
                return self._iter_operation_reply_schemas(
                    resolved.value,
                    name,
                    resolved.path,
                    seen_paths | {resolved_key},
                )
        if "messages" not in reply:
            return []
        return self._iter_operation_message_schemas(
            reply["messages"],
            _make_model_name(name, "Reply"),
            [*path, "messages"],
        )

    def _iter_operation_schemas(
        self,
        operation: Any,
        name: str,
        path: list[str],
        seen_paths: set[tuple[str, ...]] | None = None,
    ) -> list[AsyncAPISchema]:
        seen_paths = seen_paths or set()
        if not isinstance(operation, dict):
            return []
        if ref := operation.get("$ref"):
            if not isinstance(ref, str):
                return []
            resolved = self._resolve_asyncapi_ref(ref)
            resolved_key = tuple(resolved.path)
            if resolved_key in seen_paths:
                return []
            with self._asyncapi_context(resolved.context):
                return self._iter_operation_schemas(
                    resolved.value,
                    _make_model_name(resolved.path[-1] if resolved.path else name),
                    resolved.path,
                    seen_paths | {resolved_key},
                )
        schemas: list[AsyncAPISchema] = []
        if "messages" in operation:
            schemas.extend(
                self._iter_operation_message_schemas(
                    operation["messages"],
                    name,
                    [*path, "messages"],
                )
            )
        if "reply" in operation:
            schemas.extend(
                self._iter_operation_reply_schemas(
                    operation["reply"],
                    name,
                    [*path, "reply"],
                )
            )
        return schemas

    def _iter_channel_schemas(
        self,
        channel: Any,
        name: str,
        path: list[str],
        seen_paths: set[tuple[str, ...]] | None = None,
    ) -> list[AsyncAPISchema]:
        seen_paths = seen_paths or set()
        if not isinstance(channel, dict):
            return []
        if ref := channel.get("$ref"):
            if not isinstance(ref, str):
                return []
            resolved = self._resolve_asyncapi_ref(ref)
            resolved_key = tuple(resolved.path)
            if resolved_key in seen_paths:
                return []
            with self._asyncapi_context(resolved.context):
                return self._iter_channel_schemas(
                    resolved.value,
                    _make_model_name(resolved.path[-1] if resolved.path else name),
                    resolved.path,
                    seen_paths | {resolved_key},
                )
        schemas: list[AsyncAPISchema] = []
        for operation_name in OPERATION_NAMES:
            operation = channel.get(operation_name)
            if isinstance(operation, dict) and "message" in operation:
                schemas.extend(
                    self._iter_operation_message_schemas(
                        operation["message"],
                        _make_model_name(name, operation_name),
                        [*path, operation_name, "message"],
                    )
                )
        for message_name, message in _iter_mapping_items(channel.get("messages")):
            schemas.extend(
                self._iter_message_payload_schemas(
                    message,
                    _make_model_name(name, message_name),
                    [*path, "messages", message_name],
                )
            )
        return schemas

    def _iter_asyncapi_schemas(
        self,
        specification: dict[str, Any],
        path_parts: list[str],
    ) -> list[AsyncAPISchema]:
        schemas: list[AsyncAPISchema] = []
        components = specification.get("components", {})
        components = components if isinstance(components, dict) else {}

        for schema_name, raw_schema in _iter_mapping_items(components.get("schemas")):
            if not isinstance(raw_schema, (dict, bool)):
                continue
            schemas.extend(
                self._iter_schema_format_schemas(
                    schema_name,
                    raw_schema,
                    [*path_parts, "#/components", "schemas", schema_name],
                )
            )

        for message_name, message in _iter_mapping_items(components.get("messages")):
            schemas.extend(
                self._iter_message_payload_schemas(
                    message,
                    _make_model_name(message_name),
                    [*path_parts, "#/components", "messages", message_name],
                )
            )

        for trait_name, trait in _iter_mapping_items(components.get("messageTraits")):
            schemas.extend(
                self._iter_message_trait_header_schemas(
                    trait,
                    _make_model_name(trait_name, "Headers"),
                    [*path_parts, "#/components", "messageTraits", trait_name],
                )
            )

        for operation_name, operation in _iter_mapping_items(components.get("operations")):
            schemas.extend(
                self._iter_operation_schemas(
                    operation,
                    _make_model_name(operation_name),
                    [*path_parts, "#/components", "operations", operation_name],
                )
            )

        for channel_name, channel in _iter_mapping_items(specification.get("channels")):
            schemas.extend(
                self._iter_channel_schemas(
                    channel,
                    _make_model_name(channel_name),
                    [*path_parts, "#/channels", channel_name],
                )
            )

        for operation_name, operation in _iter_mapping_items(specification.get("operations")):
            schemas.extend(
                self._iter_operation_schemas(
                    operation,
                    _make_model_name(operation_name),
                    [*path_parts, "#/operations", operation_name],
                )
            )

        return schemas

    def _resolve_asyncapi_unparsed_json_pointer(
        self,
        context_sources: dict[tuple[str, ...], AsyncAPIContext],
    ) -> None:
        model_count = len(self.results)
        for root_key, context in context_sources.items():
            if not (reserved_refs := self.reserved_refs.get(root_key)):
                continue

            with self._asyncapi_context(context):
                for reserved_ref in sorted(reserved_refs):
                    if self.model_resolver.add_ref(reserved_ref, resolved=True).loaded:
                        continue
                    self.parse_json_pointer(context.raw_obj, reserved_ref, list(root_key))

        if model_count != len(self.results):
            self._resolve_asyncapi_unparsed_json_pointer(context_sources)

    def parse_raw(self) -> None:
        """Parse AsyncAPI component schemas and message payload/header schemas."""
        parsed_paths: set[tuple[str, ...]] = set()
        context_sources: dict[tuple[str, ...], AsyncAPIContext] = {}
        for source, path_parts in self._get_context_source_path_parts():
            if self.validation:
                warn_deprecated("cli.validation", stacklevel=2)

            specification: dict[str, Any] = (
                dict(source.raw_data) if source.raw_data is not None else load_data(source.text)
            )
            self.raw_obj = specification
            context_sources[tuple(path_parts)] = self._current_asyncapi_context()
            self._collect_discriminator_schemas()
            for schema in self._iter_asyncapi_schemas(specification, path_parts):
                context_sources[tuple(schema.context.root_parts)] = schema.context
                raw_schema = schema.raw_schema
                if not isinstance(raw_schema, (dict, bool)):
                    continue
                path_key = tuple(schema.path)
                if path_key in parsed_paths:
                    continue
                parsed_paths.add(path_key)
                with self._asyncapi_context(schema.context):
                    if schema.parse_as_file:
                        self._parse_file(raw_schema, schema.name, schema.path)
                    else:
                        self.parse_raw_obj(schema.name, raw_schema, schema.path)

        self._resolve_asyncapi_unparsed_json_pointer(context_sources)
        self._generate_forced_base_models()
