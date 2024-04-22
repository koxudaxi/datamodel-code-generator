from __future__ import annotations

from pathlib import Path
from typing import (
    Any,
    Callable,
    DefaultDict,
    Dict,
    Iterable,
    Iterator,
    List,
    Mapping,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
    Union,
)
from urllib.parse import ParseResult

from datamodel_code_generator import (
    DefaultPutDict,
    LiteralType,
    PythonVersion,
    snooper_to_methods,
)
from datamodel_code_generator.model import DataModel, DataModelFieldBase
from datamodel_code_generator.model import pydantic as pydantic_model
from datamodel_code_generator.model.enum import Enum
from datamodel_code_generator.model.scalar import DataTypeScalar
from datamodel_code_generator.model.union import DataTypeUnion
from datamodel_code_generator.parser.base import (
    DataType,
    Parser,
    Source,
    escape_characters,
)
from datamodel_code_generator.reference import ModelType, Reference
from datamodel_code_generator.types import (
    DataTypeManager,
    StrictTypes,
    Types,
)

try:
    import graphql
except ImportError:  # pragma: no cover
    raise Exception(
        "Please run `$pip install 'datamodel-code-generator[graphql]`' to generate data-model from a GraphQL schema."
    )


graphql_resolver = graphql.type.introspection.TypeResolvers()


def build_graphql_schema(schema_str: str) -> graphql.GraphQLSchema:
    """Build a graphql schema from a string."""
    schema = graphql.build_schema(schema_str)
    return graphql.lexicographic_sort_schema(schema)


@snooper_to_methods(max_variable_length=None)
class GraphQLParser(Parser):
    # raw graphql schema as `graphql-core` object
    raw_obj: graphql.GraphQLSchema
    # all processed graphql objects
    # mapper from an object name (unique) to an object
    all_graphql_objects: Dict[str, graphql.GraphQLNamedType]
    # a reference for each object
    # mapper from an object name to his reference
    references: Dict[str, Reference] = {}
    # mapper from graphql type to all objects with this type
    # `graphql.type.introspection.TypeKind` -- an enum with all supported types
    # `graphql.GraphQLNamedType` -- base type for each graphql object
    # see `graphql-core` for more details
    support_graphql_types: Dict[
        graphql.type.introspection.TypeKind, List[graphql.GraphQLNamedType]
    ]
    # graphql types order for render
    # may be as a parameter in the future
    parse_order: List[graphql.type.introspection.TypeKind] = [
        graphql.type.introspection.TypeKind.SCALAR,
        graphql.type.introspection.TypeKind.ENUM,
        graphql.type.introspection.TypeKind.INTERFACE,
        graphql.type.introspection.TypeKind.OBJECT,
        graphql.type.introspection.TypeKind.INPUT_OBJECT,
        graphql.type.introspection.TypeKind.UNION,
    ]

    def __init__(
        self,
        source: Union[str, Path, ParseResult],
        *,
        data_model_type: Type[DataModel] = pydantic_model.BaseModel,
        data_model_root_type: Type[DataModel] = pydantic_model.CustomRootType,
        data_model_scalar_type: Type[DataModel] = DataTypeScalar,
        data_model_union_type: Type[DataModel] = DataTypeUnion,
        data_type_manager_type: Type[DataTypeManager] = pydantic_model.DataTypeManager,
        data_model_field_type: Type[DataModelFieldBase] = pydantic_model.DataModelField,
        base_class: Optional[str] = None,
        additional_imports: Optional[List[str]] = None,
        custom_template_dir: Optional[Path] = None,
        extra_template_data: Optional[DefaultDict[str, Dict[str, Any]]] = None,
        target_python_version: PythonVersion = PythonVersion.PY_37,
        dump_resolve_reference_action: Optional[Callable[[Iterable[str]], str]] = None,
        validation: bool = False,
        field_constraints: bool = False,
        snake_case_field: bool = False,
        strip_default_none: bool = False,
        aliases: Optional[Mapping[str, str]] = None,
        allow_population_by_field_name: bool = False,
        apply_default_values_for_required_fields: bool = False,
        allow_extra_fields: bool = False,
        force_optional_for_required_fields: bool = False,
        class_name: Optional[str] = None,
        use_standard_collections: bool = False,
        base_path: Optional[Path] = None,
        use_schema_description: bool = False,
        use_field_description: bool = False,
        use_default_kwarg: bool = False,
        reuse_model: bool = False,
        encoding: str = 'utf-8',
        enum_field_as_literal: Optional[LiteralType] = None,
        set_default_enum_member: bool = False,
        use_subclass_enum: bool = False,
        strict_nullable: bool = False,
        use_generic_container_types: bool = False,
        enable_faux_immutability: bool = False,
        remote_text_cache: Optional[DefaultPutDict[str, str]] = None,
        disable_appending_item_suffix: bool = False,
        strict_types: Optional[Sequence[StrictTypes]] = None,
        empty_enum_field_name: Optional[str] = None,
        custom_class_name_generator: Optional[Callable[[str], str]] = None,
        field_extra_keys: Optional[Set[str]] = None,
        field_include_all_keys: bool = False,
        field_extra_keys_without_x_prefix: Optional[Set[str]] = None,
        wrap_string_literal: Optional[bool] = None,
        use_title_as_name: bool = False,
        use_operation_id_as_name: bool = False,
        use_unique_items_as_set: bool = False,
        http_headers: Optional[Sequence[Tuple[str, str]]] = None,
        http_ignore_tls: bool = False,
        use_annotated: bool = False,
        use_non_positive_negative_number_constrained_types: bool = False,
        original_field_name_delimiter: Optional[str] = None,
        use_double_quotes: bool = False,
        use_union_operator: bool = False,
        allow_responses_without_content: bool = False,
        collapse_root_models: bool = False,
        special_field_name_prefix: Optional[str] = None,
        remove_special_field_name_prefix: bool = False,
        capitalise_enum_members: bool = False,
        keep_model_order: bool = False,
        use_one_literal_as_default: bool = False,
        known_third_party: Optional[List[str]] = None,
        custom_formatters: Optional[List[str]] = None,
        custom_formatters_kwargs: Optional[Dict[str, Any]] = None,
        use_pendulum: bool = False,
        http_query_parameters: Optional[Sequence[Tuple[str, str]]] = None,
    ) -> None:
        super().__init__(
            source=source,
            data_model_type=data_model_type,
            data_model_root_type=data_model_root_type,
            data_type_manager_type=data_type_manager_type,
            data_model_field_type=data_model_field_type,
            base_class=base_class,
            additional_imports=additional_imports,
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
            apply_default_values_for_required_fields=apply_default_values_for_required_fields,
            force_optional_for_required_fields=force_optional_for_required_fields,
            class_name=class_name,
            use_standard_collections=use_standard_collections,
            base_path=base_path,
            use_schema_description=use_schema_description,
            use_field_description=use_field_description,
            use_default_kwarg=use_default_kwarg,
            reuse_model=reuse_model,
            encoding=encoding,
            enum_field_as_literal=enum_field_as_literal,
            use_one_literal_as_default=use_one_literal_as_default,
            set_default_enum_member=set_default_enum_member,
            use_subclass_enum=use_subclass_enum,
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
            wrap_string_literal=wrap_string_literal,
            use_title_as_name=use_title_as_name,
            use_operation_id_as_name=use_operation_id_as_name,
            use_unique_items_as_set=use_unique_items_as_set,
            http_headers=http_headers,
            http_ignore_tls=http_ignore_tls,
            use_annotated=use_annotated,
            use_non_positive_negative_number_constrained_types=use_non_positive_negative_number_constrained_types,
            original_field_name_delimiter=original_field_name_delimiter,
            use_double_quotes=use_double_quotes,
            use_union_operator=use_union_operator,
            allow_responses_without_content=allow_responses_without_content,
            collapse_root_models=collapse_root_models,
            special_field_name_prefix=special_field_name_prefix,
            remove_special_field_name_prefix=remove_special_field_name_prefix,
            capitalise_enum_members=capitalise_enum_members,
            keep_model_order=keep_model_order,
            known_third_party=known_third_party,
            custom_formatters=custom_formatters,
            custom_formatters_kwargs=custom_formatters_kwargs,
            use_pendulum=use_pendulum,
            http_query_parameters=http_query_parameters,
        )

        self.data_model_scalar_type = data_model_scalar_type
        self.data_model_union_type = data_model_union_type

    def _get_context_source_path_parts(self) -> Iterator[Tuple[Source, List[str]]]:
        # TODO (denisart): Temporarily this method duplicates
        # the method `datamodel_code_generator.parser.jsonschema.JsonSchemaParser._get_context_source_path_parts`.

        if isinstance(self.source, list) or (
            isinstance(self.source, Path) and self.source.is_dir()
        ):
            self.current_source_path = Path()
            self.model_resolver.after_load_files = {
                self.base_path.joinpath(s.path).resolve().as_posix()
                for s in self.iter_source
            }

        for source in self.iter_source:
            if isinstance(self.source, ParseResult):
                path_parts = self.get_url_path_parts(self.source)
            else:
                path_parts = list(source.path.parts)
            if self.current_source_path is not None:
                self.current_source_path = source.path
            with self.model_resolver.current_base_path_context(
                source.path.parent
            ), self.model_resolver.current_root_context(path_parts):
                yield source, path_parts

    def _resolve_types(self, paths: List[str], schema: graphql.GraphQLSchema) -> None:
        for type_name, type_ in schema.type_map.items():
            if type_name.startswith('__'):
                continue

            if type_name in ['Query', 'Mutation']:
                continue

            resolved_type = graphql_resolver.kind(type_, None)

            if resolved_type in self.support_graphql_types:
                self.all_graphql_objects[type_.name] = type_
                # TODO: need a special method for each graph type
                self.references[type_.name] = Reference(
                    path=f'{str(*paths)}/{resolved_type.value}/{type_.name}',
                    name=type_.name,
                    original_name=type_.name,
                )

                self.support_graphql_types[resolved_type].append(type_)

    def _typename_field(self, name: str) -> DataModelFieldBase:
        return self.data_model_field_type(
            name='typename__',
            data_type=DataType(literals=[name]),
            default=name,
            required=False,
            alias='__typename',
            use_one_literal_as_default=True,
            has_default=True,
        )

    def parse_scalar(self, scalar_graphql_object: graphql.GraphQLScalarType) -> None:
        self.results.append(
            self.data_model_scalar_type(
                reference=self.references[scalar_graphql_object.name],
                fields=[],
                custom_template_dir=self.custom_template_dir,
                extra_template_data=self.extra_template_data,
                description=scalar_graphql_object.description,
            )
        )

    def parse_enum(self, enum_object: graphql.GraphQLEnumType) -> None:
        enum_fields: List[DataModelFieldBase] = []
        exclude_field_names: Set[str] = set()

        for value_name, value in enum_object.values.items():
            default = (
                f"'{value_name.translate(escape_characters)}'"
                if isinstance(value_name, str)
                else value_name
            )

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

        enum = Enum(
            reference=self.references[enum_object.name],
            fields=enum_fields,
            path=self.current_source_path,
            description=enum_object.description,
            custom_template_dir=self.custom_template_dir,
        )
        self.results.append(enum)

    def parse_field(
        self,
        field_name: str,
        alias: str,
        field: Union[graphql.GraphQLField, graphql.GraphQLInputField],
    ) -> DataModelFieldBase:
        final_data_type = DataType(is_optional=True)
        data_type = final_data_type
        obj = field.type

        while graphql.is_list_type(obj) or graphql.is_non_null_type(obj):
            if graphql.is_list_type(obj):
                data_type.is_list = True

                new_data_type = DataType(is_optional=True)
                data_type.data_types = [new_data_type]

                data_type = new_data_type
            elif graphql.is_non_null_type(obj):
                data_type.is_optional = False

            obj = obj.of_type

        data_type.type = obj.name

        required = (not self.force_optional_for_required_fields) and (
            not final_data_type.is_optional
        )
        extras = {}

        if hasattr(field, 'default_value'):
            if field.default_value == graphql.pyutils.Undefined:
                default = None
            else:
                default = field.default_value
        else:
            if required is False:
                if final_data_type.is_list:
                    default = 'list'
                    extras = {'default_factory': 'list'}
                else:
                    default = None
            else:
                default = None

        return self.data_model_field_type(
            name=field_name,
            default=default,
            data_type=final_data_type,
            required=required,
            extras=extras,
            alias=alias,
            strip_default_none=self.strip_default_none,
            use_annotated=self.use_annotated,
            use_field_description=field.description is not None,
            use_default_kwarg=self.use_default_kwarg,
            original_name=field_name,
            has_default=default is not None,
        )

    def parse_object_like(
        self,
        obj: Union[
            graphql.GraphQLInterfaceType,
            graphql.GraphQLObjectType,
            graphql.GraphQLInputObjectType,
        ],
    ) -> None:
        fields = []
        exclude_field_names: Set[str] = set()

        for field_name, field in obj.fields.items():
            field_name_, alias = self.model_resolver.get_valid_field_name_and_alias(
                field_name, excludes=exclude_field_names
            )
            exclude_field_names.add(field_name_)

            data_model_field_type = self.parse_field(field_name_, alias, field)
            fields.append(data_model_field_type)

        fields.append(self._typename_field(obj.name))

        base_classes = []
        if hasattr(obj, 'interfaces'):
            base_classes = [self.references[i.name] for i in obj.interfaces]

        data_model_type = self.data_model_type(
            reference=self.references[obj.name],
            fields=fields,
            base_classes=base_classes,
            custom_base_class=self.base_class,
            custom_template_dir=self.custom_template_dir,
            extra_template_data=self.extra_template_data,
            path=self.current_source_path,
            description=obj.description,
        )
        self.results.append(data_model_type)

    def parse_interface(
        self, interface_graphql_object: graphql.GraphQLInterfaceType
    ) -> None:
        self.parse_object_like(interface_graphql_object)

    def parse_object(self, graphql_object: graphql.GraphQLObjectType) -> None:
        self.parse_object_like(graphql_object)

    def parse_input_object(
        self, input_graphql_object: graphql.GraphQLInputObjectType
    ) -> None:
        self.parse_object_like(input_graphql_object)

    def parse_union(self, union_object: graphql.GraphQLUnionType) -> None:
        fields = []

        for type_ in union_object.types:
            fields.append(
                self.data_model_field_type(name=type_.name, data_type=DataType())
            )

        data_model_type = self.data_model_union_type(
            reference=self.references[union_object.name],
            fields=fields,
            custom_base_class=self.base_class,
            custom_template_dir=self.custom_template_dir,
            extra_template_data=self.extra_template_data,
            path=self.current_source_path,
            description=union_object.description,
        )
        self.results.append(data_model_type)

    def parse_raw(self) -> None:
        self.all_graphql_objects = {}
        self.references: Dict[str, Reference] = {}

        self.support_graphql_types = {
            graphql.type.introspection.TypeKind.SCALAR: [],
            graphql.type.introspection.TypeKind.ENUM: [],
            graphql.type.introspection.TypeKind.UNION: [],
            graphql.type.introspection.TypeKind.INTERFACE: [],
            graphql.type.introspection.TypeKind.OBJECT: [],
            graphql.type.introspection.TypeKind.INPUT_OBJECT: [],
        }

        # may be as a parameter in the future (??)
        _mapper_from_graphql_type_to_parser_method = {
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
                    parser_ = _mapper_from_graphql_type_to_parser_method[next_type]
                    parser_(obj)  # type: ignore
