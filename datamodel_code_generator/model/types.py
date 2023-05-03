from typing import Any, Dict, Optional, Sequence, Type

from datamodel_code_generator import PythonVersion
from datamodel_code_generator.imports import IMPORT_ANY, IMPORT_DECIMAL
from datamodel_code_generator.types import DataType, StrictTypes, Types
from datamodel_code_generator.types import DataTypeManager as _DataTypeManager


def type_map_factory(
    data_type: Type[DataType],
) -> Dict[Types, DataType]:
    data_type_int = data_type(type='int')
    data_type_float = data_type(type='float')
    data_type_str = data_type(type='str')
    return {
        # TODO: Should we support a special type such UUID?
        Types.integer: data_type_int,
        Types.int32: data_type_int,
        Types.int64: data_type_int,
        Types.number: data_type_float,
        Types.float: data_type_float,
        Types.double: data_type_float,
        Types.decimal: data_type.from_import(IMPORT_DECIMAL),
        Types.time: data_type_str,
        Types.string: data_type_str,
        Types.byte: data_type_str,  # base64 encoded string
        Types.binary: data_type(type='bytes'),
        Types.date: data_type_str,
        Types.date_time: data_type_str,
        Types.password: data_type_str,
        Types.email: data_type_str,
        Types.uuid: data_type_str,
        Types.uuid1: data_type_str,
        Types.uuid2: data_type_str,
        Types.uuid3: data_type_str,
        Types.uuid4: data_type_str,
        Types.uuid5: data_type_str,
        Types.uri: data_type_str,
        Types.hostname: data_type_str,
        Types.ipv4: data_type_str,
        Types.ipv6: data_type_str,
        Types.ipv4_network: data_type_str,
        Types.ipv6_network: data_type_str,
        Types.boolean: data_type(type='bool'),
        Types.object: data_type.from_import(IMPORT_ANY, is_dict=True),
        Types.null: data_type(type='None'),
        Types.array: data_type.from_import(IMPORT_ANY, is_list=True),
        Types.any: data_type.from_import(IMPORT_ANY),
    }


class DataTypeManager(_DataTypeManager):
    def __init__(
        self,
        python_version: PythonVersion = PythonVersion.PY_37,
        use_standard_collections: bool = False,
        use_generic_container_types: bool = False,
        strict_types: Optional[Sequence[StrictTypes]] = None,
        use_non_positive_negative_number_constrained_types: bool = False,
        use_union_operator: bool = False,
    ):
        super().__init__(
            python_version,
            use_standard_collections,
            use_generic_container_types,
            strict_types,
            use_non_positive_negative_number_constrained_types,
            use_union_operator,
        )

        self.type_map: Dict[Types, DataType] = type_map_factory(
            self.data_type,
        )

    def get_data_type(
        self,
        types: Types,
        **_: Any,
    ) -> DataType:
        return self.type_map[types]
