"""Import management system for generated code.

Provides Import and Imports classes to track, organize, and render
Python import statements for generated data models.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache
from itertools import starmap
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable


@dataclass(frozen=True)
class Import:
    """Represents a single Python import statement."""

    import_: str
    from_: str | None = None
    alias: str | None = None
    reference_path: str | None = None

    @property
    def is_future(self) -> bool:
        """Check if this is a __future__ import."""
        return self.from_ == "__future__"

    @classmethod
    @lru_cache(maxsize=4096)
    def from_full_path(cls, class_path: str) -> Import:
        """Create an Import from a fully qualified path (e.g., 'typing.Optional')."""
        split_class_path: list[str] = class_path.split(".")
        return cls(import_=split_class_path[-1], from_=".".join(split_class_path[:-1]) or None)


class Imports(defaultdict[str | None, set[str]]):
    """Collection of imports with reference counting and alias support."""

    def __str__(self) -> str:
        """Return formatted import statements."""
        return self.dump()

    def __init__(self, use_exact: bool = False) -> None:  # noqa: FBT001, FBT002
        """Initialize empty import collection."""
        super().__init__(set)
        self.alias: defaultdict[str | None, dict[str, str]] = defaultdict(dict)
        self.counter: dict[tuple[str | None, str], int] = defaultdict(int)
        self.reference_paths: dict[str, Import] = {}
        self.use_exact: bool = use_exact
        self._exports: set[str] | None = None

    def _set_alias(self, from_: str | None, imports: set[str]) -> list[str]:
        """Apply aliases to imports and return sorted list."""
        return [
            f"{i} as {self.alias[from_][i]}" if i in self.alias[from_] and i != self.alias[from_][i] else i
            for i in sorted(imports)
        ]

    def create_line(self, from_: str | None, imports: set[str]) -> str:
        """Create a single import line from module and names."""
        if from_:
            return f"from {from_} import {', '.join(self._set_alias(from_, imports))}"
        return "\n".join(f"import {i}" for i in self._set_alias(from_, imports))

    def dump(self) -> str:
        """Render all imports as a string."""
        return "\n".join(starmap(self.create_line, self.items()))

    @staticmethod
    def _storage_key(import_: Import) -> tuple[str | None, str]:
        if "." in import_.import_:
            return None, import_.import_
        return import_.from_, import_.import_

    def append(self, imports: Import | Iterable[Import] | None) -> None:
        """Add one or more imports to the collection."""
        if imports:
            if isinstance(imports, Import):
                imports = [imports]
            for import_ in imports:
                if import_.reference_path:
                    self.reference_paths[import_.reference_path] = import_
                key = self._storage_key(import_)
                self[key[0]].add(key[1])
                self.counter[key] += 1
                if "." not in import_.import_ and import_.alias:
                    self.alias[key[0]][key[1]] = import_.alias

    def remove(self, imports: Import | Iterable[Import]) -> None:
        """Remove one or more imports from the collection."""
        if isinstance(imports, Import):
            imports = [imports]
        for import_ in imports:
            is_dotted_import = "." in import_.import_
            key = self._storage_key(import_)
            if self.counter.get(key, 0) <= 0:
                continue
            self.counter[key] -= 1
            if self.counter[key] == 0:
                del self.counter[key]
                if not is_dotted_import or (key[0] in self and key[1] in self[key[0]]):
                    self[key[0]].remove(key[1])
                    if not self[key[0]]:
                        del self[key[0]]
                if not is_dotted_import and import_.alias and key[0] in self.alias and key[1] in self.alias[key[0]]:
                    del self.alias[key[0]][key[1]]
                    if not self.alias[key[0]]:
                        del self.alias[key[0]]
            if import_.reference_path and import_.reference_path in self.reference_paths:
                del self.reference_paths[import_.reference_path]

    def remove_referenced_imports(self, reference_path: str) -> None:
        """Remove imports associated with a reference path."""
        if reference_path in self.reference_paths:
            self.remove(self.reference_paths[reference_path])

    def extract_future(self) -> Imports:
        """Extract and remove __future__ imports, returning them as a new Imports."""
        future = Imports(self.use_exact)
        future_key = "__future__"
        if future_key in self:
            self._move_module_state(future, future_key)
        return future

    def _move_module_state(self, target: Imports, module_key: str | None) -> None:
        target[module_key] = self.pop(module_key)
        for key in list(self.counter.keys()):
            if key[0] == module_key:
                target.counter[key] = self.counter.pop(key)
        if module_key in self.alias:
            target.alias[module_key] = self.alias.pop(module_key)
        for ref_path, import_ in list(self.reference_paths.items()):
            if import_.from_ == module_key:
                target.reference_paths[ref_path] = self.reference_paths.pop(ref_path)
        # _exports are local declarations, not import-module state, so they stay on self.

    def add_export(self, name: str) -> None:
        """Add a name to export without importing it (for local definitions)."""
        if self._exports is None:
            self._exports = set()
        self._exports.add(name)

    def dump_all(self, *, multiline: bool = False) -> str:
        """Generate __all__ declaration from imported names and added exports.

        Args:
            multiline: If True, format with one name per line

        Returns:
            Formatted __all__ = [...] string
        """
        name_set: set[str] = (self._exports or set()).copy()
        for from_, imports in self.items():
            name_set.update(self.alias.get(from_, {}).get(import_) or import_ for import_ in imports)
        name_list = sorted(name_set)
        if multiline:
            items = ",\n    ".join(f'"{name}"' for name in name_list)
            return f"__all__ = [\n    {items},\n]"
        items = ", ".join(f'"{name}"' for name in name_list)
        return f"__all__ = [{items}]"

    def get_effective_name(self, from_: str | None, import_: str) -> str:
        """Get the effective name after alias resolution."""
        return self.alias.get(from_, {}).get(import_, import_)

    def remove_unused(self, used_names: set[str]) -> None:
        """Remove imports not referenced in used_names.

        Note: Checks both effective name (after alias) and original name to handle
        cases where code may reference either form (e.g., type annotations may use
        original name while runtime code uses alias).
        """
        unused = [
            (from_, import_)
            for from_, imports_ in self.items()
            for import_ in imports_
            if not {self.get_effective_name(from_, import_), import_}.intersection(used_names)
        ]
        # Build reverse lookup dict for O(1) access instead of O(n) linear scan per import
        reverse_lookup: dict[tuple[str | None, str], str | None] = {
            self._storage_key(imp): path for path, imp in self.reference_paths.items()
        }
        for from_, import_ in unused:
            alias = self.alias.get(from_, {}).get(import_)
            reference_path = reverse_lookup.get((from_, import_))
            import_obj = Import(from_=from_, import_=import_, alias=alias, reference_path=reference_path)
            while self.counter.get((from_, import_), 0) > 0:
                self.remove(import_obj)


IMPORT_ANNOTATED = Import.from_full_path("typing.Annotated")
IMPORT_ANY = Import.from_full_path("typing.Any")
IMPORT_LIST = Import.from_full_path("typing.List")
IMPORT_SET = Import.from_full_path("typing.Set")
IMPORT_UNION = Import.from_full_path("typing.Union")
IMPORT_OPTIONAL = Import.from_full_path("typing.Optional")
IMPORT_LITERAL = Import.from_full_path("typing.Literal")
IMPORT_TUPLE = Import.from_full_path("typing.Tuple")
IMPORT_TYPE_ALIAS = Import.from_full_path("typing.TypeAlias")
IMPORT_TYPE_ALIAS_TYPE = Import.from_full_path("typing_extensions.TypeAliasType")
IMPORT_SEQUENCE = Import.from_full_path("typing.Sequence")
IMPORT_FROZEN_SET = Import.from_full_path("typing.FrozenSet")
IMPORT_MAPPING = Import.from_full_path("typing.Mapping")
IMPORT_ABC_SEQUENCE = Import.from_full_path("collections.abc.Sequence")
IMPORT_ABC_SET = Import.from_full_path("collections.abc.Set")
IMPORT_ABC_MAPPING = Import.from_full_path("collections.abc.Mapping")
IMPORT_ENUM = Import.from_full_path("enum.Enum")
IMPORT_STR_ENUM = Import.from_full_path("enum.StrEnum")
IMPORT_INT_ENUM = Import.from_full_path("enum.IntEnum")
IMPORT_ANNOTATIONS = Import.from_full_path("__future__.annotations")
IMPORT_DICT = Import.from_full_path("typing.Dict")
IMPORT_DECIMAL = Import.from_full_path("decimal.Decimal")
IMPORT_DATE = Import.from_full_path("datetime.date")
IMPORT_DATETIME = Import.from_full_path("datetime.datetime")
IMPORT_TIMEDELTA = Import.from_full_path("datetime.timedelta")
IMPORT_PATH = Import.from_full_path("pathlib.Path")
IMPORT_TIME = Import.from_full_path("datetime.time")
IMPORT_UUID = Import.from_full_path("uuid.UUID")
IMPORT_ULID = Import.from_full_path("ulid.ULID")
IMPORT_IPV4ADDRESS = Import.from_full_path("ipaddress.IPv4Address")
IMPORT_IPV6ADDRESS = Import.from_full_path("ipaddress.IPv6Address")
IMPORT_IPV4NETWORK = Import.from_full_path("ipaddress.IPv4Network")
IMPORT_IPV6NETWORK = Import.from_full_path("ipaddress.IPv6Network")
IMPORT_PENDULUM_DATE = Import.from_full_path("pendulum.Date")
IMPORT_PENDULUM_DATETIME = Import.from_full_path("pendulum.DateTime")
IMPORT_PENDULUM_DURATION = Import.from_full_path("pendulum.Duration")
IMPORT_PENDULUM_TIME = Import.from_full_path("pendulum.Time")
