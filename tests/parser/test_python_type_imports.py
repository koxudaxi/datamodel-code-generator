"""Tests for parser-level structured Python type import collisions."""

from __future__ import annotations

import pytest

from datamodel_code_generator._python_type_annotation import PythonTypeBoundName, PythonTypeName
from datamodel_code_generator._python_type_binding import BoundPythonType, alias_bound_python_type
from datamodel_code_generator.imports import Import, Imports
from datamodel_code_generator.model.pydantic_v2.base_model import BaseModel, DataModelField
from datamodel_code_generator.parser._python_type_imports import resolve_python_type_import_aliases
from datamodel_code_generator.reference import Reference
from datamodel_code_generator.types import DataType


def _bound_data_type(from_: str, name: str) -> DataType:
    import_ = Import(from_=from_, import_=name)
    return DataType(
        type=name,
        python_type=BoundPythonType(PythonTypeBoundName(name, from_, name), (import_,)),
    )


@pytest.mark.allow_direct_assert
def test_resolver_avoids_reserved_alias_suffixes() -> None:
    """Field reservations advance both field-style and numbered aliases."""
    aliases = resolve_python_type_import_aliases(
        [_bound_data_type("first", "Thing"), _bound_data_type("second", "Thing")],
        [],
        {"Thing_1"},
    )

    assert aliases["second", "Thing"].alias == "Thing_2"

    field_aliases = resolve_python_type_import_aliases(
        [_bound_data_type("first", "Thing"), _bound_data_type("second", "Thing")],
        [],
        {"Thing", "Thing_aliased"},
    )

    assert field_aliases["first", "Thing"].alias == "Thing_aliased_"
    assert field_aliases["second", "Thing"].alias == "Thing_aliased__"


@pytest.mark.allow_direct_assert
def test_resolver_shares_ordinary_field_alias_with_same_bound_identity() -> None:
    """One exact import identity receives one alias across ordinary and bound types."""
    import_ = Import(from_="datetime", import_="date")
    ordinary = DataType(type="date", import_=import_)
    bound = DataType(
        type="date",
        python_type=BoundPythonType(PythonTypeBoundName("date", "datetime", "date"), (import_,)),
    )

    aliases = resolve_python_type_import_aliases([ordinary, bound], [], {"date"})

    assert aliases == {("datetime", "date"): Import(from_="datetime", import_="date", alias="date_aliased")}

    assert resolve_python_type_import_aliases([ordinary, bound], [], set()) == {}


@pytest.mark.allow_direct_assert
def test_resolver_propagates_existing_alias_to_same_bound_identity() -> None:
    """An established alias remains canonical for every structured consumer."""
    ordinary_import = Import(from_="foo", import_="Bar", alias="ExistingAlias")
    bound = _bound_data_type("foo", "Bar")

    aliases = resolve_python_type_import_aliases(
        [DataType(type="ExistingAlias", import_=ordinary_import), bound],
        [],
        set(),
    )

    assert aliases == {("foo", "Bar"): ordinary_import}
    aliased_bound = alias_bound_python_type(bound.python_type, aliases)
    assert aliased_bound.expression == PythonTypeBoundName("ExistingAlias", "foo", "Bar")
    assert aliased_bound.imports == (ordinary_import,)


@pytest.mark.allow_direct_assert
def test_resolver_realiases_aggregate_binding_shadowed_by_field() -> None:
    """A canonical aggregate alias still yields to names reserved in this module."""
    module_imports = Imports()
    module_imports.append(Import(from_="foo", import_="Bar", alias="Taken"))

    aliases = resolve_python_type_import_aliases(
        [
            DataType(type="Taken", import_=Import(from_="foo", import_="Bar", alias="Taken")),
            _bound_data_type("foo", "Bar"),
        ],
        [],
        {"Taken"},
        (module_imports,),
    )

    assert aliases == {("foo", "Bar"): Import(from_="foo", import_="Bar", alias="Taken_aliased")}


@pytest.mark.allow_direct_assert
def test_resolver_collects_plain_names_model_imports_and_late_module_imports() -> None:
    """All public parser/model contexts protect their effective names."""
    plain = DataType(type="Plain")
    unbound = DataType(
        type="Local",
        python_type=BoundPythonType(PythonTypeName("Local"), ()),
    )
    model_import = Import(from_="datetime", import_="timedelta")
    target = _bound_data_type("external", "Thing")
    model = BaseModel(
        reference=Reference(path="model", name="Model"),
        fields=[
            DataModelField(name="duration", data_type=DataType(type="timedelta", import_=model_import)),
            DataModelField(name="target", data_type=target),
        ],
    )
    module_imports = Imports()
    module_imports.append([
        Import(from_="external", import_="Thing"),
        Import(from_="ordinary", import_="Thing"),
    ])

    aliases = resolve_python_type_import_aliases(
        [plain, unbound, target],
        [model],
        set(),
        (module_imports,),
    )

    assert aliases["external", "Thing"].alias == "Thing_1"


@pytest.mark.allow_direct_assert
def test_resolver_reserves_unimported_base_class_names() -> None:
    """A local base name remains protected from a structured import leaf."""
    model = BaseModel(
        reference=Reference(path="model", name="Model"),
        fields=[],
        base_classes=[Reference(path="LocalBase", name="LocalBase")],
    )

    aliases = resolve_python_type_import_aliases([_bound_data_type("external", "LocalBase")], [model], set())

    assert aliases["external", "LocalBase"].alias == "LocalBase_aliased"
