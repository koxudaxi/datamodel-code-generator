import re
from collections import defaultdict
from contextlib import contextmanager
from functools import lru_cache
from itertools import zip_longest
from keyword import iskeyword
from pathlib import Path, PurePath
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
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
    TypeVar,
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
    def short_name(self) -> str:
        return self.name.rsplit('.', 1)[-1]


SINGULAR_NAME_SUFFIX: str = 'Item'

ID_PATTERN: Pattern[str] = re.compile(r'^#[^/].*')

T = TypeVar('T')


@contextmanager
def context_variable(
    setter: Callable[[T], None], current_value: T, new_value: T
) -> Generator[None, None, None]:
    previous_value: T = current_value
    setter(new_value)
    try:
        yield
    finally:
        setter(previous_value)


_UNDER_SCORE_1: Pattern[str] = re.compile(r'(.)([A-Z][a-z]+)')
_UNDER_SCORE_2: Pattern[str] = re.compile('([a-z0-9])([A-Z])')


@lru_cache()
def camel_to_snake(string: str) -> str:
    subbed = _UNDER_SCORE_1.sub(r'\1_\2', string)
    return _UNDER_SCORE_2.sub(r'\1_\2', subbed).lower()


class FieldNameResolver:
    def __init__(
        self,
        aliases: Optional[Mapping[str, str]] = None,
        snake_case_field: bool = False,
        empty_field_name: Optional[str] = None,
    ):
        self.aliases: Mapping[str, str] = {} if aliases is None else {**aliases}
        self.empty_field_name: str = empty_field_name or '_'
        self.snake_case_field = snake_case_field

    def get_valid_name(self, name: str, excludes: Optional[Set[str]] = None) -> str:
        if not name:
            name = self.empty_field_name
        if name[0] == '#':
            name = name[1:]
        # TODO: when first character is a number
        name = re.sub(r'\W', '_', name)
        if name[0].isnumeric():
            name = f'field_{name}'
        if self.snake_case_field:
            name = camel_to_snake(name)
        count = 1
        if iskeyword(name):
            name += '_'
        new_name = name
        while not new_name.isidentifier() or (excludes and new_name in excludes):
            new_name = f'{name}_{count}'
            count += 1
        return new_name

    def get_valid_field_name_and_alias(
        self, field_name: str, excludes: Optional[Set[str]] = None
    ) -> Tuple[str, Optional[str]]:
        if field_name in self.aliases:
            return self.aliases[field_name], field_name
        valid_name = self.get_valid_name(field_name, excludes=excludes)
        return valid_name, None if field_name == valid_name else field_name


def get_relative_path(base_path: PurePath, target_path: PurePath) -> PurePath:
    if base_path == target_path:
        return Path('.')
    if not target_path.is_absolute():
        return target_path
    parent_count: int = 0
    children: List[str] = []
    for base_part, target_part in zip_longest(base_path.parts, target_path.parts):
        if base_part == target_part and not parent_count:
            continue
        if base_part or not target_part:
            parent_count += 1
        if target_part:
            children.append(target_part)
    return Path(*['..' for _ in range(parent_count)], *children)


class ModelResolver:
    def __init__(
        self,
        exclude_names: Set[str] = None,
        duplicate_name_suffix: Optional[str] = None,
        base_url: Optional[str] = None,
        singular_name_suffix: Optional[str] = None,
        aliases: Optional[Mapping[str, str]] = None,
        snake_case_field: bool = False,
        empty_field_name: Optional[str] = None,
        custom_class_name_generator: Optional[Callable[[str], str]] = None,
        base_path: Optional[Path] = None,
    ) -> None:
        self.references: Dict[str, Reference] = {}
        self._current_root: Sequence[str] = []
        self._root_id: Optional[str] = None
        self._root_id_base_path: Optional[str] = None
        self.ids: DefaultDict[str, Dict[str, str]] = defaultdict(dict)
        self.after_load_files: Set[str] = set()
        self.exclude_names: Set[str] = exclude_names or set()
        self.duplicate_name_suffix: Optional[str] = duplicate_name_suffix
        self._base_url: Optional[str] = base_url
        self.singular_name_suffix: str = singular_name_suffix if isinstance(
            singular_name_suffix, str
        ) else SINGULAR_NAME_SUFFIX
        self.field_name_resolver = FieldNameResolver(
            aliases=aliases,
            snake_case_field=snake_case_field,
            empty_field_name=empty_field_name,
        )
        self.class_name_generator = (
            custom_class_name_generator or self.default_class_name_generator
        )
        self._base_path: Path = base_path or Path.cwd()
        self._current_base_path: Optional[Path] = self._base_path

    @property
    def current_base_path(self) -> Optional[Path]:
        return self._current_base_path

    def set_current_base_path(self, base_path: Optional[Path]) -> None:
        self._current_base_path = base_path

    @property
    def base_url(self) -> Optional[str]:
        return self._base_url

    def set_base_url(self, base_url: Optional[str]) -> None:
        self._base_url = base_url

    @contextmanager
    def current_base_path_context(
        self, base_path: Optional[Path]
    ) -> Generator[None, None, None]:
        if base_path:
            base_path = (self._base_path / base_path).resolve()
        with context_variable(
            self.set_current_base_path, self.current_base_path, base_path
        ):
            yield

    @contextmanager
    def base_url_context(self, base_url: str) -> Generator[None, None, None]:

        if self._base_url:
            with context_variable(self.set_base_url, self.base_url, base_url):
                yield
        else:
            yield

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
        with context_variable(self.set_current_root, self.current_root, current_root):
            yield

    @property
    def root_id(self) -> Optional[str]:
        return self._root_id

    @property
    def root_id_base_path(self) -> Optional[str]:
        return self._root_id_base_path

    def set_root_id(self, root_id: Optional[str]) -> None:
        if root_id and '/' in root_id:
            self._root_id_base_path = root_id.rsplit('/', 1)[0]
        else:
            self._root_id_base_path = None

        self._root_id = root_id

    def add_id(self, id_: str, path: Sequence[str]) -> None:
        self.ids['/'.join(self.current_root)][id_] = self.resolve_ref(path)

    def resolve_ref(self, path: Union[Sequence[str], str]) -> str:
        if isinstance(path, str):
            joined_path = path
        else:
            joined_path = self.join_path(path)
        if joined_path == '#':
            return f"{'/'.join(self.current_root)}#"
        if (
            self.current_base_path
            and not self.base_url
            and joined_path[0] != '#'
            and not is_url(joined_path)
        ):
            # resolve local file path
            file_path, *object_part = joined_path.split('#', 1)
            resolved_file_path = Path(self.current_base_path, file_path).resolve()
            joined_path = get_relative_path(
                self._base_path, resolved_file_path
            ).as_posix()
            if object_part:
                joined_path += f'#{object_part[0]}'
        if ID_PATTERN.match(joined_path):
            ref: str = self.ids['/'.join(self.current_root)][joined_path]
        elif (
            '#' not in joined_path
            and self.root_id_base_path
            and self.current_root != path
        ):
            if Path(self._base_path, joined_path).is_file():
                ref = f'{joined_path}#'
            else:
                ref = f'{self.root_id_base_path}/{joined_path}#'
        else:
            if '#' not in joined_path:
                joined_path += '#'
            if joined_path[0] == '#':
                joined_path = f'{"/".join(self.current_root)}{joined_path}'
            delimiter = joined_path.index('#')
            ref = f"{''.join(joined_path[:delimiter])}#{''.join(joined_path[delimiter + 1:])}"
        if self.base_url:
            from .http import join_url

            return join_url(self.base_url, ref)
        if is_url(ref):
            file_part, path_part = ref.split('#', 1)
            if file_part == self.root_id:
                return f'{"/".join(self.current_root)}#{path_part}'
        return ref

    def is_after_load(self, ref: str) -> bool:
        if is_url(ref) or not self.current_base_path:
            return False
        file_part, *_ = ref.split('#', 1)
        absolute_path = Path(self._base_path, file_part).resolve().as_posix()
        if self.is_external_root_ref(ref):
            return absolute_path in self.after_load_files
        elif self.is_external_ref(ref):
            return absolute_path in self.after_load_files
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
                split_ref[0][:-1] if self.is_external_root_ref(path) else split_ref[0]
            ).stem
        else:
            original_name = (
                Path(split_ref[1][:-1]).stem
                if self.is_external_root_ref(path)
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
        unique: bool = True,
        singular_name_suffix: Optional[str] = None,
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
        if class_name:
            name = self.get_class_name(
                name=name,
                unique=unique,
                reserved_name=reference.name if reference else None,
                singular_name=singular_name,
                singular_name_suffix=singular_name_suffix,
            )
        else:
            name = self.get_valid_name(name)
            if singular_name:  # pragma: no cover
                name = get_singular_name(
                    name, singular_name_suffix or self.singular_name_suffix
                )
            elif unique:  # pragma: no cover
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

    def default_class_name_generator(self, name: str) -> str:
        name = self.field_name_resolver.get_valid_name(name)
        return snake_to_upper_camel(name)

    def get_class_name(
        self,
        name: str,
        unique: bool = True,
        reserved_name: Optional[str] = None,
        singular_name: bool = False,
        singular_name_suffix: Optional[str] = None,
    ) -> str:

        if '.' in name:
            split_name = name.split('.')
            prefix = '.'.join(
                self.field_name_resolver.get_valid_name(n) for n in split_name[:-1]
            )
            prefix += '.'
            class_name = split_name[-1]
        else:
            prefix = ''
            class_name = name

        class_name = self.class_name_generator(class_name)

        if singular_name:
            class_name = get_singular_name(
                class_name, singular_name_suffix or self.singular_name_suffix
            )

        if unique:
            if reserved_name == class_name:
                return class_name
            class_name = self._get_uniq_name(class_name, camel=True)

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

    def get_valid_name(self, name: str, excludes: Optional[Set[str]] = None) -> str:
        return self.field_name_resolver.get_valid_name(name, excludes)

    def get_valid_field_name_and_alias(
        self, field_name: str, excludes: Optional[Set[str]] = None
    ) -> Tuple[str, Optional[str]]:
        return self.field_name_resolver.get_valid_field_name_and_alias(
            field_name, excludes
        )


@lru_cache()
def get_singular_name(name: str, suffix: str = SINGULAR_NAME_SUFFIX) -> str:
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
