import re
from collections import defaultdict
from contextlib import contextmanager
from enum import Enum, auto
from functools import lru_cache
from itertools import zip_longest
from keyword import iskeyword
from pathlib import Path, PurePath
from typing import (
    TYPE_CHECKING,
    AbstractSet,
    Any,
    Callable,
    ClassVar,
    DefaultDict,
    Dict,
    Generator,
    List,
    Mapping,
    NamedTuple,
    Optional,
    Pattern,
    Sequence,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
)
from urllib.parse import ParseResult, urlparse

import inflect
import pydantic
from packaging import version
from pydantic import BaseModel

from datamodel_code_generator.util import (
    PYDANTIC_V2,
    ConfigDict,
    cached_property,
    model_validator,
)

if TYPE_CHECKING:
    from pydantic.typing import DictStrAny


class _BaseModel(BaseModel):
    _exclude_fields: ClassVar[Set[str]] = set()
    _pass_fields: ClassVar[Set[str]] = set()

    if not TYPE_CHECKING:

        def __init__(self, **values: Any) -> None:
            super().__init__(**values)
            for pass_field_name in self._pass_fields:
                if pass_field_name in values:
                    setattr(self, pass_field_name, values[pass_field_name])

    if not TYPE_CHECKING:
        if PYDANTIC_V2:

            def dict(
                self,
                *,
                include: Union[
                    AbstractSet[Union[int, str]], Mapping[Union[int, str], Any], None
                ] = None,
                exclude: Union[
                    AbstractSet[Union[int, str]], Mapping[Union[int, str], Any], None
                ] = None,
                by_alias: bool = False,
                exclude_unset: bool = False,
                exclude_defaults: bool = False,
                exclude_none: bool = False,
            ) -> 'DictStrAny':
                return self.model_dump(
                    include=include,
                    exclude=set(exclude or ()) | self._exclude_fields,
                    by_alias=by_alias,
                    exclude_unset=exclude_unset,
                    exclude_defaults=exclude_defaults,
                    exclude_none=exclude_none,
                )

        else:

            def dict(
                self,
                *,
                include: Union[
                    AbstractSet[Union[int, str]], Mapping[Union[int, str], Any], None
                ] = None,
                exclude: Union[
                    AbstractSet[Union[int, str]], Mapping[Union[int, str], Any], None
                ] = None,
                by_alias: bool = False,
                skip_defaults: Optional[bool] = None,
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
    duplicate_name: Optional[str] = None
    loaded: bool = True
    source: Optional[Any] = None
    children: List[Any] = []
    _exclude_fields: ClassVar[Set[str]] = {'children'}

    @model_validator(mode='before')
    def validate_original_name(cls, values: Any) -> Any:
        """
        If original_name is empty then, `original_name` is assigned `name`
        """
        if not isinstance(values, dict):  # pragma: no cover
            return values
        original_name = values.get('original_name')
        if original_name:
            return values

        values['original_name'] = values.get('name', original_name)
        return values

    if PYDANTIC_V2:
        # TODO[pydantic]: The following keys were removed: `copy_on_model_validation`.
        # Check https://docs.pydantic.dev/dev-v2/migration/#changes-to-config for more information.
        model_config = ConfigDict(
            arbitrary_types_allowed=True,
            ignored_types=(cached_property,),
            revalidate_instances='never',
        )
    else:

        class Config:
            arbitrary_types_allowed = True
            keep_untouched = (cached_property,)
            copy_on_model_validation = (
                False
                if version.parse(pydantic.VERSION) < version.parse('1.9.2')
                else 'none'
            )

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


_UNDER_SCORE_1: Pattern[str] = re.compile(r'([^_])([A-Z][a-z]+)')
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
        original_delimiter: Optional[str] = None,
        special_field_name_prefix: Optional[str] = None,
        remove_special_field_name_prefix: bool = False,
        capitalise_enum_members: bool = False,
    ):
        self.aliases: Mapping[str, str] = {} if aliases is None else {**aliases}
        self.empty_field_name: str = empty_field_name or '_'
        self.snake_case_field = snake_case_field
        self.original_delimiter: Optional[str] = original_delimiter
        self.special_field_name_prefix: Optional[str] = (
            'field' if special_field_name_prefix is None else special_field_name_prefix
        )
        self.remove_special_field_name_prefix: bool = remove_special_field_name_prefix
        self.capitalise_enum_members: bool = capitalise_enum_members

    @classmethod
    def _validate_field_name(cls, field_name: str) -> bool:
        return True

    def get_valid_name(
        self,
        name: str,
        excludes: Optional[Set[str]] = None,
        ignore_snake_case_field: bool = False,
        upper_camel: bool = False,
    ) -> str:
        if not name:
            name = self.empty_field_name
        if name[0] == '#':
            name = name[1:] or self.empty_field_name

        if (
            self.snake_case_field
            and not ignore_snake_case_field
            and self.original_delimiter is not None
        ):
            name = snake_to_upper_camel(name, delimiter=self.original_delimiter)

        name = re.sub(r'[¹²³⁴⁵⁶⁷⁸⁹]|\W', '_', name)
        if name[0].isnumeric():
            name = f'{self.special_field_name_prefix}_{name}'

        # We should avoid having a field begin with an underscore, as it
        # causes pydantic to consider it as private
        while name.startswith('_'):
            if self.remove_special_field_name_prefix:
                name = name[1:]
            else:
                name = f'{self.special_field_name_prefix}{name}'
                break
        if (
            self.capitalise_enum_members
            or self.snake_case_field
            and not ignore_snake_case_field
        ):
            name = camel_to_snake(name)
        count = 1
        if iskeyword(name) or not self._validate_field_name(name):
            name += '_'
        if upper_camel:
            new_name = snake_to_upper_camel(name)
        elif self.capitalise_enum_members:
            new_name = name.upper()
        else:
            new_name = name
        while (
            not (new_name.isidentifier() or not self._validate_field_name(new_name))
            or iskeyword(new_name)
            or (excludes and new_name in excludes)
        ):
            new_name = f'{name}{count}' if upper_camel else f'{name}_{count}'
            count += 1
        return new_name

    def get_valid_field_name_and_alias(
        self, field_name: str, excludes: Optional[Set[str]] = None
    ) -> Tuple[str, Optional[str]]:
        if field_name in self.aliases:
            return self.aliases[field_name], field_name
        valid_name = self.get_valid_name(field_name, excludes=excludes)
        return valid_name, None if field_name == valid_name else field_name


class PydanticFieldNameResolver(FieldNameResolver):
    @classmethod
    def _validate_field_name(cls, field_name: str) -> bool:
        # TODO: Support Pydantic V2
        return not hasattr(BaseModel, field_name)


class EnumFieldNameResolver(FieldNameResolver):
    def get_valid_name(
        self,
        name: str,
        excludes: Optional[Set[str]] = None,
        ignore_snake_case_field: bool = False,
        upper_camel: bool = False,
    ) -> str:
        return super().get_valid_name(
            name='mro_' if name == 'mro' else name,
            excludes={'mro'} | (excludes or set()),
            ignore_snake_case_field=ignore_snake_case_field,
            upper_camel=upper_camel,
        )


class ModelType(Enum):
    PYDANTIC = auto()
    ENUM = auto()
    CLASS = auto()


DEFAULT_FIELD_NAME_RESOLVERS: Dict[ModelType, Type[FieldNameResolver]] = {
    ModelType.ENUM: EnumFieldNameResolver,
    ModelType.PYDANTIC: PydanticFieldNameResolver,
    ModelType.CLASS: FieldNameResolver,
}


class ClassName(NamedTuple):
    name: str
    duplicate_name: Optional[str]


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
        exclude_names: Optional[Set[str]] = None,
        duplicate_name_suffix: Optional[str] = None,
        base_url: Optional[str] = None,
        singular_name_suffix: Optional[str] = None,
        aliases: Optional[Mapping[str, str]] = None,
        snake_case_field: bool = False,
        empty_field_name: Optional[str] = None,
        custom_class_name_generator: Optional[Callable[[str], str]] = None,
        base_path: Optional[Path] = None,
        field_name_resolver_classes: Optional[
            Dict[ModelType, Type[FieldNameResolver]]
        ] = None,
        original_field_name_delimiter: Optional[str] = None,
        special_field_name_prefix: Optional[str] = None,
        remove_special_field_name_prefix: bool = False,
        capitalise_enum_members: bool = False,
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
        self.singular_name_suffix: str = (
            singular_name_suffix
            if isinstance(singular_name_suffix, str)
            else SINGULAR_NAME_SUFFIX
        )
        merged_field_name_resolver_classes = DEFAULT_FIELD_NAME_RESOLVERS.copy()
        if field_name_resolver_classes:  # pragma: no cover
            merged_field_name_resolver_classes.update(field_name_resolver_classes)
        self.field_name_resolvers: Dict[ModelType, FieldNameResolver] = {
            k: v(
                aliases=aliases,
                snake_case_field=snake_case_field,
                empty_field_name=empty_field_name,
                original_delimiter=original_field_name_delimiter,
                special_field_name_prefix=special_field_name_prefix,
                remove_special_field_name_prefix=remove_special_field_name_prefix,
                capitalise_enum_members=capitalise_enum_members
                if k == ModelType.ENUM
                else False,
            )
            for k, v in merged_field_name_resolver_classes.items()
        }
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
        else:
            if '#' not in joined_path:
                joined_path += '#'
            elif joined_path[0] == '#':
                joined_path = f'{"/".join(self.current_root)}{joined_path}'

            delimiter = joined_path.index('#')
            file_path = ''.join(joined_path[:delimiter])
            ref = f"{''.join(joined_path[:delimiter])}#{''.join(joined_path[delimiter + 1:])}"
            if self.root_id_base_path and not (
                is_url(joined_path) or Path(self._base_path, file_path).is_file()
            ):
                ref = f'{self.root_id_base_path}/{ref}'

        if self.base_url:
            from .http import join_url

            joined_url = join_url(self.base_url, ref)
            if '#' in joined_url:
                return joined_url
            return f'{joined_url}#'

        if is_url(ref):
            file_part, path_part = ref.split('#', 1)
            if file_part == self.root_id:
                return f'{"/".join(self.current_root)}#{path_part}'
            target_url: ParseResult = urlparse(file_part)
            if not (self.root_id and self.current_base_path):
                return ref
            root_id_url: ParseResult = urlparse(self.root_id)
            if (target_url.scheme, target_url.netloc) == (
                root_id_url.scheme,
                root_id_url.netloc,
            ):  # pragma: no cover
                target_url_path = Path(target_url.path)
                relative_target_base = get_relative_path(
                    Path(root_id_url.path).parent, target_url_path.parent
                )
                target_path = (
                    self.current_base_path / relative_target_base / target_url_path.name
                )
                if target_path.exists():
                    return f'{target_path.resolve().relative_to(self._base_path)}#{path_part}'

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
        name = self.get_class_name(original_name, unique=False).name
        reference = Reference(
            path=path,
            original_name=original_name,
            name=name,
            loaded=False,
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
        duplicate_name: Optional[str] = None
        if class_name:
            name, duplicate_name = self.get_class_name(
                name=name,
                unique=unique,
                reserved_name=reference.name if reference else None,
                singular_name=singular_name,
                singular_name_suffix=singular_name_suffix,
            )
        else:
            # TODO: create a validate for module name
            name = self.get_valid_field_name(name, model_type=ModelType.CLASS)
            if singular_name:  # pragma: no cover
                name = get_singular_name(
                    name, singular_name_suffix or self.singular_name_suffix
                )
            elif unique:  # pragma: no cover
                unique_name = self._get_unique_name(name)
                if unique_name == name:
                    duplicate_name = name
                name = unique_name
        if reference:
            reference.original_name = original_name
            reference.name = name
            reference.loaded = loaded
            reference.duplicate_name = duplicate_name
        else:
            reference = Reference(
                path=joined_path,
                original_name=original_name,
                name=name,
                loaded=loaded,
                duplicate_name=duplicate_name,
            )
            self.references[joined_path] = reference
        return reference

    def get(self, path: Union[Sequence[str], str]) -> Optional[Reference]:
        return self.references.get(self.resolve_ref(path))

    def delete(self, path: Union[Sequence[str], str]) -> None:
        if self.resolve_ref(path) in self.references:
            del self.references[self.resolve_ref(path)]

    def default_class_name_generator(self, name: str) -> str:
        # TODO: create a validate for class name
        return self.field_name_resolvers[ModelType.CLASS].get_valid_name(
            name, ignore_snake_case_field=True, upper_camel=True
        )

    def get_class_name(
        self,
        name: str,
        unique: bool = True,
        reserved_name: Optional[str] = None,
        singular_name: bool = False,
        singular_name_suffix: Optional[str] = None,
    ) -> ClassName:
        if '.' in name:
            split_name = name.split('.')
            prefix = '.'.join(
                # TODO: create a validate for class name
                self.field_name_resolvers[ModelType.CLASS].get_valid_name(
                    n, ignore_snake_case_field=True
                )
                for n in split_name[:-1]
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
        duplicate_name: Optional[str] = None
        if unique:
            if reserved_name == class_name:
                return ClassName(name=class_name, duplicate_name=duplicate_name)

            unique_name = self._get_unique_name(class_name, camel=True)
            if unique_name != class_name:
                duplicate_name = class_name
            class_name = unique_name
        return ClassName(name=f'{prefix}{class_name}', duplicate_name=duplicate_name)

    def _get_unique_name(self, name: str, camel: bool = False) -> str:
        unique_name: str = name
        count: int = 1
        reference_names = {
            r.name for r in self.references.values()
        } | self.exclude_names
        while unique_name in reference_names:
            if self.duplicate_name_suffix:
                name_parts: List[Union[str, int]] = [
                    name,
                    self.duplicate_name_suffix,
                    count - 1,
                ]
            else:
                name_parts = [name, count]
            delimiter = '' if camel else '_'
            unique_name = delimiter.join(str(p) for p in name_parts if p)
            count += 1
        return unique_name

    @classmethod
    def validate_name(cls, name: str) -> bool:
        return name.isidentifier() and not iskeyword(name)

    def get_valid_field_name(
        self,
        name: str,
        excludes: Optional[Set[str]] = None,
        model_type: ModelType = ModelType.PYDANTIC,
    ) -> str:
        return self.field_name_resolvers[model_type].get_valid_name(name, excludes)

    def get_valid_field_name_and_alias(
        self,
        field_name: str,
        excludes: Optional[Set[str]] = None,
        model_type: ModelType = ModelType.PYDANTIC,
    ) -> Tuple[str, Optional[str]]:
        return self.field_name_resolvers[model_type].get_valid_field_name_and_alias(
            field_name, excludes
        )


@lru_cache()
def get_singular_name(name: str, suffix: str = SINGULAR_NAME_SUFFIX) -> str:
    singular_name = inflect_engine.singular_noun(name)
    if singular_name is False:
        singular_name = f'{name}{suffix}'
    return singular_name


@lru_cache()
def snake_to_upper_camel(word: str, delimiter: str = '_') -> str:
    prefix = ''
    if word.startswith(delimiter):
        prefix = '_'
        word = word[1:]

    return prefix + ''.join(x[0].upper() + x[1:] for x in word.split(delimiter) if x)


def is_url(ref: str) -> bool:
    return ref.startswith(('https://', 'http://'))


inflect_engine = inflect.engine()
