import re
from collections import defaultdict
from contextlib import contextmanager
from functools import lru_cache
from keyword import iskeyword
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    DefaultDict,
    Dict,
    Generator,
    List,
    Mapping,
    Optional,
    Pattern,
    Sequence,
    Set,
    Tuple,
    Union,
)

import inflect
from pydantic import BaseModel, validator

from datamodel_code_generator import cached_property

if TYPE_CHECKING:
    from pydantic.typing import AbstractSetIntStr, DictStrAny, MappingIntStrAny


class _BaseModel(BaseModel):
    _exclude_fields: ClassVar[Set[str]] = set()
    _pass_fields: ClassVar[Set[str]] = set()

    def __init__(self, **values: Any) -> None:  # type: ignore
        super().__init__(**values)
        for pass_field_name in self._pass_fields:
            if pass_field_name in values:
                setattr(self, pass_field_name, values[pass_field_name])

    def dict(
        self,
        *,
        include: Union['AbstractSetIntStr', 'MappingIntStrAny'] = None,
        exclude: Union['AbstractSetIntStr', 'MappingIntStrAny'] = None,
        by_alias: bool = False,
        skip_defaults: bool = None,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
    ) -> 'DictStrAny':
        return super().dict(
            include=include,
            exclude=set(exclude or ()) | self._exclude_fields,
            by_alias=by_alias,
            skip_defaults=skip_defaults,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
        )


class Reference(_BaseModel):
    path: str
    original_name: str = ''
    name: str
    loaded: bool = True
    source: Optional[Any] = None
    children: List[Any] = []
    _exclude_fields: ClassVar = {'children'}

    @validator('original_name')
    def validate_original_name(cls, v: Any, values: Dict[str, Any]) -> str:
        """
        If original_name is empty then, `original_name` is assigned `name`
        """
        if v:  # pragma: no cover
            return v
        return values.get('name', v)  # pragma: no cover

    class Config:
        arbitrary_types_allowed = True
        keep_untouched = (cached_property,)

    @property
    def module_name(self) -> Optional[str]:
        if is_url(self.path):  # pragma: no cover
            return None
        # TODO: Support file:///
        path = Path(self.path.split('#')[0])

        # workaround: If a file name has dot then, this method uses first part.
        module_name = f'{".".join(path.parts[:-1])}.{path.stem.split(".")[0]}'
        if module_name.startswith(f'.{self.name.split(".", 1)[0]}'):
            return None
        elif module_name == '.':  # pragma: no cover
            return None
        return module_name

    @property
    def short_name(self) -> str:
        return self.name.rsplit('.', 1)[-1]


ID_PATTERN: Pattern[str] = re.compile(r'^#[^/].*')


class ModelResolver:
    def __init__(
        self,
        aliases: Optional[Mapping[str, str]] = None,
        exclude_names: Set[str] = None,
        duplicate_name_suffix: Optional[str] = None,
    ) -> None:
        self.references: Dict[str, Reference] = {}
        self.aliases: Mapping[str, str] = {} if aliases is None else {**aliases}
        self._current_root: Sequence[str] = []
        self._root_id_base_path: Optional[str] = None
        self.ids: DefaultDict[str, Dict[str, str]] = defaultdict(dict)
        self.after_load_files: Set[str] = set()
        self.exclude_names: Set[str] = exclude_names or set()
        self.duplicate_name_suffix: Optional[str] = duplicate_name_suffix

    @property
    def current_root(self) -> Sequence[str]:
        if len(self._current_root) > 1:
            return self._current_root
        return self._current_root

    def set_current_root(self, current_root: Sequence[str]) -> None:
        self._current_root = current_root

    @contextmanager
    def current_root_context(
        self, current_root: Sequence[str]
    ) -> Generator[None, None, None]:
        previous_root_path: Sequence[str] = self.current_root
        self.set_current_root(current_root)
        yield
        self.set_current_root(previous_root_path)

    @property
    def root_id_base_path(self) -> Optional[str]:
        return self._root_id_base_path

    def set_root_id_base_path(self, root_id_base_path: Optional[str]) -> None:
        self._root_id_base_path = root_id_base_path

    def add_id(self, id_: str, path: Sequence[str]) -> None:
        self.ids['/'.join(self.current_root)][id_] = self.resolve_ref(path)

    def resolve_ref(self, path: Union[Sequence[str], str]) -> str:
        if isinstance(path, str):
            joined_path = path
        else:
            joined_path = self.join_path(path)
        if ID_PATTERN.match(joined_path):
            return self.ids['/'.join(self.current_root)][joined_path]
        elif '#' in joined_path:
            if joined_path[0] == '#':
                joined_path = f'{"/".join(self.current_root)}{joined_path}'
            if self.is_remote_ref(joined_path):
                return f'{"/".join(self.current_root[:-1])}/{joined_path}'
            delimiter = joined_path.index('#')
            return f"{''.join(joined_path[:delimiter])}#{''.join(joined_path[delimiter + 1:])}"
        elif self.root_id_base_path and self.current_root != path:
            return f'{self.root_id_base_path}/{joined_path}#'
        joined_path = f'{joined_path}#'
        if self.is_remote_ref(joined_path):
            return f'{"/".join(self.current_root[:-1])}/{joined_path}'
        return joined_path

    def is_remote_ref(self, resolved_ref: str) -> bool:
        return (
            self.is_external_ref(resolved_ref)
            and not is_url(resolved_ref)
            and len(self.current_root) > 1
        )

    def is_after_load(self, ref: str) -> bool:
        ref = self.resolve_ref(ref)
        if self.is_external_root_ref(ref):
            return ref[:-1] in self.after_load_files
        elif self.is_external_ref(ref):
            return ref.split('#/', 1)[0] in self.after_load_files
        return False  # pragma: no cover

    @staticmethod
    def is_external_ref(ref: str) -> bool:
        return '#' in ref and ref[0] != '#'

    @staticmethod
    def is_external_root_ref(ref: str) -> bool:
        return ref[-1] == '#'

    @staticmethod
    def join_path(path: Sequence[str]) -> str:
        joined_path = '/'.join(p for p in path if p).replace('/#', '#')
        if '#' not in joined_path:
            joined_path += '#'
        return joined_path

    def add_ref(self, ref: str, resolved: bool = False) -> Reference:
        if not resolved:
            path = self.resolve_ref(ref)
        else:
            path = ref
        reference = self.references.get(path)
        if reference:
            return reference
        split_ref = ref.rsplit('/', 1)
        if len(split_ref) == 1:
            original_name = Path(
                split_ref[0][:-1] if self.is_external_root_ref(ref) else split_ref[0]
            ).stem
        else:
            original_name = (
                Path(split_ref[1][:-1]).stem
                if self.is_external_root_ref(ref)
                else split_ref[1]
            )
        name = self.get_class_name(original_name, unique=False)
        reference = Reference(
            path=path, original_name=original_name, name=name, loaded=False,
        )

        self.references[path] = reference
        return reference

    def add(
        self,
        path: Sequence[str],
        original_name: str,
        *,
        class_name: bool = False,
        singular_name: bool = False,
        unique: bool = False,
        singular_name_suffix: str = 'Item',
        loaded: bool = False,
    ) -> Reference:
        joined_path = self.join_path(path)
        reference: Optional[Reference] = self.references.get(joined_path)
        if reference:
            if loaded and not reference.loaded:
                reference.loaded = True
            if (
                not original_name
                or original_name == reference.original_name
                or original_name == reference.name
            ):
                return reference
        name = original_name
        if singular_name:
            name = get_singular_name(name, singular_name_suffix)
        if class_name:
            name = self.get_class_name(name, unique)
        elif unique:
            name = self._get_uniq_name(name)
        if reference:
            reference.original_name = original_name
            reference.name = name
            reference.loaded = loaded
        else:
            reference = Reference(
                path=joined_path, original_name=original_name, name=name, loaded=loaded
            )
            self.references[joined_path] = reference
        return reference

    def get(self, path: Union[Sequence[str], str]) -> Optional[Reference]:
        return self.references.get(self.resolve_ref(path))

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
        reference_names = {
            r.name for r in self.references.values()
        } | self.exclude_names
        while uniq_name in reference_names:
            if self.duplicate_name_suffix:
                name_parts: List[Union[str, int]] = [
                    name,
                    self.duplicate_name_suffix,
                    count - 1,
                ]
            else:
                name_parts = [name, count]
            delimiter = '' if camel else '_'
            uniq_name = delimiter.join(str(p) for p in name_parts if p)
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
