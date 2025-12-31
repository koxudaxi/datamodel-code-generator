"""GraphQL schema parser implementation.

Parses GraphQL schema files to generate Python data models including
objects, interfaces, enums, scalars, inputs, and union types.
"""

from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Any,
)

from typing_extensions import Unpack

from datamodel_code_generator import (
    LiteralType,
    snooper_to_methods,
)
from datamodel_code_generator.format import DatetimeClassType
from datamodel_code_generator.model.dataclass import DataClass
from datamodel_code_generator.model.enum import SPECIALIZED_ENUM_TYPE_MATCH, Enum
from datamodel_code_generator.model.pydantic_v2.dataclass import DataClass as PydanticV2DataClass
from datamodel_code_generator.parser.base import (
    DataType,
    Parser,
    escape_characters,
)
from datamodel_code_generator.reference import ModelType, Reference
from datamodel_code_generator.types import Types

try:
    import graphql
except ImportError as exc:  # pragma: no cover
    msg = "Please run `$pip install 'datamodel-code-generator[graphql]`' to generate data-model from a GraphQL schema."
    raise Exception(msg) from exc  # noqa: TRY002


if TYPE_CHECKING:
    from pathlib import Path
    from urllib.parse import ParseResult

    from datamodel_code_generator._types import GraphQLParserConfigDict
    from datamodel_code_generator.config import GraphQLParserConfig
    from datamodel_code_generator.model import DataModel, DataModelFieldBase

# graphql-core >=3.2.7 removed TypeResolvers in favor of TypeFields.kind.
# Normalize to a single callable for resolving type kinds.
try:  # graphql-core < 3.2.7
    graphql_resolver_kind = graphql.type.introspection.TypeResolvers().kind  # pyright: ignore[reportAttributeAccessIssue]
except AttributeError:  # pragma: no cover - executed on newer graphql-core
    graphql_resolver_kind = graphql.type.introspection.TypeFields.kind  # pyright: ignore[reportAttributeAccessIssue]


def build_graphql_schema(schema_str: str) -> graphql.GraphQLSchema:
    """Build a graphql schema from a string."""
    schema = graphql.build_schema(schema_str)
    return graphql.lexicographic_sort_schema(schema)


@snooper_to_methods()
class GraphQLParser(Parser["GraphQLParserConfig"]):
    """Parser for GraphQL schema files."""

    # raw graphql schema as `graphql-core` object
    raw_obj: graphql.GraphQLSchema
    # all processed graphql objects
    # mapper from an object name (unique) to an object
    all_graphql_objects: dict[str, graphql.GraphQLNamedType]
    # a reference for each object
    # mapper from an object name to his reference
    references: dict[str, Reference] = {}  # noqa: RUF012
    # mapper from graphql type to all objects with this type
    # `graphql.type.introspection.TypeKind` -- an enum with all supported types
    # `graphql.GraphQLNamedType` -- base type for each graphql object
    # see `graphql-core` for more details
    support_graphql_types: dict[graphql.type.introspection.TypeKind, list[graphql.GraphQLNamedType]]
    # graphql types order for render
    # may be as a parameter in the future
    parse_order: list[graphql.type.introspection.TypeKind] = [  # noqa: RUF012
        graphql.type.introspection.TypeKind.SCALAR,
        graphql.type.introspection.TypeKind.ENUM,
        graphql.type.introspection.TypeKind.INTERFACE,
        graphql.type.introspection.TypeKind.OBJECT,
        graphql.type.introspection.TypeKind.INPUT_OBJECT,
        graphql.type.introspection.TypeKind.UNION,
    ]

    @classmethod
    def _create_default_config(cls, options: GraphQLParserConfigDict) -> GraphQLParserConfig:  # type: ignore[override]
        """Create a GraphQLParserConfig from options."""
        from datamodel_code_generator import types as types_module  # noqa: PLC0415
        from datamodel_code_generator.config import GraphQLParserConfig  # noqa: PLC0415
        from datamodel_code_generator.model import base as model_base  # noqa: PLC0415
        from datamodel_code_generator.util import is_pydantic_v2  # noqa: PLC0415

        if is_pydantic_v2():
            GraphQLParserConfig.model_rebuild(
                _types_namespace={
                    "StrictTypes": types_module.StrictTypes,
                    "DataModel": model_base.DataModel,
                    "DataModelFieldBase": model_base.DataModelFieldBase,
                    "DataTypeManager": types_module.DataTypeManager,
                }
            )
            return GraphQLParserConfig.model_validate(options)
        GraphQLParserConfig.update_forward_refs(
            StrictTypes=types_module.StrictTypes,
            DataModel=model_base.DataModel,
            DataModelFieldBase=model_base.DataModelFieldBase,
            DataTypeManager=types_module.DataTypeManager,
        )
        defaults = {name: field.default for name, field in GraphQLParserConfig.__fields__.items()}
        defaults.update(options)
        return GraphQLParserConfig.construct(**defaults)  # type: ignore[return-value]  # pragma: no cover

    def __init__(
        self,
        source: str | Path | ParseResult,
        *,
        config: GraphQLParserConfig | None = None,
        **options: Unpack[GraphQLParserConfigDict],
    ) -> None:
        """Initialize the GraphQL parser with configuration options."""
        if config is None and options.get("target_datetime_class") is None:
            options["target_datetime_class"] = DatetimeClassType.Datetime
        use_standard_collections = (
            config.use_standard_collections if config else options.get("use_standard_collections", False)
        )
        use_union_operator = config.use_union_operator if config else options.get("use_union_operator", False)
        super().__init__(source=source, config=config, **options)

        self.data_model_scalar_type = self.config.data_model_scalar_type
        self.data_model_union_type = self.config.data_model_union_type
        self.use_standard_collections = use_standard_collections
        self.use_union_operator = use_union_operator

    def _resolve_types(self, paths: list[str], schema: graphql.GraphQLSchema) -> None:
        for type_name, type_ in schema.type_map.items():
            if type_name.startswith("__"):
                continue

            if type_name in {"Query", "Mutation"}:
                continue

            resolved_type = graphql_resolver_kind(type_, None)

            if resolved_type in self.support_graphql_types:  # pragma: no cover
                self.all_graphql_objects[type_.name] = type_
                # TODO: need a special method for each graph type
                self.references[type_.name] = Reference(
                    path=f"{paths!s}/{resolved_type.value}/{type_.name}",
                    name=type_.name,
                    original_name=type_.name,
                )

                self.support_graphql_types[resolved_type].append(type_)

    def _create_data_model(self, model_type: type[DataModel] | None = None, **kwargs: Any) -> DataModel:
        """Create data model instance with dataclass_arguments support for DataClass."""
        # Add class decorators if not already provided
        if "decorators" not in kwargs and self.class_decorators:
            kwargs["decorators"] = list(self.class_decorators)
        data_model_class = model_type or self.data_model_type
        if issubclass(data_model_class, (DataClass, PydanticV2DataClass)):
            # Use dataclass_arguments from kwargs, or fall back to self.dataclass_arguments
            # If both are None, construct from legacy frozen_dataclasses/keyword_only flags
            dataclass_arguments = kwargs.pop("dataclass_arguments", None)
            if dataclass_arguments is None:
                dataclass_arguments = self.dataclass_arguments
            if dataclass_arguments is None:
                # Construct from legacy flags for library API compatibility
                dataclass_arguments = {}
                if self.frozen_dataclasses:
                    dataclass_arguments["frozen"] = True
                if self.keyword_only:
                    dataclass_arguments["kw_only"] = True
            kwargs["dataclass_arguments"] = dataclass_arguments
            kwargs.pop("frozen", None)
            kwargs.pop("keyword_only", None)
        else:
            kwargs.pop("dataclass_arguments", None)
        return data_model_class(**kwargs)

    def _typename_field(self, name: str) -> DataModelFieldBase:
        return self.data_model_field_type(
            name="typename__",
            data_type=DataType(
                literals=[name],
                use_union_operator=self.use_union_operator,
                use_standard_collections=self.use_standard_collections,
            ),
            default=name,
            use_annotated=self.use_annotated,
            required=False,
            alias="__typename",
            use_one_literal_as_default=True,
            use_default_kwarg=self.use_default_kwarg,
            has_default=True,
        )

    def _get_default(  # noqa: PLR6301
        self,
        field: graphql.GraphQLField | graphql.GraphQLInputField,
        final_data_type: DataType,
        *,
        required: bool,
    ) -> Any:
        if isinstance(field, graphql.GraphQLInputField):  # pragma: no cover
            if field.default_value == graphql.pyutils.Undefined:  # pragma: no cover
                return None
            return field.default_value
        if required is False and final_data_type.is_list:
            return None

        return None

    def parse_scalar(self, scalar_graphql_object: graphql.GraphQLScalarType) -> None:
        """Parse a GraphQL scalar type and add it to results."""
        self.results.append(
            self.data_model_scalar_type(
                reference=self.references[scalar_graphql_object.name],
                fields=[],
                custom_template_dir=self.custom_template_dir,
                extra_template_data=self.extra_template_data,
                description=scalar_graphql_object.description,
            )
        )

    def should_parse_enum_as_literal(self, obj: graphql.GraphQLEnumType) -> bool:
        """Determine if an enum should be parsed as a literal type."""
        if self.enum_field_as_literal == LiteralType.All:
            return True
        if self.enum_field_as_literal == LiteralType.One:
            return len(obj.values) == 1
        return False

    def parse_enum(self, enum_object: graphql.GraphQLEnumType) -> None:
        """Parse a GraphQL enum type and add it to results."""
        if self.ignore_enum_constraints:
            return self.parse_enum_as_str_type(enum_object)
        if self.should_parse_enum_as_literal(enum_object):
            return self.parse_enum_as_literal(enum_object)
        return self.parse_enum_as_enum_class(enum_object)

    def parse_enum_as_str_type(self, enum_object: graphql.GraphQLEnumType) -> None:
        """Parse enum as a str type alias when ignoring enum constraints."""
        data_type = self.data_type_manager.get_data_type(Types.string)
        data_model_type = self._create_data_model(
            model_type=self.data_model_root_type,
            reference=self.references[enum_object.name],
            fields=[
                self.data_model_field_type(
                    required=True,
                    data_type=data_type,
                )
            ],
            custom_base_class=self._resolve_base_class(enum_object.name),
            custom_template_dir=self.custom_template_dir,
            extra_template_data=self.extra_template_data,
            path=self.current_source_path,
            description=enum_object.description,
        )
        self.results.append(data_model_type)

    def parse_enum_as_literal(self, enum_object: graphql.GraphQLEnumType) -> None:
        """Parse enum values as a Literal type."""
        data_type = self.data_type(literals=list(enum_object.values.keys()))
        data_model_type = self._create_data_model(
            model_type=self.data_model_root_type,
            reference=self.references[enum_object.name],
            fields=[
                self.data_model_field_type(
                    required=True,
                    data_type=data_type,
                )
            ],
            custom_base_class=self._resolve_base_class(enum_object.name),
            custom_template_dir=self.custom_template_dir,
            extra_template_data=self.extra_template_data,
            path=self.current_source_path,
            description=enum_object.description,
        )
        self.results.append(data_model_type)

    def parse_enum_as_enum_class(self, enum_object: graphql.GraphQLEnumType) -> None:
        """Parse enum values as an Enum class."""
        enum_fields: list[DataModelFieldBase] = []
        exclude_field_names: set[str] = set()

        for value_name, value in enum_object.values.items():
            default = f"'{value_name.translate(escape_characters)}'" if isinstance(value_name, str) else value_name

            field_name = self.model_resolver.get_valid_field_name(
                value_name, excludes=exclude_field_names, model_type=ModelType.ENUM
            )
            exclude_field_names.add(field_name)

            enum_fields.append(
                self.data_model_field_type(
                    name=field_name,
                    data_type=self.data_type_manager.get_data_type(
                        Types.string,
                    ),
                    default=default,
                    required=True,
                    strip_default_none=self.strip_default_none,
                    has_default=True,
                    use_field_description=value.description is not None,
                    original_name=None,
                )
            )

        enum_cls: type[Enum] = Enum
        if (
            self.target_python_version.has_strenum
            and self.use_specialized_enum
            and (specialized_type := SPECIALIZED_ENUM_TYPE_MATCH.get(Types.string))
        ):
            # If specialized enum is available in the target Python version, use it
            enum_cls = specialized_type

        enum: Enum = enum_cls(
            reference=self.references[enum_object.name],
            fields=enum_fields,
            path=self.current_source_path,
            description=enum_object.description,
            type_=Types.string if self.use_subclass_enum else None,
            custom_template_dir=self.custom_template_dir,
        )
        self.results.append(enum)

    def parse_field(
        self,
        field_name: str,
        alias: str | list[str] | None,
        field: graphql.GraphQLField | graphql.GraphQLInputField,
    ) -> DataModelFieldBase:
        """Parse a GraphQL field and return a data model field."""
        final_data_type = DataType(
            is_optional=True,
            use_union_operator=self.use_union_operator,
            use_standard_collections=self.use_standard_collections,
        )
        data_type = final_data_type
        obj = field.type

        while graphql.is_list_type(obj) or graphql.is_non_null_type(obj):
            if graphql.is_list_type(obj):
                data_type.is_list = True

                new_data_type = DataType(
                    is_optional=True,
                    use_union_operator=self.use_union_operator,
                    use_standard_collections=self.use_standard_collections,
                )
                data_type.data_types = [new_data_type]

                data_type = new_data_type
            elif graphql.is_non_null_type(obj):  # pragma: no cover
                data_type.is_optional = False

            obj = graphql.assert_wrapping_type(obj)
            obj = obj.of_type

        obj = graphql.assert_named_type(obj)
        if obj.name in self.references:
            data_type.reference = self.references[obj.name]
        else:  # pragma: no cover
            # Only happens for Query and Mutation root types
            data_type.type = obj.name

        required = (not self.force_optional_for_required_fields) and (not final_data_type.is_optional)

        default = self._get_default(field, final_data_type, required=required)
        extras = {} if self.default_field_extras is None else self.default_field_extras.copy()

        if field.description is not None:  # pragma: no cover
            extras["description"] = field.description

        # Handle multiple aliases (Pydantic v2 AliasChoices)
        single_alias: str | None = None
        validation_aliases: list[str] | None = None
        if isinstance(alias, list):
            validation_aliases = alias
        else:
            single_alias = alias
        return self.data_model_field_type(
            name=field_name,
            default=default,
            data_type=final_data_type,
            required=required,
            extras=extras,
            alias=single_alias,
            validation_aliases=validation_aliases,
            strip_default_none=self.strip_default_none,
            use_annotated=self.use_annotated,
            use_serialize_as_any=self.use_serialize_as_any,
            use_field_description=self.use_field_description,
            use_field_description_example=self.use_field_description_example,
            use_inline_field_description=self.use_inline_field_description,
            use_default_kwarg=self.use_default_kwarg,
            original_name=field_name,
            has_default=default is not None,
        )

    def parse_object_like(
        self,
        obj: graphql.GraphQLInterfaceType | graphql.GraphQLObjectType | graphql.GraphQLInputObjectType,
    ) -> None:
        """Parse a GraphQL object-like type and add it to results."""
        fields = []
        exclude_field_names: set[str] = set()

        for field_name, field in obj.fields.items():
            field_name_, alias = self.model_resolver.get_valid_field_name_and_alias(
                field_name,
                excludes=exclude_field_names,
                model_type=self.field_name_model_type,
                class_name=obj.name,
            )
            exclude_field_names.add(field_name_)

            data_model_field_type = self.parse_field(field_name_, alias, field)
            fields.append(data_model_field_type)

        fields.append(self._typename_field(obj.name))

        base_classes = []
        if hasattr(obj, "interfaces"):  # pragma: no cover
            base_classes = [self.references[i.name] for i in obj.interfaces]  # pyright: ignore[reportAttributeAccessIssue]

        data_model_type = self._create_data_model(
            reference=self.references[obj.name],
            fields=fields,
            base_classes=base_classes,
            custom_base_class=self._resolve_base_class(obj.name),
            custom_template_dir=self.custom_template_dir,
            extra_template_data=self.extra_template_data,
            path=self.current_source_path,
            description=obj.description,
            keyword_only=self.keyword_only,
            treat_dot_as_module=self.treat_dot_as_module,
            dataclass_arguments=self.dataclass_arguments,
        )
        self.results.append(data_model_type)

    def parse_interface(self, interface_graphql_object: graphql.GraphQLInterfaceType) -> None:
        """Parse a GraphQL interface type and add it to results."""
        self.parse_object_like(interface_graphql_object)

    def parse_object(self, graphql_object: graphql.GraphQLObjectType) -> None:
        """Parse a GraphQL object type and add it to results."""
        self.parse_object_like(graphql_object)

    def parse_input_object(self, input_graphql_object: graphql.GraphQLInputObjectType) -> None:
        """Parse a GraphQL input object type and add it to results."""
        self.parse_object_like(input_graphql_object)  # pragma: no cover

    def parse_union(self, union_object: graphql.GraphQLUnionType) -> None:
        """Parse a GraphQL union type and add it to results."""
        fields = [self.data_model_field_type(name=type_.name, data_type=DataType()) for type_ in union_object.types]

        data_model_type = self.data_model_union_type(
            reference=self.references[union_object.name],
            fields=fields,
            custom_base_class=self._resolve_base_class(union_object.name),
            custom_template_dir=self.custom_template_dir,
            extra_template_data=self.extra_template_data,
            path=self.current_source_path,
            description=union_object.description,
        )
        self.results.append(data_model_type)

    def parse_raw(self) -> None:
        """Parse the raw GraphQL schema and generate all data models."""
        self.all_graphql_objects = {}
        self.references: dict[str, Reference] = {}

        self.support_graphql_types = {
            graphql.type.introspection.TypeKind.SCALAR: [],
            graphql.type.introspection.TypeKind.ENUM: [],
            graphql.type.introspection.TypeKind.UNION: [],
            graphql.type.introspection.TypeKind.INTERFACE: [],
            graphql.type.introspection.TypeKind.OBJECT: [],
            graphql.type.introspection.TypeKind.INPUT_OBJECT: [],
        }

        # may be as a parameter in the future (??)
        mapper_from_graphql_type_to_parser_method = {
            graphql.type.introspection.TypeKind.SCALAR: self.parse_scalar,
            graphql.type.introspection.TypeKind.ENUM: self.parse_enum,
            graphql.type.introspection.TypeKind.INTERFACE: self.parse_interface,
            graphql.type.introspection.TypeKind.OBJECT: self.parse_object,
            graphql.type.introspection.TypeKind.INPUT_OBJECT: self.parse_input_object,
            graphql.type.introspection.TypeKind.UNION: self.parse_union,
        }

        combined_schema = "\n".join(source.text for source in self.iter_source)
        schema: graphql.GraphQLSchema = build_graphql_schema(combined_schema)
        self.raw_obj = schema

        self._resolve_types([], schema)

        for next_type in self.parse_order:
            for obj in self.support_graphql_types[next_type]:
                parser_ = mapper_from_graphql_type_to_parser_method[next_type]
                parser_(obj)
