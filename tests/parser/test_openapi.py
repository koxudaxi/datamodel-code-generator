from pathlib import Path
from tempfile import NamedTemporaryFile

from datamodel_code_generator.model.base import TemplateBase
from datamodel_code_generator.model.pydantic import BaseModel, CustomRootType
from datamodel_code_generator.parser.base import DataType
from datamodel_code_generator.parser.openapi import (
    OpenAPIParser,
    dump_templates,
    get_data_type,
)

DATA_PATH: Path = Path(__file__).parents[1] / 'data'


class A(TemplateBase):
    def __init__(self, filename: str, data: str):
        self._data = data
        super().__init__(filename)

    def render(self) -> str:
        return self._data


def test_get_data_type():
    assert get_data_type('integer', 'int32') == DataType(type='int')
    assert get_data_type('integer', 'int64') == DataType(type='int')
    assert get_data_type('number', 'float') == DataType(type='float')
    assert get_data_type('number', 'double') == DataType(type='float')
    assert get_data_type('number', 'time') == DataType(type='time')
    assert get_data_type('string') == DataType(type='str')
    assert get_data_type('string', 'byte') == DataType(type='str')
    assert get_data_type('string', 'binary') == DataType(type='bytes')
    assert get_data_type('boolean') == DataType(type='bool')
    assert get_data_type('string') == DataType(type='str')
    assert get_data_type('string', 'date') == DataType(type='date')
    assert get_data_type('string', 'date-time') == DataType(type='datetime')
    assert get_data_type('string', 'password') == DataType(type='SecretStr')
    assert get_data_type('string', 'email') == DataType(type='EmailStr')
    assert get_data_type('string', 'uri') == DataType(type='UrlStr')
    assert get_data_type('string', 'ipv4') == DataType(type='IPv4Address')
    assert get_data_type('string', 'ipv6') == DataType(type='IPv6Address')


def test_dump_templates():
    with NamedTemporaryFile('w') as dummy_template:
        assert dump_templates(A(dummy_template.name, 'abc')) == 'abc'
        assert (
            dump_templates(
                [A(dummy_template.name, 'abc'), A(dummy_template.name, 'def')]
            )
            == 'abc\n\n\ndef'
        )


def test_openapi_parser_parse():
    parser = OpenAPIParser(
        BaseModel, CustomRootType, filename=str(DATA_PATH / 'api.yaml')
    )
    assert (
        parser.parse()
        == '''class Pet(BaseModel):
    id: int
    name: str
    tag: Optional[str] = None


class Pets(BaseModel):
    __root__: List[Pet] = None


class User(BaseModel):
    id: int
    name: str
    tag: Optional[str] = None


class Users(BaseModel):
    __root__: List[User] = None


class Id(BaseModel):
    __root__: str = None


class Rules(BaseModel):
    __root__: List[str] = None


class Error(BaseModel):
    code: int
    message: str


class api(BaseModel):
    apiKey: Optional[str] = None
    apiVersionNumber: Optional[str] = None


class apis(BaseModel):
    __root__: List[api] = None'''
    )
