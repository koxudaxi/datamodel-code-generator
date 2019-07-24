from datamodel_code_generator.model import BaseModel, DataModelField
from datamodel_code_generator.parser.openapi import Parser

if __name__ == '__main__':
    print(Parser(BaseModel, DataModelField).parse())
