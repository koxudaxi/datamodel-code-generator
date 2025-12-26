"""GraphQL schema parser implementation.

Parses GraphQL schema files to generate Python data models including
objects, interfaces, enums, scalars, inputs, and union types.
"""

from __future__ import annotations

from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
)
from urllib.parse import ParseResult

from datamodel_code_generator import (
    DEFAULT_SHARED_MODULE_NAME,
    AllOfMergeMode,
    CollapseRootModelsNameStrategy,
    DataclassArguments,
    DefaultPutDict,
    FieldTypeCollisionStrategy,
    LiteralType,
    NamingStrategy,
    PythonVersion,
    PythonVersionMin,
    ReadOnlyWriteOnlyModelType,
    ReuseScope,
    TargetPydanticVersion,
    snooper_to_methods,
)
from datamodel_code_generator.format import DEFAULT_FORMATTERS, DateClassType, DatetimeClassType, Formatter
from datamodel_code_generator.model import DataModel, DataModelFieldBase
from datamodel_code_generator.model import pydantic as pydantic_model
from datamodel_code_generator.model.dataclass import DataClass
from datamodel_code_generator.model.enum import SPECIALIZED_ENUM_TYPE_MATCH, Enum
from datamodel_code_generator.model.pydantic_v2.dataclass import DataClass as PydanticV2DataClass
from datamodel_code_generator.model.scalar import DataTypeScalar
from datamodel_code_generator.model.union import DataTypeUnion
from datamodel_code_generator.parser.base import (
    DataType,
    Parser,
    Source,
    escape_characters,
)
from datamodel_code_generator.reference import ModelType, Reference
from datamodel_code_generator.types import DataTypeManager, StrictTypes, Types

try:
    import graphql
except ImportError as exc:  # pragma: no cover
    msg = "Please run `$pip install 'datamodel-code-generator[graphql]`' to generate data-model from a GraphQL schema."
    raise Exception(msg) from exc  # noqa: TRY002


if TYPE_CHECKING:
    from collections import defaultdict
    from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence

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
class GraphQLParser(Parser):
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

    def __init__(  # noqa: PLR0913
        self,
        source: str | Path | ParseResult,
        *,
        data_model_type: type[DataModel] = pydantic_model.BaseModel,
        data_model_root_type: type[DataModel] = pydantic_model.CustomRootType,
        data_model_scalar_type: type[DataModel] = DataTypeScalar,
        data_model_union_type: type[DataModel] = DataTypeUnion,
        data_type_manager_type: type[DataTypeManager] = pydantic_model.DataTypeManager,
        data_model_field_type: type[DataModelFieldBase] = pydantic_model.DataModelField,
        base_class: str | None = None,
        base_class_map: dict[str, str] | None = None,
        additional_imports: list[str] | None = None,
        class_decorators: list[str] | None = None,
        custom_template_dir: Path | None = None,
        extra_template_data: defaultdict[str, dict[str, Any]] | None = None,
        target_python_version: PythonVersion = PythonVersionMin,
        dump_resolve_reference_action: Callable[[Iterable[str]], str] | None = None,
        validation: bool = False,
        field_constraints: bool = False,
        snake_case_field: bool = False,
        strip_default_none: bool = False,
        aliases: Mapping[str, str] | None = None,
        allow_population_by_field_name: bool = False,
        apply_default_values_for_required_fields: bool = False,
        allow_extra_fields: bool = False,
        extra_fields: str | None = None,
        use_generic_base_class: bool = False,
        force_optional_for_required_fields: bool = False,
        class_name: str | None = None,
        use_standard_collections: bool = False,
        base_path: Path | None = None,
        use_schema_description: bool = False,
        use_field_description: bool = False,
        use_field_description_example: bool = False,
        use_attribute_docstrings: bool = False,
        use_inline_field_description: bool = False,
        use_default_kwarg: bool = False,
        reuse_model: bool = False,
        reuse_scope: ReuseScope | None = None,
        shared_module_name: str = DEFAULT_SHARED_MODULE_NAME,
        encoding: str = "utf-8",
        enum_field_as_literal: LiteralType | None = None,
        enum_field_as_literal_map: dict[str, str] | None = None,
        ignore_enum_constraints: bool = False,
        set_default_enum_member: bool = False,
        use_subclass_enum: bool = False,
        use_specialized_enum: bool = True,
        strict_nullable: bool = False,
        use_generic_container_types: bool = False,
        enable_faux_immutability: bool = False,
        remote_text_cache: DefaultPutDict[str, str] | None = None,
        disable_appending_item_suffix: bool = False,
        strict_types: Sequence[StrictTypes] | None = None,
        empty_enum_field_name: str | None = None,
        custom_class_name_generator: Callable[[str], str] | None = None,
        field_extra_keys: set[str] | None = None,
        field_include_all_keys: bool = False,
        field_extra_keys_without_x_prefix: set[str] | None = None,
        model_extra_keys: set[str] | None = None,
        model_extra_keys_without_x_prefix: set[str] | None = None,
        wrap_string_literal: bool | None = None,
        use_title_as_name: bool = False,
        use_operation_id_as_name: bool = False,
        use_unique_items_as_set: bool = False,
        use_tuple_for_fixed_items: bool = False,
        allof_merge_mode: AllOfMergeMode = AllOfMergeMode.Constraints,
        http_headers: Sequence[tuple[str, str]] | None = None,
        http_ignore_tls: bool = False,
        http_timeout: float | None = None,
        use_annotated: bool = False,
        use_non_positive_negative_number_constrained_types: bool = False,
        use_decimal_for_multiple_of: bool = False,
        original_field_name_delimiter: str | None = None,
        use_double_quotes: bool = False,
        use_union_operator: bool = False,
        allow_responses_without_content: bool = False,
        collapse_root_models: bool = False,
        collapse_root_models_name_strategy: CollapseRootModelsNameStrategy | None = None,
        collapse_reuse_models: bool = False,
        skip_root_model: bool = False,
        use_type_alias: bool = False,
        special_field_name_prefix: str | None = None,
        remove_special_field_name_prefix: bool = False,
        capitalise_enum_members: bool = False,
        keep_model_order: bool = False,
        use_one_literal_as_default: bool = False,
        use_enum_values_in_discriminator: bool = False,
        known_third_party: list[str] | None = None,
        custom_formatters: list[str] | None = None,
        custom_formatters_kwargs: dict[str, Any] | None = None,
        use_pendulum: bool = False,
        use_standard_primitive_types: bool = False,
        http_query_parameters: Sequence[tuple[str, str]] | None = None,
        treat_dot_as_module: bool | None = None,
        use_exact_imports: bool = False,
        default_field_extras: dict[str, Any] | None = None,
        target_datetime_class: DatetimeClassType = DatetimeClassType.Datetime,
        target_date_class: DateClassType | None = None,
        keyword_only: bool = False,
        frozen_dataclasses: bool = False,
        no_alias: bool = False,
        formatters: list[Formatter] = DEFAULT_FORMATTERS,
        defer_formatting: bool = False,
        parent_scoped_naming: bool = False,
        naming_strategy: NamingStrategy | None = None,
        duplicate_name_suffix: dict[str, str] | None = None,
        dataclass_arguments: DataclassArguments | None = None,
        type_mappings: list[str] | None = None,
        type_overrides: dict[str, str] | None = None,
        read_only_write_only_model_type: ReadOnlyWriteOnlyModelType | None = None,
        use_serialize_as_any: bool = False,
        use_frozen_field: bool = False,
        use_default_factory_for_optional_nested_models: bool = False,
        field_type_collision_strategy: FieldTypeCollisionStrategy | None = None,
        target_pydantic_version: TargetPydanticVersion | None = None,
    ) -> None:
        """Initialize the GraphQL parser with configuration options."""
        super().__init__(
            source=source,
            data_model_type=data_model_type,
            data_model_root_type=data_model_root_type,
            data_type_manager_type=data_type_manager_type,
            data_model_field_type=data_model_field_type,
            base_class=base_class,
            base_class_map=base_class_map,
            additional_imports=additional_imports,
            class_decorators=class_decorators,
            custom_template_dir=custom_template_dir,
            extra_template_data=extra_template_data,
            target_python_version=target_python_version,
            dump_resolve_reference_action=dump_resolve_reference_action,
            validation=validation,
            field_constraints=field_constraints,
            snake_case_field=snake_case_field,
            strip_default_none=strip_default_none,
            aliases=aliases,
            allow_population_by_field_name=allow_population_by_field_name,
            allow_extra_fields=allow_extra_fields,
            extra_fields=extra_fields,
            use_generic_base_class=use_generic_base_class,
            apply_default_values_for_required_fields=apply_default_values_for_required_fields,
            force_optional_for_required_fields=force_optional_for_required_fields,
            class_name=class_name,
            use_standard_collections=use_standard_collections,
            base_path=base_path,
            use_schema_description=use_schema_description,
            use_field_description=use_field_description,
            use_field_description_example=use_field_description_example,
            use_attribute_docstrings=use_attribute_docstrings,
            use_inline_field_description=use_inline_field_description,
            use_default_kwarg=use_default_kwarg,
            reuse_model=reuse_model,
            reuse_scope=reuse_scope,
            shared_module_name=shared_module_name,
            encoding=encoding,
            enum_field_as_literal=enum_field_as_literal,
            enum_field_as_literal_map=enum_field_as_literal_map,
            ignore_enum_constraints=ignore_enum_constraints,
            use_one_literal_as_default=use_one_literal_as_default,
            use_enum_values_in_discriminator=use_enum_values_in_discriminator,
            set_default_enum_member=set_default_enum_member,
            use_subclass_enum=use_subclass_enum,
            use_specialized_enum=use_specialized_enum,
            strict_nullable=strict_nullable,
            use_generic_container_types=use_generic_container_types,
            enable_faux_immutability=enable_faux_immutability,
            remote_text_cache=remote_text_cache,
            disable_appending_item_suffix=disable_appending_item_suffix,
            strict_types=strict_types,
            empty_enum_field_name=empty_enum_field_name,
            custom_class_name_generator=custom_class_name_generator,
            field_extra_keys=field_extra_keys,
            field_include_all_keys=field_include_all_keys,
            field_extra_keys_without_x_prefix=field_extra_keys_without_x_prefix,
            model_extra_keys=model_extra_keys,
            model_extra_keys_without_x_prefix=model_extra_keys_without_x_prefix,
            wrap_string_literal=wrap_string_literal,
            use_title_as_name=use_title_as_name,
            use_operation_id_as_name=use_operation_id_as_name,
            use_unique_items_as_set=use_unique_items_as_set,
            use_tuple_for_fixed_items=use_tuple_for_fixed_items,
            allof_merge_mode=allof_merge_mode,
            http_headers=http_headers,
            http_ignore_tls=http_ignore_tls,
            http_timeout=http_timeout,
            use_annotated=use_annotated,
            use_non_positive_negative_number_constrained_types=use_non_positive_negative_number_constrained_types,
            use_decimal_for_multiple_of=use_decimal_for_multiple_of,
            original_field_name_delimiter=original_field_name_delimiter,
            use_double_quotes=use_double_quotes,
            use_union_operator=use_union_operator,
            allow_responses_without_content=allow_responses_without_content,
            collapse_root_models=collapse_root_models,
            collapse_root_models_name_strategy=collapse_root_models_name_strategy,
            collapse_reuse_models=collapse_reuse_models,
            skip_root_model=skip_root_model,
            use_type_alias=use_type_alias,
            special_field_name_prefix=special_field_name_prefix,
            remove_special_field_name_prefix=remove_special_field_name_prefix,
            capitalise_enum_members=capitalise_enum_members,
            keep_model_order=keep_model_order,
            known_third_party=known_third_party,
            custom_formatters=custom_formatters,
            custom_formatters_kwargs=custom_formatters_kwargs,
            use_pendulum=use_pendulum,
            use_standard_primitive_types=use_standard_primitive_types,
            http_query_parameters=http_query_parameters,
            treat_dot_as_module=treat_dot_as_module,
            use_exact_imports=use_exact_imports,
            default_field_extras=default_field_extras,
            target_datetime_class=target_datetime_class,
            target_date_class=target_date_class,
            keyword_only=keyword_only,
            frozen_dataclasses=frozen_dataclasses,
            no_alias=no_alias,
            formatters=formatters,
            defer_formatting=defer_formatting,
            parent_scoped_naming=parent_scoped_naming,
            naming_strategy=naming_strategy,
            duplicate_name_suffix=duplicate_name_suffix,
            dataclass_arguments=dataclass_arguments,
            type_mappings=type_mappings,
            type_overrides=type_overrides,
            read_only_write_only_model_type=read_only_write_only_model_type,
            use_serialize_as_any=use_serialize_as_any,
            use_frozen_field=use_frozen_field,
            use_default_factory_for_optional_nested_models=use_default_factory_for_optional_nested_models,
            field_type_collision_strategy=field_type_collision_strategy,
            target_pydantic_version=target_pydantic_version,
        )

        self.data_model_scalar_type = data_model_scalar_type
        self.data_model_union_type = data_model_union_type
        self.use_standard_collections = use_standard_collections
        self.use_union_operator = use_union_operator

    def _get_context_source_path_parts(self) -> Iterator[tuple[Source, list[str]]]:
        # TODO (denisart): Temporarily this method duplicates
        # the method `datamodel_code_generator.parser.jsonschema.JsonSchemaParser._get_context_source_path_parts`.

        if isinstance(self.source, list) or (  # pragma: no cover
            isinstance(self.source, Path) and self.source.is_dir()
        ):  # pragma: no cover
            self.current_source_path = Path()
            self.model_resolver.after_load_files = {
                self.base_path.joinpath(s.path).resolve().as_posix() for s in self.iter_source
            }

        for source in self.iter_source:
            if isinstance(self.source, ParseResult):  # pragma: no cover
                path_parts = self.get_url_path_parts(self.source)
            else:
                path_parts = list(source.path.parts)
            if self.current_source_path is not None:  # pragma: no cover
                self.current_source_path = source.path
            with (
                self.model_resolver.current_base_path_context(source.path.parent),
                self.model_resolver.current_root_context(path_parts),
            ):
                yield source, path_parts

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
        alias: str | None,
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

        return self.data_model_field_type(
            name=field_name,
            default=default,
            data_type=final_data_type,
            required=required,
            extras=extras,
            alias=alias,
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

        for source, path_parts in self._get_context_source_path_parts():
            schema: graphql.GraphQLSchema = build_graphql_schema(source.text)
            self.raw_obj = schema

            self._resolve_types(path_parts, schema)

            for next_type in self.parse_order:
                for obj in self.support_graphql_types[next_type]:
                    parser_ = mapper_from_graphql_type_to_parser_method[next_type]
                    parser_(obj)
