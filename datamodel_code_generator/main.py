from datamodel_code_generator.model.pydantic import BaseModel, CustomRootType
from datamodel_code_generator.parser.openapi import Parser

if __name__ == '__main__':
    print(Parser(BaseModel, CustomRootType).parse())
