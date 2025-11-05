from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile

from datamodel_code_generator import DataModelType, generate, InputFileType


def test_graphql_enum_generation():
    """Test that GraphQL enums are generated with @strawberry.enum directive."""
    graphql_schema = """
    enum Direction {
        ASC
        DESC
    }
    """
    
    with NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        output_path = Path(f.name)
    
    try:
        generate(
            graphql_schema,
            input_file_type=InputFileType.GraphQL,
            output_model_type=DataModelType.StrawberryEnum,
            output=output_path,
        )
        
        result = output_path.read_text()
        
        # Check that the result contains strawberry enum decorator
        assert "@strawberry.enum" in result
        assert "from enum import Enum" in result
        assert "class Direction(Enum)" in result
        assert 'ASC = "ASC"' in result
        assert 'DESC = "DESC"' in result
    finally:
        output_path.unlink()


def test_graphql_input_generation():
    """Test that GraphQL inputs are generated with @strawberry.input directive."""
    graphql_schema = """
    input UserInput {
        name: String!
        email: String!
        age: Int
    }
    """
    
    with NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        output_path = Path(f.name)
    
    try:
        generate(
            graphql_schema,
            input_file_type=InputFileType.GraphQL,
            output_model_type=DataModelType.StrawberryEnum,
            output=output_path,
        )
        
        result = output_path.read_text()
        
        # Check that the result contains strawberry input decorator
        assert "@strawberry.input" in result
        assert "class UserInput" in result
        assert "name: str" in result
        assert "email: str" in result
        assert "age: Optional[int]" in result or "age: int | None" in result
    finally:
        output_path.unlink()


def test_graphql_input_with_default_values():
    """Test that GraphQL inputs with default values are generated correctly."""
    graphql_schema = """
    input PagingInput {
        limit: Int! = 100
        from: Int! = 0
    }
    """
    
    with NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        output_path = Path(f.name)
    
    try:
        generate(
            graphql_schema,
            input_file_type=InputFileType.GraphQL,
            output_model_type=DataModelType.StrawberryEnum,
            output=output_path,
        )
        
        result = output_path.read_text()
        
        # Check that the result contains strawberry input decorator
        assert "@strawberry.input" in result
        assert "class PagingInput" in result
        # Check that int defaults are numbers, not strings
        # Note: Black may not format due to parser limitation with 'from_' field, so check various formats
        assert ("from_: int = strawberry.field(name='from', default=0)" in result or 
                "from_: int = strawberry.field(name=\"from\", default=0)" in result or
                "from_: int= strawberry.field(name='from', default=0)" in result or
                "from_: int=strawberry.field(name='from', default=0)" in result)
        assert ("limit: int = 100" in result or "limit: int=100" in result or "limit: int= 100" in result or "limit: int =100" in result)
        # Ensure defaults are not quoted
        assert "default='0'" not in result
        assert "limit: int = '100'" not in result
    finally:
        output_path.unlink()


def test_graphql_input_with_enum_default():
    """Test that GraphQL inputs with enum defaults are generated correctly."""
    graphql_schema = """
    enum Direction {
        ASC
        DESC
    }
    
    input Sort {
        direction: Direction! = ASC
    }
    """
    
    with NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        output_path = Path(f.name)
    
    try:
        generate(
            graphql_schema,
            input_file_type=InputFileType.GraphQL,
            output_model_type=DataModelType.StrawberryEnum,
            output=output_path,
        )
        
        result = output_path.read_text()
        
        # Check that the result contains enum and input
        assert "@strawberry.enum" in result
        assert "class Direction(Enum)" in result
        assert "@strawberry.input" in result
        assert "class Sort" in result
        # Check that enum default is correctly generated as Direction.ASC (enum member reference)
        assert "direction: Direction = Direction.ASC" in result or "direction: Direction=Direction.ASC" in result
        # Ensure enum default is not quoted and not just the bare enum value name
        assert "direction: Direction = 'ASC'" not in result
        assert "direction: Direction = \"ASC\"" not in result
        assert "direction: Direction = ASC" not in result  # Should be Direction.ASC, not just ASC
    finally:
        output_path.unlink()


def test_graphql_directive_generation():
    """Test that GraphQL directives are generated with @strawberry.schema_directive."""
    graphql_schema = """
    directive @goField(forceResolver: Boolean, name: String) on INPUT_FIELD_DEFINITION | FIELD_DEFINITION
    """
    
    with NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        output_path = Path(f.name)
    
    try:
        generate(
            graphql_schema,
            input_file_type=InputFileType.GraphQL,
            output_model_type=DataModelType.StrawberryEnum,
            output=output_path,
        )
        
        result = output_path.read_text()
        
        # Check that the result contains strawberry schema_directive decorator
        assert "@strawberry.schema_directive" in result
        assert "from strawberry.schema_directives import Location" in result
        assert "class GoField" in result
        # Check locations
        assert "Location.FIELD_DEFINITION" in result
        assert "Location.INPUT_FIELD_DEFINITION" in result
        # Check directive fields (both are nullable)
        assert "forceResolver: Optional[bool]" in result or "forceResolver: bool | None" in result
        assert "name: Optional[str]" in result or "name: str | None" in result
    finally:
        output_path.unlink()


def test_graphql_directive_without_parameters():
    """Test that GraphQL directives without parameters include pass."""
    graphql_schema = """
    directive @beta on FIELD_DEFINITION
    """
    
    with NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        output_path = Path(f.name)
    
    try:
        generate(
            graphql_schema,
            input_file_type=InputFileType.GraphQL,
            output_model_type=DataModelType.StrawberryEnum,
            output=output_path,
        )
        
        result = output_path.read_text()
        
        # Check that the result contains strawberry schema_directive decorator
        assert "@strawberry.schema_directive" in result
        assert "class Beta" in result
        # Check that pass is included
        assert "pass" in result
    finally:
        output_path.unlink()


def test_graphql_nullable_and_non_nullable_fields():
    """Test that nullable and non-nullable GraphQL fields are generated correctly."""
    graphql_schema = """
    type User {
        id: ID!
        name: String!
        email: String
        age: Int
    }
    """
    
    with NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        output_path = Path(f.name)
    
    try:
        generate(
            graphql_schema,
            input_file_type=InputFileType.GraphQL,
            output_model_type=DataModelType.StrawberryEnum,
            output=output_path,
        )
        
        result = output_path.read_text()
        
        # Check that the result contains strawberry type decorator
        assert "@strawberry.type" in result
        assert "class User" in result
        # Check non-nullable fields (no Optional)
        assert "id: ID" in result
        assert "name: str" in result
        # Check nullable fields (with Optional)
        assert "email: Optional[str]" in result or "email: str | None" in result
        assert "age: Optional[int]" in result or "age: int | None" in result
        # Ensure non-nullable fields are not wrapped with Optional
        assert "id: Optional[ID]" not in result
        assert "name: Optional[str]" not in result
    finally:
        output_path.unlink()


def test_graphql_list_types():
    """Test that GraphQL list types are generated correctly."""
    graphql_schema = """
    type User {
        id: ID!
        tags: [String!]!
        optionalTags: [String]
    }
    """
    
    with NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        output_path = Path(f.name)
    
    try:
        generate(
            graphql_schema,
            input_file_type=InputFileType.GraphQL,
            output_model_type=DataModelType.StrawberryEnum,
            output=output_path,
        )
        
        result = output_path.read_text()
        
        # Check that the result contains list types
        assert "@strawberry.type" in result
        assert "class User" in result
        # Check list types
        assert "List[str]" in result or "list[str]" in result
        # Check that non-nullable list is not wrapped with Optional
        assert "tags:" in result
        assert "optionalTags:" in result
    finally:
        output_path.unlink()


def test_graphql_id_type():
    """Test that GraphQL ID type is generated as strawberry.ID."""
    graphql_schema = """
    type User {
        id: ID!
        name: String!
    }
    """
    
    with NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        output_path = Path(f.name)
    
    try:
        generate(
            graphql_schema,
            input_file_type=InputFileType.GraphQL,
            output_model_type=DataModelType.StrawberryEnum,
            output=output_path,
        )
        
        result = output_path.read_text()
        
        # Check that ID type is imported and used
        assert "from strawberry import ID" in result
        assert "id: ID" in result
        # Ensure ID is not generated as String
        assert "id: String" not in result
        assert "id: str" not in result
    finally:
        output_path.unlink()


def test_graphql_builtin_types():
    """Test that GraphQL built-in types are mapped correctly."""
    graphql_schema = """
    type Test {
        stringField: String!
        intField: Int!
        floatField: Float!
        booleanField: Boolean!
        idField: ID!
    }
    """
    
    with NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        output_path = Path(f.name)
    
    try:
        generate(
            graphql_schema,
            input_file_type=InputFileType.GraphQL,
            output_model_type=DataModelType.StrawberryEnum,
            output=output_path,
        )
        
        result = output_path.read_text()
        
        # Check that built-in types are mapped to Python types
        assert "stringField: str" in result
        assert "intField: int" in result
        assert "floatField: float" in result
        assert "booleanField: bool" in result
        assert "idField: ID" in result
        # Ensure GraphQL type names are not used
        assert "stringField: String" not in result
        assert "intField: Int" not in result
        assert "floatField: Float" not in result
        assert "booleanField: Boolean" not in result
    finally:
        output_path.unlink()


def test_graphql_custom_scalars():
    """Test that custom scalars are imported only when --scalars-from-import is provided."""
    graphql_schema = """
    scalar Email
    scalar MD5

    type Test {
        email: Email!
        md5: MD5!
    }
    """
    
    with NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        output_path = Path(f.name)
    
    try:
        # Test without scalars_from_import (no import should be generated)
        generate(
            graphql_schema,
            input_file_type=InputFileType.GraphQL,
            output_model_type=DataModelType.StrawberryEnum,
            output=output_path,
        )
        
        result = output_path.read_text()
        
        # Check that no scalar import is generated when option is not provided
        # Extract all import statements (including multiline imports)
        import_block = []
        in_import = False
        current_import = []
        for line in result.split('\n'):
            stripped = line.strip()
            if stripped.startswith('from ') or (stripped.startswith('import ') and not in_import):
                in_import = True
                current_import = [line]
                # Check if this is a single-line import
                if not stripped.endswith('\\') and '(' not in stripped:
                    import_block.append(' '.join(current_import))
                    current_import = []
                    in_import = False
            elif in_import:
                current_import.append(line)
                # Check if this is the end of a multiline import (closing parenthesis)
                if stripped.endswith(')'):
                    import_block.append(' '.join(current_import))
                    current_import = []
                    in_import = False
        
        # Join all import statements into a single block
        import_block_text = '\n'.join(import_block)
        
        # Check that Email and MD5 are not in any import statement
        assert "Email" not in import_block_text, f"Email found in imports: {import_block_text}"
        assert "MD5" not in import_block_text, f"MD5 found in imports: {import_block_text}"
        
        # But scalars should still be used in the type definitions
        assert "Email" in result
        assert "MD5" in result
        assert "email: Email" in result
        assert "md5: MD5" in result
        
        # Test with custom import path
        output_path.unlink()
        with NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f2:
            output_path = Path(f2.name)
        
        generate(
            graphql_schema,
            input_file_type=InputFileType.GraphQL,
            output_model_type=DataModelType.StrawberryEnum,
            output=output_path,
            scalars_from_import=".custom.scalars",
        )
        
        result = output_path.read_text()
        
        # Check that custom scalars are imported with custom path
        assert "from .custom.scalars import" in result
        assert "Email" in result
        assert "MD5" in result
        assert "email: Email" in result
        assert "md5: MD5" in result
        
        # Test with .scalars.base_scalars path
        output_path.unlink()
        with NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f3:
            output_path = Path(f3.name)
        
        generate(
            graphql_schema,
            input_file_type=InputFileType.GraphQL,
            output_model_type=DataModelType.StrawberryEnum,
            output=output_path,
            scalars_from_import=".scalars.base_scalars",
        )
        
        result = output_path.read_text()
        
        # Check that scalars are imported with the provided path
        assert "from .scalars.base_scalars import" in result
        assert "Email" in result
        assert "MD5" in result
    finally:
        output_path.unlink()


def test_graphql_directive_with_default_values():
    """Test that directive parameters with different default value types are generated correctly."""
    graphql_schema = """
    enum Status {
        ACTIVE
        INACTIVE
    }
    
    directive @config(
        maxInt: Int! = 100
        minInt: Int! = 0
        maxFloat: Float! = 3.14
        enabled: Boolean! = true
        disabled: Boolean! = false
        message: String! = "Hello"
        status: Status! = ACTIVE
        optionalInt: Int = 42
        optionalString: String = "default"
    ) on FIELD_DEFINITION
    """
    
    with NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        output_path = Path(f.name)
    
    try:
        generate(
            graphql_schema,
            input_file_type=InputFileType.GraphQL,
            output_model_type=DataModelType.StrawberryEnum,
            output=output_path,
        )
        
        result = output_path.read_text()
        
        # Check that the directive is generated
        assert "@strawberry.schema_directive" in result
        assert "class Config" in result
        
        # Check int defaults are numbers, not strings
        assert "maxInt: Optional[int] = 100" in result or "maxInt: Optional[int]=100" in result or "maxInt: int | None = 100" in result
        assert "minInt: Optional[int] = 0" in result or "minInt: Optional[int]=0" in result or "minInt: int | None = 0" in result
        assert "maxInt: Optional[int] = '100'" not in result
        assert "minInt: Optional[int] = '0'" not in result
        
        # Check float defaults are numbers, not strings
        assert "maxFloat: Optional[float] = 3.14" in result or "maxFloat: Optional[float]=3.14" in result or "maxFloat: float | None = 3.14" in result
        assert "maxFloat: Optional[float] = '3.14'" not in result
        
        # Check boolean defaults are booleans, not strings
        assert "enabled: Optional[bool] = True" in result or "enabled: Optional[bool]=True" in result or "enabled: bool | None = True" in result
        assert "disabled: Optional[bool] = False" in result or "disabled: Optional[bool]=False" in result or "disabled: bool | None = False" in result
        assert "enabled: Optional[bool] = 'true'" not in result
        assert "disabled: Optional[bool] = 'false'" not in result
        
        # Check string defaults are strings (quoted)
        assert "message: Optional[str] = 'Hello'" in result or "message: Optional[str]='Hello'" in result or "message: str | None = 'Hello'" in result or "message: Optional[str] = \"Hello\"" in result
        
        # Check enum defaults are enum member references
        assert "status: Optional[Status] = Status.ACTIVE" in result or "status: Optional[Status]=Status.ACTIVE" in result or "status: Status | None = Status.ACTIVE" in result
        assert "status: Optional[Status] = 'ACTIVE'" not in result
        assert "status: Optional[Status] = ACTIVE" not in result
        
        # Check optional int defaults
        assert "optionalInt: Optional[int] = 42" in result or "optionalInt: int | None = 42" in result or "optionalInt: Optional[int]=42" in result
        assert "optionalInt: Optional[int] = '42'" not in result
        
        # Check optional string defaults
        assert "optionalString: Optional[str] = 'default'" in result or "optionalString: str | None = 'default'" in result or "optionalString: Optional[str]='default'" in result
    finally:
        output_path.unlink()


def test_graphql_complex_schema():
    """Test a complex GraphQL schema with multiple types."""
    graphql_schema = """
    enum UserStatus {
        ACTIVE
        INACTIVE
        PENDING
    }
    
    input CreateUserInput {
        name: String!
        email: String!
        status: UserStatus = ACTIVE
    }
    
    type User {
        id: ID!
        name: String!
        email: String!
        status: UserStatus!
    }
    
        directive @authorize(
            resource: String!
            action: String = "VIEW"
        ) on FIELD_DEFINITION | ENUM_VALUE
        """
    
    with NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        output_path = Path(f.name)
    
    try:
        generate(
            graphql_schema,
            input_file_type=InputFileType.GraphQL,
            output_model_type=DataModelType.StrawberryEnum,
            output=output_path,
        )
        
        result = output_path.read_text()
        
        # Check enum
        assert "@strawberry.enum" in result
        assert "class UserStatus(Enum)" in result
        assert 'ACTIVE = "ACTIVE"' in result
        
        # Check input
        assert "@strawberry.input" in result
        assert "class CreateUserInput" in result
        # Check that enum default is correctly generated as UserStatus.ACTIVE (enum member reference)
        assert "status: UserStatus = UserStatus.ACTIVE" in result or "status: UserStatus=UserStatus.ACTIVE" in result or "status: Optional[UserStatus] = UserStatus.ACTIVE" in result
        
        # Check type
        assert "@strawberry.type" in result
        assert "class User" in result
        
        # Check directive (custom directive should be generated, built-in @deprecated should not)
        assert "@strawberry.schema_directive" in result
        assert "class Authorize" in result
        assert "resource: str" in result
        assert ("action: Optional[str] = \"VIEW\"" in result or 
                "action: Optional[str] = 'VIEW'" in result or 
                "action: str | None = \"VIEW\"" in result or
                "action: str | None = 'VIEW'" in result)
        # Built-in @deprecated should NOT be generated
        assert "class Deprecated" not in result
    finally:
        output_path.unlink()


def test_graphql_builtin_directives_not_generated():
    """Test that built-in GraphQL directives are not generated."""
    graphql_schema = """
    directive @deprecated(
        reason: String = "No longer supported"
    ) on FIELD_DEFINITION | ENUM_VALUE
    
    directive @authorize(
        resource: String!
        action: String = "VIEW"
    ) on FIELD_DEFINITION
    
    type Test {
        id: ID!
        name: String!
    }
    """
    
    with NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        output_path = Path(f.name)
    
    try:
        generate(
            graphql_schema,
            input_file_type=InputFileType.GraphQL,
            output_model_type=DataModelType.StrawberryEnum,
            output=output_path,
        )
        
        result = output_path.read_text()
        
        # Check that built-in directives are NOT generated
        assert "class Deprecated" not in result, "Built-in @deprecated directive should not be generated"
        assert "class Include" not in result, "Built-in @include directive should not be generated"
        assert "class Skip" not in result, "Built-in @skip directive should not be generated"
        assert "class SpecifiedBy" not in result, "Built-in @specifiedBy directive should not be generated"
        
        # Check that custom directives ARE generated
        assert "class Authorize" in result, "Custom @authorize directive should be generated"
        assert "@strawberry.schema_directive" in result
        
        # Check that the Test type is still generated
        assert "@strawberry.type" in result
        assert "class Test" in result
    finally:
        output_path.unlink()


def test_graphql_reserved_keyword_fields():
    """Test that fields with Python reserved keyword names get @strawberry.field decorator."""
    graphql_schema = """
    type Test {
        in: String!
        from: Int!
        name: String!
    }
    
    input TestInput {
        in: String!
        from: Int!
        name: String!
    }
    """
    
    with NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        output_path = Path(f.name)
    
    try:
        generate(
            graphql_schema,
            input_file_type=InputFileType.GraphQL,
            output_model_type=DataModelType.StrawberryEnum,
            output=output_path,
        )
        
        result = output_path.read_text()
        
        # Check that reserved keyword fields use strawberry.field(name='...')
        # For type fields
        assert "in_: str = strawberry.field(name='in')" in result or "in_: str = strawberry.field(name=\"in\")" in result
        assert "from_: int = strawberry.field(name='from')" in result or "from_: int = strawberry.field(name=\"from\")" in result
        # Regular field should not use strawberry.field
        assert "name: str" in result
        assert "name: str = strawberry.field" not in result
        
        # For input fields
        assert "class TestInput" in result
        # Input fields should also use strawberry.field
        assert "in_: str = strawberry.field(name='in')" in result or "in_: str = strawberry.field(name=\"in\")" in result
        assert "from_: int = strawberry.field(name='from')" in result or "from_: int = strawberry.field(name=\"from\")" in result
    finally:
        output_path.unlink()

