import re
from keyword import iskeyword
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple, Union

import inflect
from pydantic import BaseModel


class Reference(BaseModel):
    path: str
    original_name: str
    name: str
    loaded: bool = True
    actual_module_name: Optional[str]

    @property
    def module_name(self) -> Optional[str]:
        if self.path.startswith(('https://', 'http://')):  # pragma: no cover
            return None
        # TODO: Support file:///
        path = Path(self.path.split('#')[0])
        module_name = f'{".".join(path.parts[:-1][1:])}.{path.stem}'
        if module_name == '.':
            return None
        return module_name


class ModelResolver:
    def __init__(self, aliases: Optional[Mapping[str, str]] = None) -> None:
        self.references: Dict[str, Reference] = {}
        self.aliases: Mapping[str, str] = {**aliases} if aliases is not None else {}
        self._current_root: List[str] = []

    @property
    def current_root(self) -> List[str]:
        return self._current_root  # pragma: no cover

    def set_current_root(self, current_root: List[str]) -> None:
        self._current_root = current_root

    def _get_path(self, path: List[str]) -> str:
        joined_path = '/'.join(p for p in path if p)
        if '#' in joined_path:  # remote
            delimiter = joined_path.index('#')
            return f"{''.join(joined_path[:delimiter])}#{''.join(joined_path[delimiter + 1:])}"
        return f"{''.join(self._current_root)}#/{'/'.join(path[1:] if '#' in joined_path else path)}"

    def add_ref(self, ref: str, actual_module_name: Optional[str] = None) -> Reference:
        path = self._get_path(ref.split('/'))
        reference = self.references.get(path)
        if reference:
            reference.actual_module_name = actual_module_name
            return reference
        split_ref = ref.rsplit('/', 1)
        if len(split_ref) == 1:
            # TODO Support $id with $ref
            # https://json-schema.org/understanding-json-schema/structuring.html#using-id-with-ref
            raise NotImplementedError('It is not support to use $id with $ref')
        parents, original_name = split_ref  # type: str, str
        loaded: bool = not ref.startswith(('https://', 'http://'))
        if not original_name:
            original_name = Path(parents).stem
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
    ) -> Reference:
        joined_path: str = self._get_path(path)
        if joined_path in self.references:
            return self.references[joined_path]
        if not original_name:
            original_name = Path(joined_path.split('#')[0]).stem
        if class_name:
            name = self.get_class_name(original_name, unique)
            if singular_name:  # pragma: no cover
                name = get_singular_name(name, singular_name_suffix)
        elif singular_name:
            name = get_singular_name(original_name, singular_name_suffix)
            if unique:  # pragma: no cover
                name = self._get_uniq_name(name)
        elif unique:
            name = self._get_uniq_name(original_name)
        else:
            name = original_name
        reference = Reference(path=joined_path, original_name=original_name, name=name)
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
        while uniq_name in [r.name for r in self.references.values()]:
            if camel:
                uniq_name = f'{name}{count}'
            else:
                uniq_name = f'{name}_{count}'
            count += 1
        return uniq_name

    @classmethod
    def validate_name(cls, name: str) -> bool:
        return name.isidentifier() and not iskeyword(name)

    def get_valid_name(self, name: str, camel: bool = False) -> str:
        # TODO: when first character is a number
        replaced_name = re.sub(r'\W', '_', name)
        if re.match(r'^[0-9]', replaced_name):
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


def get_singular_name(name: str, suffix: str = 'Item') -> str:
    singular_name = inflect_engine.singular_noun(name)
    if singular_name is False:
        singular_name = f'{name}{suffix}'
    return singular_name


def snake_to_upper_camel(word: str) -> str:
    prefix = ''
    if word.startswith('_'):
        prefix = '_'
        word = word[1:]

    return prefix + ''.join(x[0].upper() + x[1:] for x in word.split('_') if x)


inflect_engine = inflect.engine()
