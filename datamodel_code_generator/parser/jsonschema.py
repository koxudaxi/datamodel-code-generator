from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from ..parser.base import Parser
from ..types import Types


def get_model_by_path(schema: Dict[str, Any], keys: List[str]) -> Dict:
    if len(keys) == 1:
        return schema[keys[0]]
    return get_model_by_path(schema[keys[0]], keys[1:])


json_schema_data_formats: Dict[str, Dict[str, Types]] = {
    'integer': {'int32': Types.int32, 'int64': Types.int64, 'default': Types.integer},
    'number': {
        'float': Types.float,
        'double': Types.double,
        'time': Types.time,
        'default': Types.number,
    },
    'string': {
        'default': Types.string,
        'byte': Types.byte,  # base64 encoded string
        'binary': Types.binary,
        'date': Types.date,
        'date-time': Types.date_time,
        'password': Types.password,
        'email': Types.email,
        'uuid': Types.uuid,
        'uuid1': Types.uuid1,
        'uuid2': Types.uuid2,
        'uuid3': Types.uuid3,
        'uuid4': Types.uuid4,
        'uuid5': Types.uuid5,
        'uri': Types.uri,
        'ipv4': Types.ipv4,
        'ipv6': Types.ipv6,
    },
    'boolean': {'default': Types.boolean},
    'object': {'default': Types.object},
}


class JsonSchemaObject(BaseModel):
    items: Union[List['JsonSchemaObject'], 'JsonSchemaObject', None]
    uniqueItem: Optional[bool]
    type: Optional[str]
    format: Optional[str]
    pattern: Optional[str]
    minLength: Optional[int]
    maxLength: Optional[int]
    minimum: Optional[float]
    maximum: Optional[float]
    multipleOf: Optional[float]
    exclusiveMaximum: Optional[bool]
    exclusiveMinimum: Optional[bool]
    additionalProperties: Union['JsonSchemaObject', bool, None]
    anyOf: List['JsonSchemaObject'] = []
    allOf: List['JsonSchemaObject'] = []
    enum: List[str] = []
    writeOnly: Optional[bool]
    properties: Optional[Dict[str, 'JsonSchemaObject']]
    required: List[str] = []
    ref: Optional[str] = Field(default=None, alias='$ref')  # type: ignore
    nullable: Optional[bool] = False
    x_enum_varnames: List[str] = Field(  # type: ignore
        default=[], alias='x-enum-varnames'
    )

    @property
    def is_object(self) -> bool:
        return self.properties is not None or self.type == 'object'

    @property
    def is_array(self) -> bool:
        return self.items is not None or self.type == 'array'

    @property
    def ref_object_name(self) -> str:
        return self.ref.rsplit('/', 1)[-1]  # type: ignore


JsonSchemaObject.update_forward_refs()


def parse_ref(obj: JsonSchemaObject, parser: Parser) -> None:
    if obj.ref:
        ref: str = obj.ref
        # https://swagger.io/docs/specification/using-ref/
        if obj.ref.startswith('#'):
            # Local Reference – $ref: '#/definitions/myElement'
            pass
        elif '://' in ref:
            # URL Reference – $ref: 'http://path/to/your/resource' Uses the whole document located on the different server.
            raise NotImplementedError(f'URL Reference is not supported. $ref:{ref}')

        else:
            # Remote Reference – $ref: 'document.json' Uses the whole document located on the same server and in the same location.
            # TODO treat edge case
            relative_path, object_path = ref.split('#/')
            full_path = parser.base_path / relative_path
            with full_path.open() as f:
                if full_path.suffix.lower() == '.json':
                    import json

                    ref_body: Dict[str, Any] = json.load(f)
                else:
                    # expect yaml
                    import yaml

                    ref_body = yaml.safe_load(f)
                object_parents = object_path.split('/')
                ref_path = str(full_path) + '#/' + object_path
                if ref_path not in parser.excludes_ref_path:
                    parser.excludes_ref_path.add(str(full_path) + '#/' + object_path)
                    model = get_model_by_path(ref_body, object_parents)
                    parser.parse_raw(object_parents[-1], model)

    if obj.items:
        if isinstance(obj.items, JsonSchemaObject):
            parse_ref(obj.items, parser)
        else:
            for item in obj.items:
                parse_ref(item, parser)
    if isinstance(obj.additionalProperties, JsonSchemaObject):
        parse_ref(obj.additionalProperties, parser)
    for item in obj.anyOf:
        parse_ref(item, parser)
    for item in obj.allOf:
        parse_ref(item, parser)
    if obj.properties:
        for value in obj.properties.values():
            parse_ref(value, parser)
