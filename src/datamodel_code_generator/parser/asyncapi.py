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

from datamodel_code_generator import YamlValue, load_data, snooper_to_methods
from datamodel_code_generator.deprecations import warn_deprecated
from datamodel_code_generator.enums import AsyncAPIVersion
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


def _iter_mapping_items(value: Any) -> list[tuple[str, Any]]:
    return list(value.items()) if isinstance(value, dict) else []


def _make_model_name(*parts: object) -> str:
    words: list[str] = []
    for part in parts:
        words.extend(word[:1].upper() + word[1:] for word in NAME_PART_PATTERN.findall(str(part)))
    return "".join(words) or "AsyncAPIModel"


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

    def _schema(self, name: str, raw_schema: YamlValue, path: list[str]) -> AsyncAPISchema:
        return AsyncAPISchema(
            name=name,
            raw_schema=raw_schema,
            path=path,
            context=self._current_asyncapi_context(),
        )

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
        if "payload" in message:
            schemas.append(self._schema(_make_model_name(name, "Payload"), message["payload"], [*path, "payload"]))
        if "headers" in message:
            schemas.append(self._schema(_make_model_name(name, "Headers"), message["headers"], [*path, "headers"]))
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

    def _iter_asyncapi_schemas(
        self,
        specification: dict[str, Any],
        path_parts: list[str],
    ) -> list[AsyncAPISchema]:
        schemas: list[AsyncAPISchema] = []
        components = specification.get("components", {})
        components = components if isinstance(components, dict) else {}

        for schema_name, raw_schema in _iter_mapping_items(components.get("schemas")):
            schemas.append(self._schema(schema_name, raw_schema, [*path_parts, "#/components", "schemas", schema_name]))

        for message_name, message in _iter_mapping_items(components.get("messages")):
            schemas.extend(
                self._iter_message_payload_schemas(
                    message,
                    _make_model_name(message_name),
                    [*path_parts, "#/components", "messages", message_name],
                )
            )

        for channel_name, channel in _iter_mapping_items(specification.get("channels")):
            if not isinstance(channel, dict):
                continue
            for operation_name in OPERATION_NAMES:
                operation = channel.get(operation_name)
                if isinstance(operation, dict) and "message" in operation:
                    schemas.extend(
                        self._iter_operation_message_schemas(
                            operation["message"],
                            _make_model_name(channel_name, operation_name),
                            [*path_parts, "#/channels", channel_name, operation_name, "message"],
                        )
                    )
            for message_name, message in _iter_mapping_items(channel.get("messages")):
                schemas.extend(
                    self._iter_message_payload_schemas(
                        message,
                        _make_model_name(channel_name, message_name),
                        [*path_parts, "#/channels", channel_name, "messages", message_name],
                    )
                )

        for operation_name, operation in _iter_mapping_items(specification.get("operations")):
            if isinstance(operation, dict) and "messages" in operation:
                schemas.extend(
                    self._iter_operation_message_schemas(
                        operation["messages"],
                        _make_model_name(operation_name),
                        [*path_parts, "#/operations", operation_name, "messages"],
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
                    self.parse_raw_obj(schema.name, raw_schema, schema.path)

        self._resolve_asyncapi_unparsed_json_pointer(context_sources)
        self._generate_forced_base_models()
