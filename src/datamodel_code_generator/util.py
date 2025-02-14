from __future__ import annotations

import copy
from typing import TYPE_CHECKING, Any, Callable, TypeVar

import pydantic
from packaging import version
from pydantic import BaseModel as _BaseModel

PYDANTIC_VERSION = version.parse(pydantic.VERSION if isinstance(pydantic.VERSION, str) else str(pydantic.VERSION))

PYDANTIC_V2: bool = version.parse("2.0b3") <= PYDANTIC_VERSION

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Literal

    from yaml import SafeLoader

    def load_toml(path: Path) -> dict[str, Any]: ...

else:
    try:
        from yaml import CSafeLoader as SafeLoader
    except ImportError:  # pragma: no cover
        from yaml import SafeLoader

    try:
        from tomllib import load as load_tomllib
    except ImportError:
        from tomli import load as load_tomllib

    def load_toml(path: Path) -> dict[str, Any]:
        with path.open("rb") as f:
            return load_tomllib(f)


SafeLoaderTemp = copy.deepcopy(SafeLoader)
SafeLoaderTemp.yaml_constructors = copy.deepcopy(SafeLoader.yaml_constructors)
SafeLoaderTemp.add_constructor(
    "tag:yaml.org,2002:timestamp",
    SafeLoaderTemp.yaml_constructors["tag:yaml.org,2002:str"],
)
SafeLoader = SafeLoaderTemp

Model = TypeVar("Model", bound=_BaseModel)


def model_validator(
    mode: Literal["before", "after"] = "after",
) -> Callable[[Callable[[Model, Any], Any]], Callable[[Model, Any], Any]]:
    def inner(method: Callable[[Model, Any], Any]) -> Callable[[Model, Any], Any]:
        if PYDANTIC_V2:
            from pydantic import model_validator as model_validator_v2  # noqa: PLC0415

            return model_validator_v2(mode=mode)(method)  # pyright: ignore[reportReturnType]
        from pydantic import root_validator  # noqa: PLC0415

        return root_validator(method, pre=mode == "before")  # pyright: ignore[reportCallIssue]

    return inner


def field_validator(
    field_name: str,
    *fields: str,
    mode: Literal["before", "after"] = "after",
) -> Callable[[Any], Callable[[BaseModel, Any], Any]]:
    def inner(method: Callable[[Model, Any], Any]) -> Callable[[Model, Any], Any]:
        if PYDANTIC_V2:
            from pydantic import field_validator as field_validator_v2  # noqa: PLC0415

            return field_validator_v2(field_name, *fields, mode=mode)(method)
        from pydantic import validator  # noqa: PLC0415

        return validator(field_name, *fields, pre=mode == "before")(method)  # pyright: ignore[reportReturnType]

    return inner


if PYDANTIC_V2:
    from pydantic import ConfigDict
else:
    ConfigDict = dict


class BaseModel(_BaseModel):
    if PYDANTIC_V2:
        model_config = ConfigDict(strict=False)  # pyright: ignore[reportAssignmentType]
