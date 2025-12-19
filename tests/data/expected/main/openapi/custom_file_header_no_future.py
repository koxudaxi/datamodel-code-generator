# multiline custom ;
# header ;
# file ;


from pydantic import AnyUrl, BaseModel, Field


class Pet(BaseModel):
    id: int
    name: str
    tag: str | None = None


class Pets(BaseModel):
    __root__: list[Pet]


class User(BaseModel):
    id: int
    name: str
    tag: str | None = None


class Users(BaseModel):
    __root__: list[User]


class Id(BaseModel):
    __root__: str


class Rules(BaseModel):
    __root__: list[str]


class Error(BaseModel):
    code: int
    message: str


class Api(BaseModel):
    apiKey: str | None = Field(
        None, description='To be used as a dataset parameter value'
    )
    apiVersionNumber: str | None = Field(
        None, description='To be used as a version parameter value'
    )
    apiUrl: AnyUrl | None = Field(
        None, description="The URL describing the dataset's fields"
    )
    apiDocumentationUrl: AnyUrl | None = Field(
        None, description='A URL to the API console for each API'
    )


class Apis(BaseModel):
    __root__: list[Api]


class Event(BaseModel):
    name: str | None = None


class Result(BaseModel):
    event: Event | None = None
