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
    TypeVar,
    Union,
)
from urllib.parse import ParseResult

from pydantic import BaseModel

from datamodel_code_generator.format import CodeFormatter, PythonVersion
from datamodel_code_generator.imports import (
    IMPORT_ANNOTATIONS,
    IMPORT_LITERAL,
    IMPORT_LITERAL_BACKPORT,
    Import,
    Imports,
)
from datamodel_code_generator.model import pydantic as pydantic_model
from datamodel_code_generator.model import pydantic_v2 as pydantic_model_v2
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
from datamodel_code_generator.util import Protocol, runtime_checkable

SPECIAL_PATH_FORMAT: str = '#-datamodel-code-generator-#-{}-#-special-#'


def get_special_path(keyword: str, path: List[str]) -> List[str]:
    return [*path, SPECIAL_PATH_FORMAT.format(keyword)]


escape_characters = str.maketrans(
    {
        '\\': r'\\',
        "'": r'\'',
        '\b': r'\b',
        '\f': r'\f',
        '\n': r'\n',
        '\r': r'\r',
        '\t': r'\t',
    }
)


def to_hashable(item: Any) -> Any:
    if isinstance(
        item,
        (
            list,
            tuple,
        ),
    ):
        return tuple(sorted(to_hashable(i) for i in item))
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
                getattr(s.reference, 'path', None) for s in model.base_classes
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
                f'[class: {item.path} references: {item.reference_classes}]'
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


T = TypeVar('T')


def get_most_of_parent(value: Any, type_: Optional[Type[T]] = None) -> Optional[T]:
    if isinstance(value, Child) and (type_ is None or not isinstance(value, type_)):
        return get_most_of_parent(value.parent, type_)
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
    source: Optional[Path] = None


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
        additional_imports: Optional[List[str]] = None,
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
        use_operation_id_as_name: bool = False,
        use_unique_items_as_set: bool = False,
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
        use_one_literal_as_default: bool = False,
        known_third_party: Optional[List[str]] = None,
        custom_formatters: Optional[List[str]] = None,
        custom_formatters_kwargs: Optional[Dict[str, Any]] = None,
        use_pendulum: bool = False,
        http_query_parameters: Optional[Sequence[Tuple[str, str]]] = None,
    ) -> None:
        self.data_type_manager: DataTypeManager = data_type_manager_type(
            python_version=target_python_version,
            use_standard_collections=use_standard_collections,
            use_generic_container_types=use_generic_container_types,
            strict_types=strict_types,
            use_union_operator=use_union_operator,
            use_pendulum=use_pendulum,
        )
        self.data_model_type: Type[DataModel] = data_model_type
        self.data_model_root_type: Type[DataModel] = data_model_root_type
        self.data_model_field_type: Type[DataModelFieldBase] = data_model_field_type

        self.imports: Imports = Imports()
        self._append_additional_imports(additional_imports=additional_imports)

        self.base_class: Optional[str] = base_class
        self.target_python_version: PythonVersion = target_python_version
        self.results: List[DataModel] = []
        self.dump_resolve_reference_action: Optional[Callable[[Iterable[str]], str]] = (
            dump_resolve_reference_action
        )
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
        self.custom_class_name_generator: Optional[Callable[[str], str]] = (
            custom_class_name_generator
        )
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
        self.use_operation_id_as_name: bool = use_operation_id_as_name
        self.use_unique_items_as_set: bool = use_unique_items_as_set

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
        self.extra_template_data: DefaultDict[str, Any] = (
            extra_template_data or defaultdict(dict)
        )

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
        self.http_query_parameters: Optional[Sequence[Tuple[str, str]]] = (
            http_query_parameters
        )
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
        self.use_one_literal_as_default = use_one_literal_as_default
        self.known_third_party = known_third_party
        self.custom_formatter = custom_formatters
        self.custom_formatters_kwargs = custom_formatters_kwargs

    @property
    def iter_source(self) -> Iterator[Source]:
        if isinstance(self.source, str):
            yield Source(path=Path(), text=self.source)
        elif isinstance(self.source, Path):  # pragma: no cover
            if self.source.is_dir():
                for path in sorted(self.source.rglob('*'), key=lambda p: p.name):
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

    def _append_additional_imports(
        self, additional_imports: Optional[List[str]]
    ) -> None:
        if additional_imports is None:
            additional_imports = []

        for additional_import_string in additional_imports:
            new_import = Import.from_full_path(additional_import_string)
            self.imports.append(new_import)

    def _get_text_from_url(self, url: str) -> str:
        from datamodel_code_generator.http import get_body

        return self.remote_text_cache.get_or_put(
            url,
            default_factory=lambda url_: get_body(
                url, self.http_headers, self.http_ignore_tls, self.http_query_parameters
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
        model_to_duplicate_models: DefaultDict[DataModel, List[DataModel]] = (
            defaultdict(list)
        )
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
                        model.render(class_name=model.duplicate_class_name),
                        model.imports,
                    )
                )
                original_model = model_class_names[class_name]
                original_model_key = tuple(
                    to_hashable(v)
                    for v in (
                        original_model.render(
                            class_name=original_model.duplicate_class_name
                        ),
                        original_model.imports,
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
            before_import = model.imports
            imports.append(before_import)
            for data_type in model.all_data_types:
                # To change from/import

                if not data_type.reference or data_type.reference.source in models:
                    # No need to import non-reference model.
                    # Or, Referenced model is in the same file. we don't need to import the model
                    continue

                if isinstance(data_type, BaseClassDataType):
                    left, right = relative(model.module_name, data_type.full_name)
                    from_ = (
                        ''.join([left, right])
                        if left.endswith('.')
                        else '.'.join([left, right])
                    )
                    import_ = data_type.reference.short_name
                    full_path = from_, import_
                else:
                    from_, import_ = full_path = relative(
                        model.module_name, data_type.full_name
                    )
                    import_ = import_.replace('-', '_')

                alias = scoped_model_resolver.add(full_path, import_).name

                name = data_type.reference.short_name
                if from_ and import_ and alias != name:
                    data_type.alias = (
                        alias
                        if data_type.reference.short_name == import_
                        else f'{alias}.{name}'
                    )

                if init:
                    from_ = '.' + from_
                imports.append(
                    Import(
                        from_=from_,
                        import_=import_,
                        alias=alias,
                        reference_path=data_type.reference.path,
                    ),
                )
            after_import = model.imports
            if before_import != after_import:
                imports.append(after_import)

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

    def __apply_discriminator_type(
        self,
        models: List[DataModel],
        imports: Imports,
    ) -> None:
        for model in models:
            for field in model.fields:
                discriminator = field.extras.get('discriminator')
                if not discriminator or not isinstance(discriminator, dict):
                    continue
                property_name = discriminator.get('propertyName')
                if not property_name:  # pragma: no cover
                    continue
                mapping = discriminator.get('mapping', {})
                for data_type in field.data_type.data_types:
                    if not data_type.reference:  # pragma: no cover
                        continue
                    discriminator_model = data_type.reference.source
                    if not isinstance(  # pragma: no cover
                        discriminator_model,
                        (pydantic_model.BaseModel, pydantic_model_v2.BaseModel),
                    ):
                        continue  # pragma: no cover
                    type_names = []
                    if mapping:
                        for name, path in mapping.items():
                            if (
                                discriminator_model.path.split('#/')[-1]
                                != path.split('#/')[-1]
                            ):
                                if (
                                    path.startswith('#/')
                                    or discriminator_model.path[:-1]
                                    != path.split('/')[-1]
                                ):
                                    t_path = path[str(path).find('/') + 1 :]
                                    t_disc = discriminator_model.path[
                                        : str(discriminator_model.path).find('#')
                                    ].lstrip('../')
                                    t_disc_2 = '/'.join(t_disc.split('/')[1:])
                                    if t_path != t_disc and t_path != t_disc_2:
                                        continue
                            type_names.append(name)
                    else:
                        type_names = [discriminator_model.path.split('/')[-1]]
                    if not type_names:  # pragma: no cover
                        raise RuntimeError(
                            f'Discriminator type is not found. {data_type.reference.path}'
                        )
                    has_one_literal = False
                    for discriminator_field in discriminator_model.fields:
                        if (
                            discriminator_field.original_name
                            or discriminator_field.name
                        ) != property_name:
                            continue
                        literals = discriminator_field.data_type.literals
                        if (
                            len(literals) == 1 and literals[0] == type_names[0]
                            if type_names
                            else None
                        ):
                            has_one_literal = True
                            continue
                        for (
                            field_data_type
                        ) in discriminator_field.data_type.all_data_types:
                            if field_data_type.reference:  # pragma: no cover
                                field_data_type.remove_reference()
                        discriminator_field.data_type = self.data_type(
                            literals=type_names
                        )
                        discriminator_field.data_type.parent = discriminator_field
                        discriminator_field.required = True
                        imports.append(discriminator_field.imports)
                        has_one_literal = True
                    if not has_one_literal:
                        discriminator_model.fields.append(
                            self.data_model_field_type(
                                name=property_name,
                                data_type=self.data_type(literals=type_names),
                                required=True,
                            )
                        )
                    imports.append(
                        IMPORT_LITERAL
                        if self.target_python_version.has_literal_type
                        else IMPORT_LITERAL_BACKPORT
                    )

    @classmethod
    def _create_set_from_list(cls, data_type: DataType) -> Optional[DataType]:
        if data_type.is_list:
            new_data_type = data_type.copy()
            new_data_type.is_list = False
            new_data_type.is_set = True
            for data_type_ in new_data_type.data_types:
                data_type_.parent = new_data_type
            return new_data_type
        elif data_type.data_types:  # pragma: no cover
            for index, nested_data_type in enumerate(data_type.data_types[:]):
                set_data_type = cls._create_set_from_list(nested_data_type)
                if set_data_type:  # pragma: no cover
                    data_type.data_types[index] = set_data_type
            return data_type
        return None  # pragma: no cover

    def __replace_unique_list_to_set(self, models: List[DataModel]) -> None:
        for model in models:
            for model_field in model.fields:
                if not self.use_unique_items_as_set:
                    continue

                if not (
                    model_field.constraints and model_field.constraints.unique_items
                ):
                    continue
                set_data_type = self._create_set_from_list(model_field.data_type)
                if set_data_type:  # pragma: no cover
                    model_field.data_type.parent = None
                    model_field.data_type = set_data_type
                    set_data_type.parent = model_field

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
                to_hashable(v) for v in (model.render(class_name='M'), model.imports)
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
                        custom_template_dir=model._custom_template_dir,
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
        self, models: List[DataModel], unused_models: List[DataModel], imports: Imports
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
                            if d.is_dict or d.is_union
                        )
                    ):
                        continue

                    # set copied data_type
                    copied_data_type = root_type_field.data_type.copy()
                    if isinstance(data_type.parent, self.data_model_field_type):
                        # for field
                        # override empty field by root-type field
                        model_field.extras = {
                            **root_type_field.extras,
                            **model_field.extras,
                        }
                        model_field.process_const()

                        if self.field_constraints:
                            model_field.constraints = ConstraintsBase.merge_constraints(
                                root_type_field.constraints, model_field.constraints
                            )

                        data_type.parent.data_type = copied_data_type

                    elif data_type.parent.is_list:
                        if self.field_constraints:
                            model_field.constraints = ConstraintsBase.merge_constraints(
                                root_type_field.constraints, model_field.constraints
                            )
                        if isinstance(
                            root_type_field, pydantic_model.DataModelField
                        ) and not model_field.extras.get('discriminator'):  # no: pragma
                            discriminator = root_type_field.extras.get('discriminator')
                            if discriminator:  # no: pragma
                                model_field.extras['discriminator'] = discriminator
                        data_type.parent.data_types.remove(data_type)
                        data_type.parent.data_types.append(copied_data_type)

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
                    original_field = get_most_of_parent(data_type, DataModelFieldBase)
                    if original_field:  # pragma: no cover
                        # TODO: Improve detection of reference type
                        imports.append(original_field.imports)

                    data_type.remove_reference()

                    root_type_model.reference.children = [
                        c
                        for c in root_type_model.reference.children
                        if getattr(c, 'parent', None)
                    ]

                    imports.remove_referenced_imports(root_type_model.path)
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

        imported = {i for v in imports.values() for i in v}
        model_class_name_baseclasses: Dict[DataModel, Tuple[str, Set[str]]] = {}
        for model in models:
            class_name = model.class_name
            model_class_name_baseclasses[model] = (
                class_name,
                {b.type_hint for b in model.base_classes if b.reference} - {class_name},
            )

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

    def __set_one_literal_on_default(self, models: List[DataModel]) -> None:
        if not self.use_one_literal_as_default:
            return None
        for model in models:
            for model_field in model.fields:
                if not model_field.required or len(model_field.data_type.literals) != 1:
                    continue
                model_field.default = model_field.data_type.literals[0]
                model_field.required = False
                if model_field.nullable is not True:  # pragma: no cover
                    model_field.nullable = False

    def __change_imported_model_name(
        self,
        models: List[DataModel],
        imports: Imports,
        scoped_model_resolver: ModelResolver,
    ) -> None:
        imported_names = {
            imports.alias[from_][i]
            if i in imports.alias[from_] and i != imports.alias[from_][i]
            else i
            for from_, import_ in imports.items()
            for i in import_
        }
        for model in models:
            if model.class_name not in imported_names:  # pragma: no cover
                continue

            model.reference.name = scoped_model_resolver.add(  # pragma: no cover
                path=get_special_path('imported_name', model.path.split('/')),
                original_name=model.reference.name,
                unique=True,
                class_name=True,
            ).name

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
                known_third_party=self.known_third_party,
                custom_formatters=self.custom_formatter,
                custom_formatters_kwargs=self.custom_formatters_kwargs,
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
        model_to_module_models: Dict[
            DataModel, Tuple[Tuple[str, ...], List[DataModel]]
        ] = {}
        module_to_import: Dict[Tuple[str, ...], Imports] = {}

        previous_module = ()  # type: Tuple[str, ...]
        for module, models in ((k, [*v]) for k, v in grouped_models):  # type: Tuple[str, ...], List[DataModel]
            for model in models:
                model_to_module_models[model] = module, models
            self.__delete_duplicate_models(models)
            self.__replace_duplicate_name_in_module(models)
            if len(previous_module) - len(module) > 1:
                for parts in range(len(previous_module) - 1, len(module), -1):
                    module_models.append(
                        (
                            previous_module[:parts],
                            [],
                        )
                    )
            module_models.append(
                (
                    module,
                    models,
                )
            )
            previous_module = module

        class Processed(NamedTuple):
            module: Tuple[str, ...]
            models: List[DataModel]
            init: bool
            imports: Imports
            scoped_model_resolver: ModelResolver

        processed_models: List[Processed] = []

        for module, models in module_models:
            imports = module_to_import[module] = Imports()
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
                    module = tuple(part.replace('-', '_') for part in module)
            else:
                module = ('__init__.py',)

            scoped_model_resolver = ModelResolver()

            self.__override_required_field(models)
            self.__replace_unique_list_to_set(models)
            self.__change_from_import(models, imports, scoped_model_resolver, init)
            self.__extract_inherited_enum(models)
            self.__set_reference_default_value_to_field(models)
            self.__reuse_model(models, require_update_action_models)
            self.__collapse_root_models(models, unused_models, imports)
            self.__set_default_enum_member(models)
            self.__sort_models(models, imports)
            self.__set_one_literal_on_default(models)
            self.__apply_discriminator_type(models, imports)

            processed_models.append(
                Processed(module, models, init, imports, scoped_model_resolver)
            )

        for unused_model in unused_models:
            module, models = model_to_module_models[unused_model]
            if unused_model in models:  # pragma: no cover
                imports = module_to_import[module]
                imports.remove(unused_model.imports)
                models.remove(unused_model)

        for module, models, init, imports, scoped_model_resolver in processed_models:
            # process after removing unused models
            self.__change_imported_model_name(models, imports, scoped_model_resolver)

        for module, models, init, imports, scoped_model_resolver in processed_models:
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

            results[module] = Result(
                body=body, source=models[0].file_path if models else None
            )

        # retain existing behaviour
        if [*results] == [('__init__.py',)]:
            return results[('__init__.py',)].body

        return results
