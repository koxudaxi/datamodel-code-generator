import re
from collections import defaultdict
from contextlib import contextmanager
from functools import lru_cache
from keyword import iskeyword
from pathlib import Path
from typing import (
    DefaultDict,
    Dict,
    Generator,
    List,
    Mapping,
    Optional,
    Pattern,
    Set,
    Tuple,
    Union,
)

import inflect
from pydantic import BaseModel

from datamodel_code_generator import cached_property


class Reference(BaseModel):
    path: str
    original_name: str
    name: str
    loaded: bool = True
    actual_module_name: Optional[str]

    class Config:
        arbitrary_types_allowed = True
        keep_untouched = (cached_property,)

    @cached_property
    def module_name(self) -> Optional[str]:
        if is_url(self.path):  # pragma: no cover
            return None
        # TODO: Support file:///
        path = Path(self.path.split('#')[0])

        # workaround: If a file name has dot then, this method uses first part.
        module_name = f'{".".join(path.parts[:-1])}.{path.stem.split(".")[0]}'
        if module_name.startswith(f'.{self.name.split(".", 1)[0]}'):
            return None
        elif module_name == '.':
            return None
        return module_name


ID_PATTERN: Pattern[str] = re.compile(r'^#[^/].*')


class ModelResolver:
    def __init__(self, aliases: Optional[Mapping[str, str]] = None) -> None:
        self.references: Dict[str, Reference] = {}
        self.aliases: Mapping[str, str] = {} if aliases is None else {**aliases}
        self._current_root: List[str] = []
        self._root_id_base_path: Optional[str] = None
        self.ids: DefaultDict[str, Dict[str, str]] = defaultdict(dict)
        self.after_load_files: Set[str] = set()

    @property
    def current_root(self) -> List[str]:
        return self._current_root

    def set_current_root(self, current_root: List[str]) -> None:
        self._current_root = current_root

    @contextmanager
    def current_root_context(
        self, current_root: List[str]
    ) -> Generator[None, None, None]:
        previous_root_path: List[str] = self.current_root
        self.set_current_root(current_root)
        yield
        self.set_current_root(previous_root_path)

    @property
    def root_id_base_path(self) -> Optional[str]:
        return self._root_id_base_path

    def set_root_id_base_path(self, root_id_base_path: Optional[str]) -> None:
        self._root_id_base_path = root_id_base_path

    def add_id(self, id_: str, path: List[str]) -> None:
        self.ids['/'.join(self.current_root)][id_] = self._get_path(path)

    def _get_path(self, path: List[str]) -> str:
        joined_path = '/'.join(p for p in path if p).replace('/#', '#')
        if ID_PATTERN.match(joined_path):
            return self.ids['/'.join(self.current_root)][joined_path]
        elif '#' in joined_path:
            delimiter = joined_path.index('#')
            return f"{''.join(joined_path[:delimiter])}#{''.join(joined_path[delimiter + 1:])}"
        elif self.root_id_base_path and self.current_root != path:
            return f'{self.root_id_base_path}/{joined_path}#'
        return f'{joined_path}#'

    def is_after_load(self, ref: str) -> bool:
        if self.current_root and len(self.current_root) > 1:
            ref = f"{'/'.join(self.current_root[:-1])}/{ref}"
        if self.is_external_ref(ref):
            return ref.split('#/', 1)[0] in self.after_load_files
        elif self.is_external_root_ref(ref):
            return ref[:-1] in self.after_load_files
        return False

    @staticmethod
    def is_external_ref(ref: str) -> bool:
        return '#/' in ref

    @staticmethod
    def is_external_root_ref(ref: str) -> bool:
        return ref[-1] == '#'

    def add_ref(self, ref: str, actual_module_name: Optional[str] = None) -> Reference:
        path = self._get_path(ref.split('/'))
        reference = self.references.get(path)
        if reference:
            reference.actual_module_name = actual_module_name
            return reference
        split_ref = ref.rsplit('/', 1)
        if len(split_ref) == 1:
            parents = self.root_id_base_path
            original_name = Path(
                split_ref[0][:-1] if self.is_external_root_ref(ref) else split_ref[0]
            ).stem
        else:
            parents = split_ref[0]
            original_name = (
                Path(split_ref[1][:-1]).stem
                if self.is_external_root_ref(ref)
                else split_ref[1]
            )
        if self.is_after_load(ref):
            loaded: bool = False
        else:
            loaded = not self.is_external_ref(ref) and not self.is_external_root_ref(
                ref
            )
        if not original_name:
            original_name = Path(parents).stem  # type: ignore
            loaded = False
        name = self.get_class_name(original_name, unique=False)
        reference = Reference(
            path=path,
            original_name=original_name,
            name=name,
            loaded=loaded,
            actual_module_name=actual_module_name,
        )

        self.references[path] = reference
        return reference

    def add(
        self,
        path: List[str],
        original_name: str,
        *,
        class_name: bool = False,
        singular_name: bool = False,
        unique: bool = False,
        singular_name_suffix: str = 'Item',
        loaded: bool = False,
    ) -> Reference:
        joined_path: str = self._get_path(path)
        if joined_path in self.references:
            reference = self.references[joined_path]
            if loaded and not reference.loaded:
                reference.loaded = True
            return reference
        elif not original_name:
            original_name = Path(joined_path.split('#')[0]).stem
        name = original_name
        if singular_name:
            name = get_singular_name(name, singular_name_suffix)
        if class_name:
            name = self.get_class_name(name, unique)
        elif unique:
            name = self._get_uniq_name(name)
        reference = Reference(
            path=joined_path, original_name=original_name, name=name, loaded=loaded
        )
        self.references[joined_path] = reference
        return reference

    def get(
        self, path: Union[List[str], str]
    ) -> Optional[Reference]:  # pragma: no cover
        if isinstance(path, str):
            return self.references.get(path)
        return self.references[self._get_path(path)]

    def get_class_name(self, field_name: str, unique: bool = True) -> str:
        if '.' in field_name:
            split_name = [self.get_valid_name(n) for n in field_name.split('.')]
            prefix, field_name = '.'.join(split_name[:-1]), split_name[-1]
            prefix += '.'
        else:
            prefix = ''

        field_name = self.get_valid_name(field_name)
        upper_camel_name = snake_to_upper_camel(field_name)
        if unique:
            class_name = self._get_uniq_name(upper_camel_name, camel=True)
        else:
            class_name = upper_camel_name

        return f'{prefix}{class_name}'

    def _get_uniq_name(self, name: str, camel: bool = False) -> str:
        uniq_name: str = name
        count: int = 1
        reference_names = {r.name for r in self.references.values()}
        while uniq_name in reference_names:
            if camel:
                uniq_name = f'{name}{count}'
            else:
                uniq_name = f'{name}_{count}'
            count += 1
        return uniq_name

    @classmethod
    def validate_name(cls, name: str) -> bool:
        return name.isidentifier() and not iskeyword(name)

    @lru_cache()
    def get_valid_name(self, name: str, camel: bool = False) -> str:
        if name.isidentifier():
            return name
        if name[0] == '#':
            name = name[1:]
        # TODO: when first character is a number
        replaced_name = re.sub(r'\W', '_', name)
        if replaced_name[0].isnumeric():
            replaced_name = f'field_{replaced_name}'
        # if replaced_name.isidentifier() and not iskeyword(replaced_name):
        # return self.get_uniq_name(replaced_name, camel)
        return replaced_name

    def get_valid_field_name_and_alias(
        self, field_name: str
    ) -> Tuple[str, Optional[str]]:
        if field_name in self.aliases:
            return self.aliases[field_name], field_name
        valid_name = self.get_valid_name(field_name)
        return valid_name, None if field_name == valid_name else field_name


@lru_cache()
def get_singular_name(name: str, suffix: str = 'Item') -> str:
    singular_name = inflect_engine.singular_noun(name)
    if singular_name is False:
        singular_name = f'{name}{suffix}'
    return singular_name


@lru_cache()
def snake_to_upper_camel(word: str) -> str:
    prefix = ''
    if word.startswith('_'):
        prefix = '_'
        word = word[1:]

    return prefix + ''.join(x[0].upper() + x[1:] for x in word.split('_') if x)


def is_url(ref: str) -> bool:
    return ref.startswith(('https://', 'http://'))


inflect_engine = inflect.engine()
