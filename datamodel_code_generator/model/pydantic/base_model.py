from typing import Dict, List, Optional

from datamodel_code_generator.model import DataModel, DataModelField
from datamodel_code_generator.model.base import Types
from datamodel_code_generator.types import DataType, Import

type_map: Dict[Types, DataType] = {
    Types.int32: DataType(type='int'),
    Types.int64: DataType(type='int'),
    Types.float: DataType(type='float'),
    Types.double: DataType(type='float'),
    Types.time: DataType(type='time'),
    Types.string: DataType(type='str'),
    Types.byte: DataType(type='str'),  # base64 encoded string
    Types.binary: DataType(type='bytes'),
    Types.date: DataType(type='date'),
    Types.date_time: DataType(type='datetime'),
    Types.password: DataType(
        type='SecretStr', import_=Import(from_='pydantic', import_='SecretStr')
    ),
    Types.email: DataType(
        type='EmailStr', import_=Import(from_='pydantic', import_='EmailStr')
    ),
    Types.uuid: DataType(type='UUID', import_=Import(from_='pydantic', import_='UUID')),
    Types.uuid1: DataType(
        type='UUID1', import_=Import(from_='pydantic', import_='UUID1')
    ),
    Types.uuid2: DataType(
        type='UUID2', import_=Import(from_='pydantic', import_='UUID2')
    ),
    Types.uuid3: DataType(
        type='UUID3', import_=Import(from_='pydantic', import_='UUID3')
    ),
    Types.uuid4: DataType(
        type='UUID4', import_=Import(from_='pydantic', import_='UUID4')
    ),
    Types.uuid5: DataType(
        type='UUID5', import_=Import(from_='pydantic', import_='UUID5')
    ),
    Types.uri: DataType(
        type='UrlStr', import_=Import(from_='pydantic', import_='UrlStr')
    ),
    Types.ipv4: DataType(
        type='IPv4Address', import_=Import(from_='pydantic', import_='IPv4Address')
    ),
    Types.ipv6: DataType(
        type='IPv6Address', import_=Import(from_='pydantic', import_='IPv6Address')
    ),
    Types.boolean: DataType(type='bool'),
}


class BaseModel(DataModel):
    TEMPLATE_FILE_PATH = 'pydantic/BaseModel.jinja2'
    BASE_CLASS = 'BaseModel'
    FROM_ = 'pydantic'
    IMPORT_ = 'BaseModel'
    DATA_TYPE_MAP: Dict[Types, DataType] = type_map

    def __init__(
        self,
        name: str,
        fields: List[DataModelField],
        decorators: Optional[List[str]] = None,
    ):
        super().__init__(name=name, fields=fields, decorators=decorators)
