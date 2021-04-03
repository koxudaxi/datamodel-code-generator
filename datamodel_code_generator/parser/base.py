import re
from abc import ABC, abstractmethod
from collections import OrderedDict, defaultdict
from itertools import groupby
from pathlib import Path
from typing import (
    Any,
    Callable,
    DefaultDict,
    Dict,
    Iterable,
    Iterator,
    List,
    Mapping,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
    Union,
)
from urllib.parse import ParseResult

from pydantic import BaseModel

from datamodel_code_generator import Protocol, runtime_checkable
from datamodel_code_generator.format import CodeFormatter, PythonVersion
from datamodel_code_generator.imports import IMPORT_ANNOTATIONS, Import, Imports
from datamodel_code_generator.model import pydantic as pydantic_model
from datamodel_code_generator.model.base import (
    ALL_MODEL,
    BaseClassDataType,
    DataModel,
    DataModelFieldBase,
)
from datamodel_code_generator.model.enum import Enum
from datamodel_code_generator.parser import DefaultPutDict, LiteralType
from datamodel_code_generator.reference import ModelResolver, Reference
from datamodel_code_generator.types import DataType, DataTypeManager, StrictTypes

escape_characters = str.maketrans(
    {
        "\\": r"\\",
        "'": r"\'",
        '\b': r'\b',
        '\f': r'\f',
        '\n': r'\n',
        '\r': r'\r',
        '\t': r'\t',
    }
)


def to_hashable(item: Any) -> Any:
    if isinstance(item, list):
        return tuple(to_hashable(i) for i in item)
    elif isinstance(item, dict):
        return tuple(sorted((k, to_hashable(v),) for k, v in item.items()))
    elif isinstance(item, set):  # pragma: no cover
        return frozenset(to_hashable(i) for i in item)
    elif isinstance(item, BaseModel):
        return to_hashable(item.dict())
    return item


def dump_templates(templates: List[DataModel]) -> str:
    return '\n\n\n'.join(str(m) for m in templates)


ReferenceMapSet = Dict[str, Set[str]]
SortedDataModels = Dict[str, DataModel]

MAX_RECURSION_COUNT: int = 100


def sort_data_models(
    unsorted_data_models: List[DataModel],
    sorted_data_models: Optional[SortedDataModels] = None,
    require_update_action_models: Optional[List[str]] = None,
    recursion_count: int = MAX_RECURSION_COUNT,
) -> Tuple[List[DataModel], SortedDataModels, List[str]]:
    if sorted_data_models is None:
        sorted_data_models = OrderedDict()
    if require_update_action_models is None:
        require_update_action_models = []

    unresolved_references: List[DataModel] = []
    for model in unsorted_data_models:
        if not model.reference_classes:
            sorted_data_models[model.path] = model
        elif (
            model.path in model.reference_classes and len(model.reference_classes) == 1
        ):  # only self-referencing
            sorted_data_models[model.path] = model
            require_update_action_models.append(model.path)
        elif (
            not model.reference_classes - {model.path} - set(sorted_data_models)
        ):  # reference classes have been resolved
            sorted_data_models[model.path] = model
            if model.path in model.reference_classes:
                require_update_action_models.append(model.path)
        else:
            unresolved_references.append(model)
    if unresolved_references:
        if recursion_count:
            try:
                return sort_data_models(
                    unresolved_references,
                    sorted_data_models,
                    require_update_action_models,
                    recursion_count - 1,
                )
            except RecursionError:
                pass

        # sort on base_class dependency
        while True:
            ordered_models: List[Tuple[int, DataModel]] = []
            unresolved_reference_model_names = [m.path for m in unresolved_references]
            for model in unresolved_references:
                indexes = [
                    unresolved_reference_model_names.index(b.reference.path)
                    for b in model.base_classes
                    if b.reference
                    and b.reference.path in unresolved_reference_model_names
                ]
                if indexes:
                    ordered_models.append((min(indexes), model,))
                else:
                    ordered_models.append((-1, model,))
            sorted_unresolved_models = [
                m[1] for m in sorted(ordered_models, key=lambda m: m[0])
            ]
            if sorted_unresolved_models == unresolved_references:
                break
            unresolved_references = sorted_unresolved_models

        # circular reference
        unsorted_data_model_names = set(unresolved_reference_model_names)
        for model in unresolved_references:
            unresolved_model = (
                model.reference_classes - {model.path} - set(sorted_data_models)
            )
            if not unresolved_model:
                sorted_data_models[model.path] = model
                continue
            if not unresolved_model - unsorted_data_model_names:
                sorted_data_models[model.path] = model
                require_update_action_models.append(model.path)
                continue
            # unresolved
            unresolved_classes = ', '.join(
                f"[class: {item.path} references: {item.reference_classes}]"
                for item in unresolved_references
            )
            raise Exception(f'A Parser can not resolve classes: {unresolved_classes}.')
    return unresolved_references, sorted_data_models, require_update_action_models


def relative(current_module: str, reference: str) -> Tuple[str, str]:
    """Find relative module path."""

    current_module_path = current_module.split('.') if current_module else []
    *reference_path, name = reference.split('.')

    if current_module_path == reference_path:
        return '', ''

    i = 0
    for x, y in zip(current_module_path, reference_path):
        if x != y:
            break
        i += 1

    left = '.' * (len(current_module_path) - i)
    right = '.'.join(reference_path[i:])

    if not left:
        left = '.'
    if not right:
        right = name
    elif '.' in right:
        extra, right = right.rsplit('.', 1)
        left += extra

    return left, right


@runtime_checkable
class Child(Protocol):
    @property
    def parent(self) -> Optional[Any]:
        raise NotImplementedError


def get_most_of_parent(value: Any) -> Optional[Any]:
    if isinstance(value, Child):
        return get_most_of_parent(value.parent)
    return value


def title_to_class_name(title: str) -> str:
    classname = re.sub('[^A-Za-z0-9]+', ' ', title)
    classname = ''.join(x for x in classname.title() if not x.isspace())
    return classname


class Result(BaseModel):
    body: str
    source: Optional[Path]


class Source(BaseModel):
    path: Path
    text: str

    @classmethod
    def from_path(cls, path: Path, base_path: Path, encoding: str) -> 'Source':
        return cls(
            path=path.relative_to(base_path), text=path.read_text(encoding=encoding),
        )


class Parser(ABC):
    def __init__(
        self,
        source: Union[str, Path, List[Path], ParseResult],
        *,
        data_model_type: Type[DataModel] = pydantic_model.BaseModel,
        data_model_root_type: Type[DataModel] = pydantic_model.CustomRootType,
        data_type_manager_type: Type[DataTypeManager] = pydantic_model.DataTypeManager,
        data_model_field_type: Type[DataModelFieldBase] = pydantic_model.DataModelField,
        base_class: Optional[str] = None,
        custom_template_dir: Optional[Path] = None,
        extra_template_data: Optional[DefaultDict[str, Dict[str, Any]]] = None,
        target_python_version: PythonVersion = PythonVersion.PY_37,
        dump_resolve_reference_action: Optional[Callable[[Iterable[str]], str]] = None,
        validation: bool = False,
        field_constraints: bool = False,
        snake_case_field: bool = False,
        strip_default_none: bool = False,
        aliases: Optional[Mapping[str, str]] = None,
        allow_population_by_field_name: bool = False,
        apply_default_values_for_required_fields: bool = False,
        force_optional_for_required_fields: bool = False,
        class_name: Optional[str] = None,
        use_standard_collections: bool = False,
        base_path: Optional[Path] = None,
        use_schema_description: bool = False,
        reuse_model: bool = False,
        encoding: str = 'utf-8',
        enum_field_as_literal: Optional[LiteralType] = None,
        set_default_enum_member: bool = False,
        strict_nullable: bool = False,
        use_generic_container_types: bool = False,
        enable_faux_immutability: bool = False,
        remote_text_cache: Optional[DefaultPutDict[str, str]] = None,
        disable_appending_item_suffix: bool = False,
        strict_types: Optional[Sequence[StrictTypes]] = None,
        empty_enum_field_name: Optional[str] = None,
        custom_class_name_generator: Optional[
            Callable[[str], str]
        ] = title_to_class_name,
    ):
        self.data_type_manager: DataTypeManager = data_type_manager_type(
            target_python_version,
            use_standard_collections,
            use_generic_container_types,
            strict_types,
        )
        self.data_model_type: Type[DataModel] = data_model_type
        self.data_model_root_type: Type[DataModel] = data_model_root_type
        self.data_model_field_type: Type[DataModelFieldBase] = data_model_field_type
        self.imports: Imports = Imports()
        self.base_class: Optional[str] = base_class
        self.target_python_version: PythonVersion = target_python_version
        self.results: List[DataModel] = []
        self.dump_resolve_reference_action: Optional[
            Callable[[Iterable[str]], str]
        ] = dump_resolve_reference_action
        self.validation: bool = validation
        self.field_constraints: bool = field_constraints
        self.snake_case_field: bool = snake_case_field
        self.strip_default_none: bool = strip_default_none
        self.apply_default_values_for_required_fields: bool = (
            apply_default_values_for_required_fields
        )
        self.force_optional_for_required_fields: bool = (
            force_optional_for_required_fields
        )
        self.use_schema_description: bool = use_schema_description
        self.reuse_model: bool = reuse_model
        self.encoding: str = encoding
        self.enum_field_as_literal: Optional[LiteralType] = enum_field_as_literal
        self.set_default_enum_member: bool = set_default_enum_member
        self.strict_nullable: bool = strict_nullable
        self.use_generic_container_types: bool = use_generic_container_types
        self.enable_faux_immutability: bool = enable_faux_immutability
        self.custom_class_name_generator: Optional[
            Callable[[str], str]
        ] = custom_class_name_generator

        self.remote_text_cache: DefaultPutDict[str, str] = (
            remote_text_cache or DefaultPutDict()
        )
        self.current_source_path: Optional[Path] = None

        if base_path:
            self.base_path = base_path
        elif isinstance(source, Path):
            self.base_path = (
                source.absolute() if source.is_dir() else source.absolute().parent
            )
        else:
            self.base_path = Path.cwd()

        self.source: Union[str, Path, List[Path], ParseResult] = source
        self.custom_template_dir = custom_template_dir
        self.extra_template_data: DefaultDict[
            str, Any
        ] = extra_template_data or defaultdict(dict)

        if allow_population_by_field_name:
            self.extra_template_data[ALL_MODEL]['allow_population_by_field_name'] = True

        if enable_faux_immutability:
            self.extra_template_data[ALL_MODEL]['allow_mutation'] = False

        self.model_resolver = ModelResolver(
            base_url=source.geturl() if isinstance(source, ParseResult) else None,
            singular_name_suffix='' if disable_appending_item_suffix else None,
            aliases=aliases,
            empty_field_name=empty_enum_field_name,
            snake_case_field=snake_case_field,
            custom_class_name_generator=custom_class_name_generator,
            base_path=self.base_path,
        )
        self.class_name: Optional[str] = class_name

    @property
    def iter_source(self) -> Iterator[Source]:
        if isinstance(self.source, str):
            yield Source(path=Path(), text=self.source)
        elif isinstance(self.source, Path):  # pragma: no cover
            if self.source.is_dir():
                for path in self.source.rglob('*'):
                    if path.is_file():
                        yield Source.from_path(path, self.base_path, self.encoding)
            else:
                yield Source.from_path(self.source, self.base_path, self.encoding)
        elif isinstance(self.source, list):  # pragma: no cover
            for path in self.source:
                yield Source.from_path(path, self.base_path, self.encoding)
        else:
            yield Source(
                path=Path(self.source.path),
                text=self.remote_text_cache.get_or_put(
                    self.source.geturl(), default_factory=self._get_text_from_url
                ),
            )

    def _get_text_from_url(self, url: str) -> str:
        from datamodel_code_generator.http import get_body

        return self.remote_text_cache.get_or_put(url, default_factory=get_body)

    @classmethod
    def get_url_path_parts(cls, url: ParseResult) -> List[str]:
        return [
            f'{url.scheme}://{url.hostname}',
            *url.path.split('/')[1:],
        ]

    @property
    def data_type(self) -> Type[DataType]:
        return self.data_type_manager.data_type

    @abstractmethod
    def parse_raw(self) -> None:
        raise NotImplementedError

    def parse(
        self,
        with_import: Optional[bool] = True,
        format_: Optional[bool] = True,
        settings_path: Optional[Path] = None,
    ) -> Union[str, Dict[Tuple[str, ...], Result]]:

        self.parse_raw()

        if with_import:
            if self.target_python_version != PythonVersion.PY_36:
                self.imports.append(IMPORT_ANNOTATIONS)

        if format_:
            code_formatter: Optional[CodeFormatter] = CodeFormatter(
                self.target_python_version, settings_path
            )
        else:
            code_formatter = None

        _, sorted_data_models, require_update_action_models = sort_data_models(
            self.results
        )

        results: Dict[Tuple[str, ...], Result] = {}

        module_key = lambda x: x.module_path

        # process in reverse order to correctly establish module levels
        grouped_models = groupby(
            sorted(sorted_data_models.values(), key=module_key, reverse=True),
            key=module_key,
        )

        module_models: List[Tuple[Tuple[str, ...], List[DataModel]]] = []

        for module, models in (
            (k, [*v]) for k, v in grouped_models
        ):  # type: Tuple[str, ...], List[DataModel]

            for model in models:
                if isinstance(model, self.data_model_root_type):
                    root_data_type = model.fields[0].data_type

                    # backward compatible
                    # Remove duplicated root model
                    if (
                        root_data_type.reference
                        and not root_data_type.is_dict
                        and not root_data_type.is_list
                        and root_data_type.reference.source in models
                        and root_data_type.reference.name
                        == self.model_resolver.get_class_name(
                            model.reference.original_name, unique=False
                        )
                    ):
                        # Replace referenced duplicate model to original model
                        for child in model.reference.children[:]:
                            child.replace_reference(root_data_type.reference)
                        models.remove(model)
                        continue

                    #  Custom root model can't be inherited on restriction of Pydantic
                    for child in model.reference.children:
                        # inheritance model
                        if isinstance(child, DataModel):
                            for base_class in child.base_classes:
                                if base_class.reference == model.reference:
                                    child.base_classes.remove(base_class)

            module_models.append((module, models,))

            scoped_model_resolver = ModelResolver(
                exclude_names={i.alias or i.import_ for m in models for i in m.imports},
                duplicate_name_suffix='Model',
            )

            for model in models:
                class_name: str = model.class_name
                generated_name: str = scoped_model_resolver.add(
                    model.path, class_name, unique=True, class_name=True
                ).name
                if class_name != generated_name:
                    if '.' in model.reference.name:
                        model.reference.name = (
                            f"{model.reference.name.rsplit('.', 1)[0]}.{generated_name}"
                        )
                    else:
                        model.reference.name = generated_name

        for module, models in module_models:

            init = False
            if module:
                parent = (*module[:-1], '__init__.py')
                if parent not in results:
                    results[parent] = Result(body='')
                if (*module, '__init__.py') in results:
                    module = (*module, '__init__.py')
                    init = True
                else:
                    module = (*module[:-1], f'{module[-1]}.py')
            else:
                module = ('__init__.py',)

            result: List[str] = []
            imports = Imports()
            scoped_model_resolver = ModelResolver()

            for model in models:
                imports.append(model.imports)
                for data_type in model.all_data_types:
                    # To change from/import

                    if not data_type.reference or data_type.reference.source in models:
                        # No need to import non-reference model.
                        # Or, Referenced model is in the same file. we don't need to import the model
                        continue

                    if isinstance(data_type, BaseClassDataType):
                        from_ = ''.join(
                            relative(model.module_name, data_type.full_name)
                        )
                        import_ = data_type.reference.short_name
                        full_path = from_, import_
                    else:
                        from_, import_ = full_path = relative(
                            model.module_name, data_type.full_name
                        )

                    alias = scoped_model_resolver.add(full_path, import_).name

                    name = data_type.reference.short_name
                    if from_ and import_ and alias != name:
                        data_type.alias = f'{alias}.{name}'

                    if init:
                        from_ += "."
                    imports.append(Import(from_=from_, import_=import_, alias=alias))

            if self.reuse_model:
                model_cache: Dict[Tuple[str, ...], Reference] = {}
                for model in models:
                    model_key = tuple(
                        to_hashable(v)
                        for v in (
                            model.base_classes,
                            model.extra_template_data,
                            model.fields,
                        )
                    )
                    cached_model_reference = model_cache.get(model_key)
                    if cached_model_reference:
                        if isinstance(model, Enum):
                            for child in model.reference.children[:]:
                                # child is resolved data_type by reference
                                data_model = get_most_of_parent(child)

                                # TODO: replace reference in all modules
                                if data_model in models:  # pragma: no cover
                                    child.replace_reference(cached_model_reference)
                        else:
                            index = models.index(model)
                            inherited_model = model.__class__(
                                fields=[],
                                base_classes=[cached_model_reference],
                                description=model.description,
                                reference=Reference(
                                    name=model.name,
                                    path=model.reference.path + '/reuse',
                                ),
                            )
                            if (
                                cached_model_reference.path
                                in require_update_action_models
                            ):
                                require_update_action_models.append(
                                    inherited_model.path
                                )
                            models.insert(index, inherited_model)
                            models.remove(model)

                    else:
                        model_cache[model_key] = model.reference

            if self.set_default_enum_member:
                for model in models:
                    for model_field in model.fields:
                        if not model_field.default:
                            continue
                        for data_type in model_field.data_type.all_data_types:
                            if data_type.reference and isinstance(
                                data_type.reference.source, Enum
                            ):  # pragma: no cover
                                enum_member = data_type.reference.source.find_member(
                                    model_field.default
                                )
                                if enum_member:
                                    model_field.default = enum_member
            if with_import:
                result += [str(self.imports), str(imports), '\n']

            code = dump_templates(models)
            result += [code]

            if self.dump_resolve_reference_action is not None:
                result += [
                    '\n',
                    self.dump_resolve_reference_action(
                        m.reference.short_name
                        for m in models
                        if m.path in require_update_action_models
                    ),
                ]

            body = '\n'.join(result)
            if code_formatter:
                body = code_formatter.format_code(body)

            results[module] = Result(body=body, source=models[0].file_path)

        # retain existing behaviour
        if [*results] == [('__init__.py',)]:
            return results[('__init__.py',)].body

        return results
