from datamodel_code_generator.model import BaseModel, DataModelField, DataClass
from datamodel_code_generator.parser.openapi import Parser

if __name__ == '__main__':
    Parser(BaseModel, DataModelField).parse()
