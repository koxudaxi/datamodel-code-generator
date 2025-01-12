from datamodel_code_generator.format import PythonVersion
from datamodel_code_generator.imports import (
    IMPORT_LITERAL,
    IMPORT_LITERAL_BACKPORT,
    IMPORT_OPTIONAL,
)
from datamodel_code_generator.types import DataType


class TestDataType:
    def test_imports_with_literal_one(self):
        """Test imports for a DataType with single literal value"""
        data_type = DataType(literals=[''], python_version=PythonVersion.PY_38)

        # Convert iterator to list for assertion
        imports = list(data_type.imports)
        assert IMPORT_LITERAL in imports
        assert len(imports) == 1

    def test_imports_with_literal_one_and_optional(self):
        """Test imports for an optional DataType with single literal value"""
        data_type = DataType(
            literals=[''], is_optional=True, python_version=PythonVersion.PY_38
        )

        imports = list(data_type.imports)
        assert IMPORT_LITERAL in imports
        assert IMPORT_OPTIONAL in imports
        assert len(imports) == 2

    def test_imports_with_literal_empty(self):
        """Test imports for a DataType with no literal values"""
        data_type = DataType(literals=[], python_version=PythonVersion.PY_38)

        imports = list(data_type.imports)
        assert len(imports) == 0

    def test_imports_with_literal_python37(self):
        """Test imports for a DataType with literal in Python 3.7"""
        data_type = DataType(literals=[''], python_version=PythonVersion.PY_37)

        imports = list(data_type.imports)
        assert IMPORT_LITERAL_BACKPORT in imports
        assert len(imports) == 1

    def test_imports_with_nested_dict_key(self):
        """Test imports for a DataType with dict_key containing literals"""
        dict_key_type = DataType(literals=['key'], python_version=PythonVersion.PY_38)

        data_type = DataType(python_version=PythonVersion.PY_38, dict_key=dict_key_type)

        imports = list(data_type.imports)
        assert IMPORT_LITERAL in imports
        assert len(imports) == 1

    def test_imports_without_duplicate_literals(self):
        """Test that literal import is not duplicated"""
        dict_key_type = DataType(literals=['key1'], python_version=PythonVersion.PY_38)

        data_type = DataType(
            literals=['key2'],
            python_version=PythonVersion.PY_38,
            dict_key=dict_key_type,
        )

        imports = list(data_type.imports)
        assert IMPORT_LITERAL in imports
