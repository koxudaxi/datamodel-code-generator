"""Tests for non-finite float math import helpers."""

from __future__ import annotations

import ast
from unittest.mock import MagicMock

from datamodel_code_generator.parser._math_imports import (
    add_math_imports_for_non_finite_literals,
    apply_math_imports_to_parse_result,
)


def test_add_math_imports_for_non_finite_literals_basic() -> None:
    """Test injecting math imports for both inf and nan literals."""
    code = """from pydantic import BaseModel

class Item(BaseModel):
    max_val: float = inf
    min_val: float = -inf
    missing: float = nan
"""
    result = add_math_imports_for_non_finite_literals(code)
    assert result.startswith("from math import inf, nan\n")
    assert "max_val: float = inf" in result


def test_add_math_imports_single_inf() -> None:
    """Test injecting math import for only inf."""
    code = """from pydantic import BaseModel

class Item(BaseModel):
    max_val: float = inf
"""
    result = add_math_imports_for_non_finite_literals(code)
    assert result.startswith("from math import inf\n")


def test_add_math_imports_single_nan() -> None:
    """Test injecting math import for only nan."""
    code = """from pydantic import BaseModel

class Item(BaseModel):
    missing: float = nan
"""
    result = add_math_imports_for_non_finite_literals(code)
    assert result.startswith("from math import nan\n")


def test_add_math_imports_no_non_finite() -> None:
    """Test that code without non-finite literals is unchanged."""
    code = """from pydantic import BaseModel

class Item(BaseModel):
    val: float = 1.0
"""
    result = add_math_imports_for_non_finite_literals(code)
    assert result == code


def test_add_math_imports_ignores_comments_and_docstrings() -> None:
    """Test that inf/nan inside comments, docstrings, and strings do not trigger imports."""
    code = """# Model handling inf and nan cases
\"\"\"Docstring discussing nan and inf limits.\"\"\"
from pydantic import BaseModel, Field

class Item(BaseModel):
    name: str = Field(description="Handles nan gracefully without inf")
"""
    result = add_math_imports_for_non_finite_literals(code)
    assert "from math import" not in result
    assert result == code


def test_add_math_imports_ignores_field_name_store_context() -> None:
    """Test that fields named inf or nan do not trigger math imports."""
    code = """from pydantic import BaseModel

class Item(BaseModel):
    inf: float = 1.0
    nan: int = 0
"""
    result = add_math_imports_for_non_finite_literals(code)
    assert "from math import" not in result
    assert result == code


def test_add_math_imports_with_module_docstring_and_future_import() -> None:
    """Test that math imports are placed after __future__ imports when docstrings are present."""
    code = """\"\"\"Module documentation.\"\"\"

from __future__ import annotations

from pydantic import BaseModel

class Item(BaseModel):
    max_val: float = inf
"""
    result = add_math_imports_for_non_finite_literals(code)
    assert "from __future__ import annotations\n\nfrom math import inf" in result
    ast.parse(result)


def test_add_math_imports_existing_imports() -> None:
    """Test that fully imported math names are not duplicated."""
    code = """from math import inf, nan
from pydantic import BaseModel

class Item(BaseModel):
    max_val: float = inf
    missing: float = nan
"""
    result = add_math_imports_for_non_finite_literals(code)
    assert result.count("from math import") == 1
    assert result == code


def test_add_math_imports_existing_partial_import() -> None:
    """Test that missing non-finite names are imported alongside existing imports."""
    code = """from math import inf
from pydantic import BaseModel

class Item(BaseModel):
    max_val: float = inf
    missing: float = nan
"""
    result = add_math_imports_for_non_finite_literals(code)
    assert "from math import nan" in result
    assert "from math import inf" in result
    assert "from math import inf, nan" not in result


def test_apply_math_imports_to_parse_result_str() -> None:
    """Test applying math imports to a single string parse result."""
    code = "val: float = inf\n"
    result = apply_math_imports_to_parse_result(code)
    assert isinstance(result, str)
    assert result.startswith("from math import inf\n")


def test_apply_math_imports_to_parse_result_dict() -> None:
    """Test applying math imports across module dictionary results."""
    item1 = MagicMock()
    item1.body = "val: float = nan\n"
    item2 = MagicMock()
    item2.body = "name: str = 'clean'\n"

    result_dict = {("mod1",): item1, ("mod2",): item2}
    result = apply_math_imports_to_parse_result(result_dict)

    assert isinstance(result, dict)
    assert result["mod1",].body.startswith("from math import nan\n")
    assert result["mod2",].body == "name: str = 'clean'\n"
