from typing import ClassVar, Optional, Tuple, List
from keyword import iskeyword
import re
import builtins

from datamodel_code_generator.imports import Import
from datamodel_code_generator.model.base import DataModelFieldBase, DataModel
from datamodel_code_generator.model.schematics.imports import IMPORT_MODEL, IMPORT_LIST, IMPORT_DICT
from datamodel_code_generator.types import chain_as_tuple, DataType


class SchematicsModelField(DataModelFieldBase):

    @property
    def serialized_name(self) -> str:
        return f"'{self.name}'"

    @property
    def imports(self) -> Tuple[Import, ...]:
        imports_ = ()
        if self.data_type.is_list:
            imports_ = chain_as_tuple(imports_, (IMPORT_LIST,))
        if self.data_type.is_dict:
            imports_ = chain_as_tuple(imports_, (IMPORT_DICT,))
        if self.is_model_type:
            imports_ = chain_as_tuple(imports_, (IMPORT_MODEL,))

        return chain_as_tuple(self.data_type.all_imports, imports_)

    @property
    def is_model_type(self) -> bool:
        return self.data_type.reference if self.data_type.reference is not None \
            else len(self.data_type.data_types) > 0 and self.data_type.data_types[-1].reference is not None

    @property
    def model_name(self) -> Optional[str]:
        return self.data_type.reference.name if self.data_type.reference is not None \
            else self.data_type.data_types[-1].reference.name if len(self.data_type.data_types) > 0 else None

    @property
    def is_required(self) -> bool:
        return self.nullable is not None and self.nullable or self.required

    @property
    def snakecase_name(self) -> str:
        if not self.name:
            # We don't want to this this case ever
            return 'NO_FIELD_SET'

        name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', self.name)
        snakecase = re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()

        # If var shadowing builtin, mutate. i.e. `id` > `_id`
        if iskeyword(snakecase):
            snakecase = f'_{snakecase}'
        return snakecase

    @property
    def is_list(self) -> bool:
        return self.data_type.is_list

    @property
    def is_dict(self) -> bool:
        return self.data_type.is_dict

    @property
    def is_nested_type(self) -> bool:
        return self.is_list or self.is_dict

    @property
    def data_types(self) -> list:
        return self.data_type.data_types

    @property
    def inline_value(self) -> str:
        def _create_type_string(types_list: list) -> str:
            """
            Takes in list of types and formats them into schematics format

            Returns of recursion of ['ListType', 'DictType', 'StringType'] will return for each subsequent call
            [1] > 'StringType()'
            [2] > 'DictType(StringType)'
            [3] > 'ListType(DictType(StringType()), required=True)'


            :param list[str] types_list: List of types, ex ['ListType', 'DictType', 'StringType']
            :return: formatted string. ex 'ListType(DictType(StringType), serialized_name='blah', required=False)'
            """

            def recurse(sublist: List[DataType], is_top_level: bool = False):

                outer = sublist[0]
                is_model_type = outer.reference is not None

                # Is model type if reference attr exists
                if outer.is_list:
                    outer_type = 'ListType'
                elif outer.is_enum:
                    outer_type = 'StringType'
                elif outer.is_dict:
                    outer_type = 'DictType'
                elif is_model_type:
                    outer_type = 'ModelType'
                else:
                    outer_type = outer.full_name

                inner_type = recurse(sublist[1:]) if len(sublist) > 1 else None

                # Format kwargs for Type here. Will output in key=value format,
                # i.e., {'required':True, 'serialized_name':'id'} > outputs > '(required=True, serialized_name=id)'
                extra_kwargs = dict()

                if is_top_level:
                    extra_kwargs['required'] = not self.data_type.is_optional

                if outer.is_enum:
                    extra_kwargs['choices'] = [field.name for field in outer.reference.source.fields]

                if is_top_level and self.name and self.name != self.snakecase_name:
                    extra_kwargs['serialized_name'] = self.serialized_name

                extra_kwarg_string = ((', ' if inner_type and extra_kwargs else '') + ", ".join(f"{key}={value}"
                                                                                                for key, value in
                                                                                                extra_kwargs.items()))

                if is_model_type:
                    if outer.is_enum:
                        return f'StringType({extra_kwarg_string})' if is_top_level else f'StringType, {extra_kwarg_string}'

                    # If this is the top level, give it kwarg string, if its nested, don't
                    extra = f', {extra_kwarg_string}' if is_top_level else ''
                    return f'ModelType({outer.reference.name}{extra})'

                if not is_top_level and not is_model_type:
                    return outer_type

                return f'{outer_type}({f"{inner_type}" if inner_type else ""}{extra_kwarg_string})'

            return recurse(types_list, is_top_level=True)

        data_types = [self.data_type] + self.data_type.data_types
        assembled_string = _create_type_string(data_types)

        return assembled_string


class BaseModel(DataModel):
    TEMPLATE_FILE_PATH: ClassVar[str] = 'schematics/BaseModel.jinja2'
    BASE_CLASS: ClassVar[str] = 'schematics.BaseModel'

    @property
    def imports(self) -> Tuple[Import, ...]:
        return chain_as_tuple(
            (i for f in self.fields for i in f.imports), self._additional_imports
        )
