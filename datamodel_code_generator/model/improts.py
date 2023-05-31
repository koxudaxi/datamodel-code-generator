from datamodel_code_generator.imports import Import

IMPORT_DATACLASS = Import.from_full_path('dataclasses.dataclass')
IMPORT_FIELD = Import.from_full_path('dataclasses.field')
IMPORT_TYPED_DICT = Import.from_full_path('typing.TypedDict')
IMPORT_TYPED_DICT_BACKPORT = Import.from_full_path('typing_extensions.TypedDict')
IMPORT_NOT_REQUIRED = Import.from_full_path('typing.NotRequired')
IMPORT_NOT_REQUIRED_BACKPORT = Import.from_full_path('typing_extensions.NotRequired')
