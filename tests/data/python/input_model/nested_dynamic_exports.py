"""Dynamic short exports remain valid when their descriptive owners change."""

from __future__ import annotations

from typing import Any, NoReturn

from pydantic import BaseModel

calls = []
exports = {}


class DeletedOwner:
    """Exercise a real nested export binding."""

    class Deleted(BaseModel):
        """Exercise a real nested export binding."""

        value: int


exports["Deleted"] = DeletedOwner.Deleted


class DeletedRoot(BaseModel):
    """Exercise a real nested export binding."""

    child: DeletedOwner.Deleted
    model_config = {"json_schema_extra": {"x-caller-root": "kept"}}


globals().pop("DeletedOwner")


class ScalarOwner:
    """Exercise a real nested export binding."""

    class Scalar(BaseModel):
        """Exercise a real nested export binding."""

        value: int


exports["Scalar"] = ScalarOwner.Scalar


class ScalarRoot(BaseModel):
    """Exercise a real nested export binding."""

    child: ScalarOwner.Scalar


class Replacement:
    """Exercise a real nested export binding."""

    @property
    def __class__(self) -> type:
        """Record unexpected instance type inspection."""
        calls.append("replacement.__class__")
        return type(self)

    def __getattr__(self, name: str) -> NoReturn:
        """Record unexpected owner attribute resolution."""
        calls.append(f"replacement.{name}")
        raise AttributeError(name)


ScalarOwner = Replacement()


class ChangedOwner:
    """Exercise a real nested export binding."""

    class Changed(BaseModel):
        """Exercise a real nested export binding."""

        value: int


exports["Changed"] = ChangedOwner.Changed


class ChangedRoot(BaseModel):
    """Exercise a real nested export binding."""

    child: ChangedOwner.Changed


class Other(BaseModel):
    """Exercise a real nested export binding."""

    other: str


ChangedOwner.Changed = Other


class DescriptorOwner:
    """Exercise a real nested export binding."""

    class Descriptor(BaseModel):
        """Exercise a real nested export binding."""

        value: int


exports["Descriptor"] = DescriptorOwner.Descriptor


class DescriptorRoot(BaseModel):
    """Exercise a real nested export binding."""

    child: DescriptorOwner.Descriptor


class OwnerDescriptor:
    """Exercise a real nested export binding."""

    def __get__(self, instance: object, owner: type | None) -> type[Other]:
        """Record unexpected descriptor evaluation."""
        calls.append("descriptor.__get__")
        return Other


DescriptorOwner.Descriptor = OwnerDescriptor()


class ObservedMeta(type):
    """Exercise a real nested export binding."""

    def __getattribute__(cls, name: str) -> Any:
        """Observe namespace access through the metaclass hook."""
        if name == "__dict__":
            calls.append("owner.__dict__")
        return super().__getattribute__(name)


class LiveOwner(metaclass=ObservedMeta):
    """Exercise a real nested export binding."""

    class Live(BaseModel):
        """Exercise a real nested export binding."""

        value: int


exports["Live"] = LiveOwner.Live


class LiveRoot(BaseModel):
    """Exercise a real nested export binding."""

    child: LiveOwner.Live


class LazyOwner:
    """Exercise a real nested export binding."""

    class Lazy(BaseModel):
        """Exercise a real nested export binding."""

        value: int


LazyOwner.Lazy.__module__ = "tests.data.python.input_model.nested_lazy_exports"
exports["Lazy"] = LazyOwner.Lazy


class LazyRoot(BaseModel):
    """Exercise a real nested export binding."""

    child: LazyOwner.Lazy


def __getattr__(name: str) -> type[BaseModel]:
    """Expose stale owner types through their supported short names."""
    calls.append(name)
    if name in exports and name != "Live":
        return exports[name]
    raise AttributeError(name)
