from dataclasses import dataclass, Field
from typing import Dict, Type, Optional, List, Set

from datamodel_code_generator.model import DataModelField, CustomRootType, DataModel

from prance import ResolvingParser, BaseParser


@dataclass
class DataType:
    type_hint: str
    format: Optional[str] = None
    default: Optional[Field] = None


data_types: Dict[str, Dict[str, DataType]] = {
    # https://docs.python.org/3.7/library/json.html#encoders-and-decoders
    'integer':
        {
            'int32': DataType(type_hint='int'),
            'int64': DataType(type_hint='int')
         },
    'number':
        {
            'float': DataType(type_hint='float'),
            'double': DataType(type_hint='float')
        },
    'string':
        {   'default': DataType(type_hint='str'),
            'byte': DataType(type_hint='str'),
            'binary':  DataType(type_hint='bytes')
        },
#               'data': date,}, #As defined by full-date - RFC3339
    'boolean': {'default': DataType(type_hint='bool')}
}


def get_data_type(_type, format = None) -> DataType:
    _format: str = format or 'default'
    return data_types[_type][_format]


resolving_parser = ResolvingParser('api.yaml', backend = 'openapi-spec-validator')
base_parser = BaseParser('api.yaml', backend = 'openapi-spec-validator')




class Parser:
    def __init__(self, data_model_type: Type[DataModel], data_model_field_type: Type[DataModelField]):
        self.data_model_type:  Type[DataModel] = data_model_type
        self.data_model_field_type: Type[DataModelField] = data_model_field_type
        self.models = []

    def parse_object(self, name: str, obj: Dict):
        requires: Set[str] = set(obj.get('required', []))
        d_list: List[DataModelField] = []
        for field_name, filed in obj['properties'].items():
            # object
            d_list.append(self.data_model_field_type(
                name=field_name, type_hint=get_data_type(filed["type"],
                                                         filed.get("format")).type_hint,
                required=field_name in requires))
        self.models.append(self.data_model_type(name, fields=d_list))

    def parse_array(self,name: str, obj: Dict):
        # continue
        if '$ref' in obj['items']:
            _type: str = f"List[{obj['items']['$ref'].split('/')[-1]}]"
            self.models.append(CustomRootType(name, _type))
        elif 'properties' in obj['items']:
            self.parse_object(name[:-1], obj['items'])
            self.models.append(CustomRootType(name, f'List[{name[:-1]}]'))

    def parse(self):
        for obj_name, obj in base_parser.specification['components']['schemas'].items():
            if 'properties' in obj:
                self.parse_object(obj_name, obj)
            elif 'items' in obj:
                self.parse_array(obj_name, obj)

        for data_model in self.models:
            print(data_model)
            print('')
