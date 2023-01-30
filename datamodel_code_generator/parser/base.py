import re
import sys
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
    NamedTuple,
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
    UNDEFINED,
    BaseClassDataType,
    ConstraintsBase,
    DataModel,
    DataModelFieldBase,
)
from datamodel_code_generator.model.enum import Enum, Member
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
        return tuple(
            sorted(
                (
                    k,
                    to_hashable(v),
                )
                for k, v in item.items()
            )
        )
    elif isinstance(item, set):  # pragma: no cover
        return frozenset(to_hashable(i) for i in item)
    elif isinstance(item, BaseModel):
        return to_hashable(item.dict())
    return item


def dump_templates(templates: List[DataModel]) -> str:
    return '\n\n\n'.join(str(m) for m in templates)


ReferenceMapSet = Dict[str, Set[str]]
SortedDataModels = Dict[str, DataModel]

MAX_RECURSION_COUNT: int = sys.getrecursionlimit()


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
    sorted_model_count: int = len(sorted_data_models)

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
        if sorted_model_count != len(sorted_data_models) and recursion_count:
            try:
                return sort_data_models(
                    unresolved_references,
                    sorted_data_models,
                    require_update_action_models,
                    recursion_count - 1,
                )
            except RecursionError:  # pragma: no cover
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
                    ordered_models.append(
                        (
                            max(indexes),
                            model,
                        )
                    )
                else:
                    ordered_models.append(
                        (
                            -1,
                            model,
                        )
                    )
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
            base_models = [
                getattr(s.reference, "path", None) for s in model.base_classes
            ]
            update_action_parent = set(require_update_action_models).intersection(
                base_models
            )
            if not unresolved_model:
                sorted_data_models[model.path] = model
                if update_action_parent:
                    require_update_action_models.append(model.path)
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


def _find_base_classes(model: DataModel) -> List[DataModel]:
    return [
        b.reference.source
        for b in model.base_classes
        if b.reference and isinstance(b.reference.source, DataModel)
    ]


def _find_field(
    original_name: str, models: List[DataModel]
) -> Optional[DataModelFieldBase]:
    def _find_field_and_base_classes(
        model_: DataModel,
    ) -> Tuple[Optional[DataModelFieldBase], List[DataModel]]:
        for field_ in model_.fields:
            if field_.original_name == original_name:
                return field_, []
        return None, _find_base_classes(model_)  # pragma: no cover

    for model in models:
        field, base_models = _find_field_and_base_classes(model)
        if field:
            return field
        models.extend(base_models)  # pragma: no cover

    return None  # pragma: no cover


def _copy_data_types(data_types: List[DataType]) -> List[DataType]:
    copied_data_types: List[DataType] = []
    for data_type_ in data_types:
        if data_type_.reference:
            copied_data_types.append(
                data_type_.__class__(reference=data_type_.reference)
            )
        elif data_type_.data_types:
            copied_data_type = data_type_.copy()
            copied_data_type.data_types = _copy_data_types(data_type_.data_types)
            copied_data_types.append(copied_data_type)
        else:
            copied_data_types.append(data_type_.copy())
    return copied_data_types


class Result(BaseModel):
    body: str
    source: Optional[Path]


class Source(BaseModel):
    path: Path
    text: str

    @classmethod
    def from_path(cls, path: Path, base_path: Path, encoding: str) -> 'Source':
        return cls(
            path=path.relative_to(base_path),
            text=path.read_text(encoding=encoding),
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
        allow_extra_fields: bool = False,
        force_optional_for_required_fields: bool = False,
        class_name: Optional[str] = None,
        use_standard_collections: bool = False,
        base_path: Optional[Path] = None,
        use_schema_description: bool = False,
        use_field_description: bool = False,
        use_default_kwarg: bool = False,
        reuse_model: bool = False,
        encoding: str = 'utf-8',
        enum_field_as_literal: Optional[LiteralType] = None,
        set_default_enum_member: bool = False,
        use_subclass_enum: bool = False,
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
        field_extra_keys: Optional[Set[str]] = None,
        field_include_all_keys: bool = False,
        field_extra_keys_without_x_prefix: Optional[Set[str]] = None,
        wrap_string_literal: Optional[bool] = None,
        use_title_as_name: bool = False,
        http_headers: Optional[Sequence[Tuple[str, str]]] = None,
        http_ignore_tls: bool = False,
        use_annotated: bool = False,
        use_non_positive_negative_number_constrained_types: bool = False,
        original_field_name_delimiter: Optional[str] = None,
        use_double_quotes: bool = False,
        use_union_operator: bool = False,
        allow_responses_without_content: bool = False,
        collapse_root_models: bool = False,
        special_field_name_prefix: Optional[str] = None,
        remove_special_field_name_prefix: bool = False,
        capitalise_enum_members: bool = False,
        keep_model_order: bool = False,
    ):
        self.data_type_manager: DataTypeManager = data_type_manager_type(
            python_version=target_python_version,
            use_standard_collections=use_standard_collections,
            use_generic_container_types=use_generic_container_types,
            strict_types=strict_types,
            use_union_operator=use_union_operator,
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
        self.use_field_description: bool = use_field_description
        self.use_default_kwarg: bool = use_default_kwarg
        self.reuse_model: bool = reuse_model
        self.encoding: str = encoding
        self.enum_field_as_literal: Optional[LiteralType] = enum_field_as_literal
        self.set_default_enum_member: bool = set_default_enum_member
        self.use_subclass_enum: bool = use_subclass_enum
        self.strict_nullable: bool = strict_nullable
        self.use_generic_container_types: bool = use_generic_container_types
        self.use_union_operator: bool = use_union_operator
        self.enable_faux_immutability: bool = enable_faux_immutability
        self.custom_class_name_generator: Optional[
            Callable[[str], str]
        ] = custom_class_name_generator
        self.field_extra_keys: Set[str] = field_extra_keys or set()
        self.field_extra_keys_without_x_prefix: Set[str] = (
            field_extra_keys_without_x_prefix or set()
        )
        self.field_include_all_keys: bool = field_include_all_keys

        self.remote_text_cache: DefaultPutDict[str, str] = (
            remote_text_cache or DefaultPutDict()
        )
        self.current_source_path: Optional[Path] = None
        self.use_title_as_name: bool = use_title_as_name

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

        if allow_extra_fields:
            self.extra_template_data[ALL_MODEL]['allow_extra_fields'] = True

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
            original_field_name_delimiter=original_field_name_delimiter,
            special_field_name_prefix=special_field_name_prefix,
            remove_special_field_name_prefix=remove_special_field_name_prefix,
            capitalise_enum_members=capitalise_enum_members,
        )
        self.class_name: Optional[str] = class_name
        self.wrap_string_literal: Optional[bool] = wrap_string_literal
        self.http_headers: Optional[Sequence[Tuple[str, str]]] = http_headers
        self.http_ignore_tls: bool = http_ignore_tls
        self.use_annotated: bool = use_annotated
        if self.use_annotated and not self.field_constraints:  # pragma: no cover
            raise Exception(
                '`use_annotated=True` has to be used with `field_constraints=True`'
            )
        self.use_non_positive_negative_number_constrained_types = (
            use_non_positive_negative_number_constrained_types
        )
        self.use_double_quotes = use_double_quotes
        self.allow_responses_without_content = allow_responses_without_content
        self.collapse_root_models = collapse_root_models
        self.capitalise_enum_members = capitalise_enum_members
        self.keep_model_order = keep_model_order

    @property
    def iter_source(self) -> Iterator[Source]:
        if isinstance(self.source, str):
            yield Source(path=Path(), text=self.source)
        elif isinstance(self.source, Path):  # pragma: no cover
            if self.source.is_dir():
                paths = (
                    sorted(self.source.rglob('*'))
                    if self.keep_model_order
                    else self.source.rglob('*')
                )
                for path in paths:
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

        return self.remote_text_cache.get_or_put(
            url,
            default_factory=lambda url_: get_body(
                url, self.http_headers, self.http_ignore_tls
            ),
        )

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

    def __delete_duplicate_models(self, models: List[DataModel]) -> None:
        model_class_names: Dict[str, DataModel] = {}
        model_to_duplicate_models: DefaultDict[
            DataModel, List[DataModel]
        ] = defaultdict(list)
        for model in models[:]:
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
                    ).name
                ):
                    # Replace referenced duplicate model to original model
                    for child in model.reference.children[:]:
                        child.replace_reference(root_data_type.reference)
                    models.remove(model)
                    for data_type in model.all_data_types:
                        if data_type.reference:
                            data_type.remove_reference()
                    continue

                #  Custom root model can't be inherited on restriction of Pydantic
                for child in model.reference.children:
                    # inheritance model
                    if isinstance(child, DataModel):
                        for base_class in child.base_classes[:]:
                            if base_class.reference == model.reference:
                                child.base_classes.remove(base_class)
                        if not child.base_classes:  # pragma: no cover
                            child.set_base_class()

            class_name = model.duplicate_class_name or model.class_name
            if class_name in model_class_names:
                model_key = tuple(
                    to_hashable(v)
                    for v in (
                        model.base_classes,
                        model.extra_template_data,
                        model.fields,
                        model.description,
                        model.default,
                        model.decorators,
                    )
                )
                original_model = model_class_names[class_name]
                original_model_key = tuple(
                    to_hashable(v)
                    for v in (
                        original_model.base_classes,
                        original_model.extra_template_data,
                        original_model.fields,
                        original_model.description,
                        original_model.default,
                        original_model.decorators,
                    )
                )
                if model_key == original_model_key:
                    model_to_duplicate_models[original_model].append(model)
                    continue
            model_class_names[class_name] = model
        for model, duplicate_models in model_to_duplicate_models.items():
            for duplicate_model in duplicate_models:
                for child in duplicate_model.reference.children[:]:
                    child.replace_reference(model.reference)
                models.remove(duplicate_model)

    @classmethod
    def __replace_duplicate_name_in_module(cls, models: List[DataModel]) -> None:
        scoped_model_resolver = ModelResolver(
            exclude_names={i.alias or i.import_ for m in models for i in m.imports},
            duplicate_name_suffix='Model',
        )

        model_names: Dict[str, DataModel] = {}
        for model in models:
            class_name: str = model.class_name
            generated_name: str = scoped_model_resolver.add(
                model.path, class_name, unique=True, class_name=True
            ).name
            if class_name != generated_name:
                model.class_name = generated_name
            model_names[model.class_name] = model

        for model in models:
            duplicate_name = model.duplicate_class_name
            # check only first desired name
            if duplicate_name and duplicate_name not in model_names:
                del model_names[model.class_name]
                model.class_name = duplicate_name
                model_names[duplicate_name] = model

    @classmethod
    def __change_from_import(
        cls,
        models: List[DataModel],
        imports: Imports,
        scoped_model_resolver: ModelResolver,
        init: bool,
    ) -> None:
        for model in models:
            scoped_model_resolver.add(model.path, model.class_name)
        for model in models:
            imports.append(model.imports)
            for data_type in model.all_data_types:
                # To change from/import

                if not data_type.reference or data_type.reference.source in models:
                    # No need to import non-reference model.
                    # Or, Referenced model is in the same file. we don't need to import the model
                    continue

                if isinstance(data_type, BaseClassDataType):
                    from_ = ''.join(relative(model.module_name, data_type.full_name))
                    import_ = data_type.reference.short_name
                    full_path = from_, import_
                else:
                    from_, import_ = full_path = relative(
                        model.module_name, data_type.full_name
                    )

                alias = scoped_model_resolver.add(full_path, import_).name

                name = data_type.reference.short_name
                if from_ and import_ and alias != name:
                    data_type.alias = (
                        alias
                        if from_ == '.' and data_type.full_name == import_
                        else f'{alias}.{name}'
                    )

                if init:
                    from_ = "." + from_
                imports.append(Import(from_=from_, import_=import_, alias=alias))

    @classmethod
    def __extract_inherited_enum(cls, models: List[DataModel]) -> None:
        for model in models[:]:
            if model.fields:
                continue
            enums: List[Enum] = []
            for base_model in model.base_classes:
                if not base_model.reference:
                    continue
                source_model = base_model.reference.source
                if isinstance(source_model, Enum):
                    enums.append(source_model)
            if enums:
                models.insert(
                    models.index(model),
                    enums[0].__class__(
                        fields=[f for e in enums for f in e.fields],
                        description=model.description,
                        reference=model.reference,
                    ),
                )
                models.remove(model)

    @classmethod
    def __set_reference_default_value_to_field(cls, models: List[DataModel]) -> None:
        for model in models:
            for model_field in model.fields:
                if not model_field.data_type.reference or model_field.has_default:
                    continue
                if isinstance(
                    model_field.data_type.reference.source, DataModel
                ):  # pragma: no cover
                    if model_field.data_type.reference.source.default != UNDEFINED:
                        model_field.default = (
                            model_field.data_type.reference.source.default
                        )

    def __reuse_model(
        self, models: List[DataModel], require_update_action_models: List[str]
    ) -> None:
        if not self.reuse_model:
            return None
        model_cache: Dict[Tuple[str, ...], Reference] = {}
        duplicates = []
        for model in models[:]:
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
                    duplicates.append(model)
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
                    if cached_model_reference.path in require_update_action_models:
                        require_update_action_models.append(inherited_model.path)
                    models.insert(index, inherited_model)
                    models.remove(model)

            else:
                model_cache[model_key] = model.reference

        for duplicate in duplicates:
            models.remove(duplicate)

    def __collapse_root_models(
        self, models: List[DataModel], unused_models: List[DataModel]
    ) -> None:
        if not self.collapse_root_models:
            return None
        for model in models:
            for model_field in model.fields:
                for data_type in model_field.data_type.all_data_types:
                    reference = data_type.reference
                    if not reference or not isinstance(
                        reference.source, self.data_model_root_type
                    ):
                        continue

                    # Use root-type as model_field type
                    root_type_model = reference.source
                    root_type_field = root_type_model.fields[0]

                    if (
                        self.field_constraints
                        and isinstance(root_type_field.constraints, ConstraintsBase)
                        and root_type_field.constraints.has_constraints
                        and any(
                            d
                            for d in model_field.data_type.all_data_types
                            if d.is_dict or d.is_list or d.is_union
                        )
                    ):
                        continue

                    # set copied data_type
                    copied_data_type = root_type_field.data_type.copy()
                    if isinstance(data_type.parent, self.data_model_field_type):

                        # for field
                        # override empty field by root-type field
                        model_field.extras = dict(
                            root_type_field.extras, **model_field.extras
                        )
                        if self.field_constraints:
                            if isinstance(
                                root_type_field.constraints, ConstraintsBase
                            ):  # pragma: no cover
                                model_field.constraints = root_type_field.constraints.copy(
                                    update={
                                        k: v
                                        for k, v in model_field.constraints.dict().items()
                                        if v is not None
                                    }
                                    if isinstance(
                                        model_field.constraints, ConstraintsBase
                                    )
                                    else {}
                                )
                        else:
                            pass
                            # skip function type-hint kwargs overriding

                        data_type.parent.data_type = copied_data_type
                    elif isinstance(data_type.parent, DataType):
                        # for data_type
                        data_type_id = id(data_type)
                        data_type.parent.data_types = [
                            d
                            for d in (*data_type.parent.data_types, copied_data_type)
                            if id(d) != data_type_id
                        ]
                    else:  # pragma: no cover
                        continue

                    data_type.remove_reference()

                    root_type_model.reference.children = [
                        c for c in root_type_model.reference.children if c.parent
                    ]

                    if not root_type_model.reference.children:
                        unused_models.append(root_type_model)

    def __set_default_enum_member(
        self,
        models: List[DataModel],
    ) -> None:
        if not self.set_default_enum_member:
            return None
        for model in models:
            for model_field in model.fields:
                if not model_field.default:
                    continue
                for data_type in model_field.data_type.all_data_types:
                    if data_type.reference and isinstance(
                        data_type.reference.source, Enum
                    ):  # pragma: no cover
                        if isinstance(model_field.default, list):
                            enum_member: Union[List[Member], Optional[Member]] = [
                                e
                                for e in (
                                    data_type.reference.source.find_member(d)
                                    for d in model_field.default
                                )
                                if e
                            ]
                        else:
                            enum_member = data_type.reference.source.find_member(
                                model_field.default
                            )
                        if not enum_member:
                            continue
                        model_field.default = enum_member
                        if data_type.alias:
                            if isinstance(enum_member, list):
                                for enum_member_ in enum_member:
                                    enum_member_.alias = data_type.alias
                            else:
                                enum_member.alias = data_type.alias

    def __override_required_field(
        self,
        models: List[DataModel],
    ) -> None:
        for model in models:
            if isinstance(model, (Enum, self.data_model_root_type)):
                continue
            for index, model_field in enumerate(model.fields[:]):
                data_type = model_field.data_type
                if (
                    not model_field.original_name
                    or data_type.data_types
                    or data_type.reference
                    or data_type.type
                    or data_type.literals
                    or data_type.dict_key
                ):
                    continue

                original_field = _find_field(
                    model_field.original_name, _find_base_classes(model)
                )
                if not original_field:  # pragma: no cover
                    model.fields.remove(model_field)
                    continue
                copied_original_field = original_field.copy()
                if original_field.data_type.reference:
                    data_type = self.data_type_manager.data_type(
                        reference=original_field.data_type.reference,
                    )
                elif original_field.data_type.data_types:
                    data_type = original_field.data_type.copy()
                    data_type.data_types = _copy_data_types(
                        original_field.data_type.data_types
                    )
                    for data_type_ in data_type.data_types:
                        data_type_.parent = data_type
                else:
                    data_type = original_field.data_type.copy()
                data_type.parent = copied_original_field
                copied_original_field.data_type = data_type
                copied_original_field.parent = model
                copied_original_field.required = True
                model.fields.insert(index, copied_original_field)
                model.fields.remove(model_field)

    def __sort_models(
        self,
        models: List[DataModel],
        imports: Imports,
    ) -> None:
        if not self.keep_model_order:
            return

        models.sort(key=lambda x: x.class_name)

        imported = set(i for v in imports.values() for i in v)
        model_class_name_baseclasses: Dict[DataModel, Tuple[str, Set[str]]] = {}
        for model in models:
            class_name = model.class_name
            model_class_name_baseclasses[model] = class_name, {
                b.type_hint for b in model.base_classes if b.reference
            } - {class_name}

        changed: bool = True
        while changed:
            changed = False
            resolved = imported.copy()
            for i in range(len(models) - 1):
                model = models[i]
                class_name, baseclasses = model_class_name_baseclasses[model]
                if not baseclasses - resolved:
                    resolved.add(class_name)
                    continue
                models[i], models[i + 1] = models[i + 1], model
                changed = True

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
                self.target_python_version,
                settings_path,
                self.wrap_string_literal,
                skip_string_normalization=not self.use_double_quotes,
            )
        else:
            code_formatter = None

        _, sorted_data_models, require_update_action_models = sort_data_models(
            self.results
        )

        results: Dict[Tuple[str, ...], Result] = {}

        def module_key(data_model: DataModel) -> Tuple[str, ...]:
            return tuple(data_model.module_path)

        # process in reverse order to correctly establish module levels
        grouped_models = groupby(
            sorted(sorted_data_models.values(), key=module_key, reverse=True),
            key=module_key,
        )

        module_models: List[Tuple[Tuple[str, ...], List[DataModel]]] = []
        unused_models: List[DataModel] = []
        model_to_models: Dict[DataModel, List[DataModel]] = {}

        for module, models in (
            (k, [*v]) for k, v in grouped_models
        ):  # type: Tuple[str, ...], List[DataModel]
            for model in models:
                model_to_models[model] = models
            self.__delete_duplicate_models(models)
            self.__replace_duplicate_name_in_module(models)
            module_models.append(
                (
                    module,
                    models,
                )
            )

        class Processed(NamedTuple):
            module: Tuple[str, ...]
            models: List[DataModel]
            init: bool
            imports: Imports

        processed_models: List[Processed] = []
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

            imports = Imports()
            scoped_model_resolver = ModelResolver()

            self.__change_from_import(models, imports, scoped_model_resolver, init)
            self.__extract_inherited_enum(models)
            self.__set_reference_default_value_to_field(models)
            self.__reuse_model(models, require_update_action_models)
            self.__collapse_root_models(models, unused_models)
            self.__set_default_enum_member(models)
            self.__override_required_field(models)
            self.__sort_models(models, imports)

            processed_models.append(Processed(module, models, init, imports))

        for unused_model in unused_models:
            if unused_model in model_to_models[unused_model]:  # pragma: no cover
                model_to_models[unused_model].remove(unused_model)

        for module, models, init, imports in processed_models:
            result: List[str] = []
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
