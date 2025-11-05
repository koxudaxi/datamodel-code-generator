from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable
from urllib.parse import ParseResult

from datamodel_code_generator import (
    DefaultPutDict,
    LiteralType,
    PythonVersion,
    PythonVersionMin,
    snooper_to_methods,
)
from datamodel_code_generator.model import DataModel, DataModelFieldBase
from datamodel_code_generator.model import strawberry as strawberry_model
from datamodel_code_generator.model.dataclass import DataClass
from datamodel_code_generator.model.enum import Enum
from datamodel_code_generator.model.scalar import DataTypeScalar
from datamodel_code_generator.model.union import DataTypeUnion
from datamodel_code_generator.parser.base import (
    DataType,
    Parser,
    Source,
    escape_characters,
)
from datamodel_code_generator.parser.graphql import GraphQLParser, build_graphql_schema
from datamodel_code_generator.reference import ModelType, Reference
from datamodel_code_generator.types import DataTypeManager, StrictTypes, Types

try:
    import graphql
except ImportError as exc:  # pragma: no cover
    msg = "Please run `$pip install 'datamodel-code-generator[graphql]`' to generate data-model from a GraphQL schema."
    raise Exception(msg) from exc  # noqa: TRY002

from datamodel_code_generator.format import DEFAULT_FORMATTERS, DatetimeClassType, Formatter

if TYPE_CHECKING:
    from collections import defaultdict
    from collections.abc import Iterable, Iterator, Mapping, Sequence


@snooper_to_methods()
class StrawberryGraphQLParser(GraphQLParser):
    """GraphQL parser that generates Strawberry GraphQL types."""
    
    def __init__(  # noqa: PLR0913
        self,
        source: str | Path | ParseResult,
        *,
        data_model_type: type[DataModel] = strawberry_model.BaseModel,
        data_model_root_type: type[DataModel] = strawberry_model.RootModel,
        data_model_scalar_type: type[DataModel] = DataTypeScalar,
        data_model_union_type: type[DataModel] = DataTypeUnion,
        data_type_manager_type: type[DataTypeManager] = strawberry_model.DataTypeManager,
        data_model_field_type: type[DataModelFieldBase] = strawberry_model.DataModelField,
        base_class: str | None = None,
        additional_imports: list[str] | None = None,
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
        force_optional_for_required_fields: bool = False,
        class_name: str | None = None,
        use_standard_collections: bool = False,
        base_path: Path | None = None,
        use_schema_description: bool = False,
        use_field_description: bool = False,
        use_default_kwarg: bool = False,
        reuse_model: bool = False,
        encoding: str = "utf-8",
        enum_field_as_literal: LiteralType | None = None,
        set_default_enum_member: bool = False,
        use_subclass_enum: bool = False,
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
        wrap_string_literal: bool | None = None,
        use_title_as_name: bool = False,
        use_operation_id_as_name: bool = False,
        use_unique_items_as_set: bool = False,
        http_headers: Sequence[tuple[str, str]] | None = None,
        http_ignore_tls: bool = False,
        use_annotated: bool = False,
        use_non_positive_negative_number_constrained_types: bool = False,
        original_field_name_delimiter: str | None = None,
        use_double_quotes: bool = False,
        use_union_operator: bool = False,
        allow_responses_without_content: bool = False,
        collapse_root_models: bool = False,
        special_field_name_prefix: str | None = None,
        remove_special_field_name_prefix: bool = False,
        capitalise_enum_members: bool = False,
        keep_model_order: bool = False,
        use_one_literal_as_default: bool = False,
        known_third_party: list[str] | None = None,
        custom_formatters: list[str] | None = None,
        custom_formatters_kwargs: dict[str, Any] | None = None,
        use_pendulum: bool = False,
        http_query_parameters: Sequence[tuple[str, str]] | None = None,
        treat_dot_as_module: bool = False,
        use_exact_imports: bool = False,
        default_field_extras: dict[str, Any] | None = None,
        target_datetime_class: DatetimeClassType = DatetimeClassType.Datetime,
        keyword_only: bool = False,
        frozen_dataclasses: bool = False,
        no_alias: bool = False,
        formatters: list[Formatter] = DEFAULT_FORMATTERS,
        parent_scoped_naming: bool = False,
        scalars_from_import: str | None = None,
    ) -> None:
        super().__init__(
            source=source,
            data_model_type=data_model_type,
            data_model_root_type=data_model_root_type,
            data_model_scalar_type=data_model_scalar_type,
            data_model_union_type=data_model_union_type,
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
            apply_default_values_for_required_fields=apply_default_values_for_required_fields,
            allow_extra_fields=allow_extra_fields,
            extra_fields=extra_fields,
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
            use_one_literal_as_default=use_one_literal_as_default,
            known_third_party=known_third_party,
            custom_formatters=custom_formatters,
            custom_formatters_kwargs=custom_formatters_kwargs,
            use_pendulum=use_pendulum,
            http_query_parameters=http_query_parameters,
            treat_dot_as_module=treat_dot_as_module,
            use_exact_imports=use_exact_imports,
            default_field_extras=default_field_extras,
            target_datetime_class=target_datetime_class,
            keyword_only=keyword_only,
            frozen_dataclasses=frozen_dataclasses,
            no_alias=no_alias,
            formatters=formatters,
            parent_scoped_naming=parent_scoped_naming,
        )
        self.custom_scalar_import_from = scalars_from_import

    def parse_enum(self, enum_object: graphql.GraphQLEnumType) -> None:
        """Parse GraphQL enum to Strawberry enum."""
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
                    data_type=self.data_type_manager.get_data_type(Types.string),
                    default=default,
                    required=True,
                    strip_default_none=self.strip_default_none,
                    has_default=True,
                    use_field_description=value.description is not None,
                    original_name=None,
                )
            )

        enum = strawberry_model.Enum(
            reference=self.references[enum_object.name],
            fields=enum_fields,
            custom_template_dir=self.custom_template_dir,
            extra_template_data=self.extra_template_data,
            path=self.current_source_path,
            description=enum_object.description,
            treat_dot_as_module=self.treat_dot_as_module,
        )
        self.results.append(enum)

    def parse_input_object(self, input_graphql_object: graphql.GraphQLInputObjectType) -> None:
        """Parse GraphQL input object to Strawberry input."""
        fields = []
        exclude_field_names: set[str] = set()

        for field_name, field in input_graphql_object.fields.items():
            field_name_, alias = self.model_resolver.get_valid_field_name_and_alias(
                field_name, excludes=exclude_field_names
            )
            exclude_field_names.add(field_name_)

            data_model_field_type = self.parse_field(field_name_, alias, field, original_name=field_name)
            fields.append(data_model_field_type)

        # Don't add typename field for input objects
        base_classes = []

        data_model_type = strawberry_model.Input(
            reference=self.references[input_graphql_object.name],
            fields=fields,
            base_classes=base_classes,
            custom_base_class=self.base_class,
            custom_template_dir=self.custom_template_dir,
            extra_template_data=self.extra_template_data,
            path=self.current_source_path,
            description=input_graphql_object.description,
            keyword_only=self.keyword_only,
            treat_dot_as_module=self.treat_dot_as_module,
        )
        self.results.append(data_model_type)

    def parse_object_like(
        self,
        obj: graphql.GraphQLInterfaceType | graphql.GraphQLObjectType | graphql.GraphQLInputObjectType,
    ) -> None:
        """Parse GraphQL object-like types to appropriate Strawberry types."""
        fields = []
        exclude_field_names: set[str] = set()

        for field_name, field in obj.fields.items():
            field_name_, alias = self.model_resolver.get_valid_field_name_and_alias(
                field_name, excludes=exclude_field_names
            )
            exclude_field_names.add(field_name_)

            data_model_field_type = self.parse_field(field_name_, alias, field, original_name=field_name)
            fields.append(data_model_field_type)

        # Don't add typename field for Strawberry types
        base_classes = []
        if hasattr(obj, "interfaces"):  # pragma: no cover
            base_classes = [self.references[i.name] for i in obj.interfaces]  # pyright: ignore[reportAttributeAccessIssue]

        # Use appropriate Strawberry model type based on GraphQL type
        if isinstance(obj, graphql.GraphQLInputObjectType):
            data_model_type = strawberry_model.Input(
                reference=self.references[obj.name],
                fields=fields,
                base_classes=base_classes,
                custom_base_class=self.base_class,
                custom_template_dir=self.custom_template_dir,
                extra_template_data=self.extra_template_data,
                path=self.current_source_path,
                description=obj.description,
                keyword_only=self.keyword_only,
                treat_dot_as_module=self.treat_dot_as_module,
            )
        else:
            # For objects and interfaces, use @strawberry.type
            data_model_type = strawberry_model.BaseModel(
                reference=self.references[obj.name],
                fields=fields,
                base_classes=base_classes,
                custom_base_class=self.base_class,
                custom_template_dir=self.custom_template_dir,
                extra_template_data=self.extra_template_data,
                path=self.current_source_path,
                description=obj.description,
                keyword_only=self.keyword_only,
                treat_dot_as_module=self.treat_dot_as_module,
            )
        
        self.results.append(data_model_type)

    def parse_field(
        self,
        field_name: str,
        alias: str | None,
        field: graphql.GraphQLField | graphql.GraphQLInputField,
        original_name: str | None = None,
        ) -> DataModelFieldBase:
        """Parse GraphQL field with proper type mapping."""
        final_data_type = DataType(
            is_optional=True,
            use_union_operator=self.use_union_operator,
            use_standard_collections=self.use_standard_collections,
        )
        data_type = final_data_type
        obj = field.type
        original_is_non_null = graphql.is_non_null_type(obj)

        # Track if we're in a list
        is_list = False
        while graphql.is_list_type(obj) or graphql.is_non_null_type(obj):
            if graphql.is_list_type(obj):
                is_list = True
                data_type.is_list = True

                new_data_type = DataType(
                    is_optional=True,
                    use_union_operator=self.use_union_operator,
                    use_standard_collections=self.use_standard_collections,
                )
                data_type.data_types = [new_data_type]

                data_type = new_data_type
            elif graphql.is_non_null_type(obj):
                data_type.is_optional = False

            obj = graphql.assert_wrapping_type(obj)
            obj = obj.of_type

        # Save the unwrapped GraphQL type for enum checking later
        unwrapped_graphql_type = obj
        
        # Check if it's an enum and save the enum info
        is_enum = graphql.is_enum_type(obj)
        enum_name_for_default = None
        if is_enum:
            obj = graphql.assert_enum_type(obj)
            data_type.reference = self.references[obj.name]
            enum_name_for_default = obj.name  # Save enum name for default formatting

        obj = graphql.assert_named_type(obj)
        
        # Map GraphQL built-in types to Python types
        graphql_to_python = {
            "String": "str",
            "Int": "int", 
            "Float": "float",
            "Boolean": "bool",
            "ID": "strawberry.ID",
        }
        
        # Set the inner type for lists or the direct type
        inner_type_name = obj.name
        if inner_type_name in graphql_to_python:
            if inner_type_name == "ID":
                if is_list:
                    # For lists like [ID!], update the inner data_type to use ID import
                    if final_data_type.data_types:
                        inner_dt = final_data_type.data_types[0]
                        inner_data_type = DataType.from_import(
                            strawberry_model.imports.IMPORT_STRAWBERRY_ID,
                            is_optional=inner_dt.is_optional,
                        )
                        # Copy other properties
                        inner_data_type.use_union_operator = inner_dt.use_union_operator
                        inner_data_type.use_standard_collections = inner_dt.use_standard_collections
                        final_data_type.data_types[0] = inner_data_type
                    else:
                        # Create new data type for list element
                        inner_data_type = DataType.from_import(
                            strawberry_model.imports.IMPORT_STRAWBERRY_ID,
                            is_optional=False,  # Non-nullable in [ID!]
                        )
                        inner_data_type.use_union_operator = self.use_union_operator
                        inner_data_type.use_standard_collections = self.use_standard_collections
                        final_data_type.data_types = [inner_data_type]
                else:
                    final_data_type = DataType.from_import(strawberry_model.imports.IMPORT_STRAWBERRY_ID)
            else:
                if is_list:
                    # Update the inner data_type
                    if final_data_type.data_types:
                        final_data_type.data_types[0].type = graphql_to_python[inner_type_name]
                    else:
                        inner_data_type = DataType(
                            type=graphql_to_python[inner_type_name],
                            is_optional=False,
                            use_union_operator=self.use_union_operator,
                            use_standard_collections=self.use_standard_collections,
                        )
                        final_data_type.data_types = [inner_data_type]
                else:
                    final_data_type.type = graphql_to_python[inner_type_name]
        else:
            if is_list:
                # Update the inner data_type
                if final_data_type.data_types:
                    final_data_type.data_types[0].type = inner_type_name
                    if graphql.is_enum_type(obj):
                        final_data_type.data_types[0].reference = self.references[inner_type_name]
                else:
                    inner_data_type = DataType(
                        type=inner_type_name,
                        is_optional=False,
                        use_union_operator=self.use_union_operator,
                        use_standard_collections=self.use_standard_collections,
                    )
                    if inner_type_name in self.references:
                        inner_data_type.reference = self.references[inner_type_name]
                    final_data_type.data_types = [inner_data_type]
            else:
                final_data_type.type = inner_type_name

        required = (not self.force_optional_for_required_fields) and (not final_data_type.is_optional)

        # Override _get_default to handle defaults even for required fields
        default = None
        if isinstance(field, graphql.GraphQLInputField):
            try:
                from graphql import Undefined
            except ImportError:
                Undefined = object()
            
            if hasattr(field, 'default_value') and field.default_value is not Undefined:
                default_value_obj = field.default_value
                # Convert scalar default values to their Python equivalents
                if isinstance(default_value_obj, str):
                    # Check if this field type is an enum FIRST - enum defaults take precedence
                    # Use the enum name we saved earlier, or check the schema
                    if enum_name_for_default and hasattr(self, 'raw_obj') and self.raw_obj:
                        # We know it's an enum from the earlier check
                        graphql_type = self.raw_obj.type_map.get(enum_name_for_default)
                        if graphql_type and graphql.is_enum_type(graphql_type):
                            enum_type = graphql.assert_enum_type(graphql_type)
                            # Verify the default value matches an enum member
                            if default_value_obj in enum_type.values.keys():
                                # Format as EnumName.MemberName
                                default = f"{enum_name_for_default}.{default_value_obj}"
                            else:
                                # Default doesn't match enum member, keep as string
                                default = default_value_obj
                        else:
                            # Fallback: check if it's a scalar type reference
                            scalar_types = {"ID", "String", "Int", "Float", "Boolean"}
                            if default_value_obj in scalar_types:
                                default = default_value_obj
                            else:
                                default = default_value_obj
                    else:
                        # Not an enum type - check if it's a scalar type reference (GraphQL scalar names)
                        scalar_types = {"ID", "String", "Int", "Float", "Boolean"}
                        # If the default is a scalar type name, use just the scalar name
                        # (since we import * from strawberry.scalars)
                        if default_value_obj in scalar_types:
                            default = default_value_obj  # Just "ID", not "strawberry.scalars.ID"
                        else:
                            # Regular string value, keep as string (will be quoted by repr)
                            default = default_value_obj
                elif isinstance(default_value_obj, bool):
                    # Keep as boolean (repr will handle it correctly)
                    default = default_value_obj
                elif isinstance(default_value_obj, (int, float)):
                    # Keep as number (repr will handle it correctly, no quotes)
                    default = default_value_obj
                elif default_value_obj is None:
                    default = None
                else:
                    # Check if it's a GraphQL scalar type object
                    if hasattr(default_value_obj, 'name'):
                        scalar_name = default_value_obj.name
                        scalar_types = {"ID", "String", "Int", "Float", "Boolean"}
                        if scalar_name in scalar_types:
                            default = scalar_name  # Just the scalar name
                        else:
                            default = default_value_obj
                    else:
                        default = default_value_obj

        if default is None:
            default = self._get_default(field, final_data_type, required)
        
        # Set has_default if we have a default value
        has_default = default is not None
        
        extras = {} if self.default_field_extras is None else self.default_field_extras.copy()

        if field.description is not None:  # pragma: no cover
            extras["description"] = field.description

        return self.data_model_field_type(
            name=field_name,
            default=default,
            data_type=final_data_type,
            required=required,
            alias=alias,
            extras=extras,
            has_default=has_default,
            original_name=original_name or field_name,
        )

    def _resolve_types(self, paths: list[str], schema: graphql.GraphQLSchema) -> None:
        """Override to add directive support and track custom scalars."""
        # Call parent method first
        super()._resolve_types(paths, schema)
        
        # Track custom scalars (non-built-in)
        builtin_scalars = {"String", "Int", "Float", "Boolean", "ID"}
        custom_scalars = []
        for type_name, type_obj in schema.type_map.items():
            if isinstance(type_obj, graphql.GraphQLScalarType):
                if type_name not in builtin_scalars:
                    custom_scalars.append(type_name)
                    self.all_graphql_objects[type_name] = type_obj
                    self.references[type_name] = Reference(
                        path=f"{paths!s}/scalar/{type_name}",
                        name=type_name,
                        original_name=type_name,
                    )
        
        # Add import for custom scalars (only if scalars_from_import is provided)
        if custom_scalars and self.custom_scalar_import_from:
            from datamodel_code_generator.imports import Import
            # Sort scalars for consistent output
            sorted_scalars = sorted(custom_scalars)
            for scalar_name in sorted_scalars:
                scalar_import = Import(import_=scalar_name, from_=self.custom_scalar_import_from)
                self.imports.append(scalar_import)
        
        # Handle directives
        for directive in schema.directives:
            # Skip built-in directives
            if directive.name in {"deprecated", "include", "skip", "specifiedBy"}:
                continue
                
            self.all_graphql_objects[directive.name] = directive
            self.references[directive.name] = Reference(
                path=f"{paths!s}/directive/{directive.name}",
                name=directive.name,
                original_name=directive.name,
            )
            
            # Add to a special directives list
            if not hasattr(self, 'directives'):
                self.directives = []
            self.directives.append(directive)

    def parse_directive(self, directive: graphql.GraphQLDirective) -> None:
        """Parse GraphQL directive to Strawberry directive."""
        # Map GraphQL directive locations to Strawberry Location enum values
        graphql_to_strawberry_location = {
            "schema": "SCHEMA",
            "scalar": "SCALAR",
            "object": "OBJECT",
            "field definition": "FIELD_DEFINITION",
            "argument definition": "ARGUMENT_DEFINITION",
            "interface": "INTERFACE",
            "union": "UNION",
            "enum": "ENUM",
            "enum value": "ENUM_VALUE",
            "input object": "INPUT_OBJECT",
            "input field definition": "INPUT_FIELD_DEFINITION",
        }
        
        locations = []
        for location in directive.locations:
            # GraphQL locations are DirectiveLocation enum values with a .value attribute
            if hasattr(location, 'value'):
                location_str = location.value
            else:
                location_str = str(location)
            strawberry_location = graphql_to_strawberry_location.get(location_str.lower())
            if strawberry_location:
                locations.append(strawberry_location)
        
        fields = []
        exclude_field_names: set[str] = set()

        # Parse directive arguments
        for arg_name, arg in directive.args.items():
            field_name = self.model_resolver.get_valid_field_name(
                arg_name, excludes=exclude_field_names, model_type=ModelType.ENUM
            )
            exclude_field_names.add(field_name)

            # Check if the argument type is non-nullable (ends with !)
            is_non_null = graphql.is_non_null_type(arg.type)
            
            # Map GraphQL argument types to Python types
            arg_type = arg.type
            while graphql.is_non_null_type(arg_type):
                arg_type = arg_type.of_type
            
            if graphql.is_list_type(arg_type):
                arg_type = arg_type.of_type
                while graphql.is_non_null_type(arg_type):
                    arg_type = arg_type.of_type
                data_type = DataType(
                    type="list",
                    is_list=True,
                    is_optional=not is_non_null,  # Only optional if not non-null
                    use_union_operator=self.use_union_operator,
                    use_standard_collections=self.use_standard_collections,
                )
            else:
                # Map GraphQL types to Python types
                type_name = arg_type.name if hasattr(arg_type, 'name') else str(arg_type)
                graphql_to_python = {
                    "String": "str",
                    "Int": "int", 
                    "Float": "float",
                    "Boolean": "bool",
                    "ID": "strawberry.ID",
                }
                
                if type_name in graphql_to_python:
                    if type_name == "ID":
                        data_type = DataType.from_import(
                            strawberry_model.imports.IMPORT_STRAWBERRY_ID,
                            is_optional=not is_non_null,
                        )
                    else:
                        data_type = DataType(
                            type=graphql_to_python[type_name],
                            is_optional=not is_non_null,
                        )
                else:
                    data_type = DataType(
                        type=type_name,
                        is_optional=not is_non_null,
                    )

            # Check if argument has a default value
            # GraphQL uses Undefined sentinel object for arguments without defaults
            default = None
            if hasattr(arg, 'default_value'):
                try:
                    from graphql import Undefined
                except ImportError:
                    Undefined = object()  # Fallback if Undefined is not available
                
                arg_default = arg.default_value
                # Only set default if it's not Undefined
                if arg_default is not Undefined:
                    # Check if this argument type is an enum
                    if graphql.is_enum_type(arg_type):
                        enum_type = graphql.assert_enum_type(arg_type)
                        enum_name = enum_type.name if hasattr(enum_type, 'name') else str(arg_type)
                        # If default is a string and matches an enum member
                        if isinstance(arg_default, str) and arg_default in enum_type.values.keys():
                            # Format as EnumName.MemberName
                            default = f"{enum_name}.{arg_default}"
                        else:
                            default = str(arg_default)
                    elif isinstance(arg_default, str):
                        # Check if it's a scalar type reference
                        scalar_types = {"ID", "String", "Int", "Float", "Boolean"}
                        if arg_default in scalar_types:
                            default = arg_default  # Just the scalar name
                        else:
                            # Regular string value, keep as string (will be quoted by repr in template)
                            default = arg_default
                    elif isinstance(arg_default, bool):
                        # Keep as boolean (repr will handle it correctly)
                        default = arg_default
                    elif isinstance(arg_default, (int, float)):
                        # Keep as number (repr will handle it correctly, no quotes)
                        default = arg_default
                    elif arg_default is None:
                        default = None
                    else:
                        # Check if it's a GraphQL scalar type object
                        if hasattr(arg_default, 'name'):
                            scalar_name = arg_default.name
                            scalar_types = {"ID", "String", "Int", "Float", "Boolean"}
                            if scalar_name in scalar_types:
                                default = scalar_name  # Just the scalar name
                            else:
                                default = str(arg_default)
                        else:
                            default = str(arg_default)
            
            # Required is True if non-null AND no default value
            required = is_non_null and default is None
            
            # Only pass default if there's an actual default value
            field_kwargs = {
                'name': field_name,
                'data_type': data_type,
                'required': required,
                'description': arg.description,
            }
            if default is not None:
                field_kwargs['default'] = default
                # Set has_default flag so the template knows to render the default
                field_kwargs['has_default'] = True
            
            fields.append(
                self.data_model_field_type(**field_kwargs)
            )

        directive_model = strawberry_model.Directive(
            reference=self.references[directive.name],
            fields=fields,
            custom_template_dir=self.custom_template_dir,
            extra_template_data=self.extra_template_data,
            path=self.current_source_path,
            description=directive.description,
            treat_dot_as_module=self.treat_dot_as_module,
            locations=locations,
        )
        self.results.append(directive_model)

    def parse_scalar(self, scalar_graphql_object: graphql.GraphQLScalarType) -> None:
        """Skip scalar type generation for Strawberry - we don't need them."""
        # Don't generate scalar types for Strawberry GraphQL
        pass

    def parse_raw(self) -> None:
        """Override to add directive parsing."""
        # Call parent method first
        super().parse_raw()
        
        # Parse directives if they exist
        if hasattr(self, 'directives'):
            for directive in self.directives:
                self.parse_directive(directive)
