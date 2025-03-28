from __future__ import annotations

from datamodel_code_generator.imports import Import

IMPORT_CONSTR = Import.from_full_path("pydantic.constr")
IMPORT_CONINT = Import.from_full_path("pydantic.conint")
IMPORT_CONFLOAT = Import.from_full_path("pydantic.confloat")
IMPORT_CONDECIMAL = Import.from_full_path("pydantic.condecimal")
IMPORT_CONBYTES = Import.from_full_path("pydantic.conbytes")
IMPORT_POSITIVE_INT = Import.from_full_path("pydantic.PositiveInt")
IMPORT_NEGATIVE_INT = Import.from_full_path("pydantic.NegativeInt")
IMPORT_NON_POSITIVE_INT = Import.from_full_path("pydantic.NonPositiveInt")
IMPORT_NON_NEGATIVE_INT = Import.from_full_path("pydantic.NonNegativeInt")
IMPORT_POSITIVE_FLOAT = Import.from_full_path("pydantic.PositiveFloat")
IMPORT_NEGATIVE_FLOAT = Import.from_full_path("pydantic.NegativeFloat")
IMPORT_NON_NEGATIVE_FLOAT = Import.from_full_path("pydantic.NonNegativeFloat")
IMPORT_NON_POSITIVE_FLOAT = Import.from_full_path("pydantic.NonPositiveFloat")
IMPORT_SECRET_STR = Import.from_full_path("pydantic.SecretStr")
IMPORT_EMAIL_STR = Import.from_full_path("pydantic.EmailStr")
IMPORT_UUID1 = Import.from_full_path("pydantic.UUID1")
IMPORT_UUID2 = Import.from_full_path("pydantic.UUID2")
IMPORT_UUID3 = Import.from_full_path("pydantic.UUID3")
IMPORT_UUID4 = Import.from_full_path("pydantic.UUID4")
IMPORT_UUID5 = Import.from_full_path("pydantic.UUID5")
IMPORT_ANYURL = Import.from_full_path("pydantic.AnyUrl")
IMPORT_IPV4ADDRESS = Import.from_full_path("ipaddress.IPv4Address")
IMPORT_IPV6ADDRESS = Import.from_full_path("ipaddress.IPv6Address")
IMPORT_IPV4NETWORKS = Import.from_full_path("ipaddress.IPv4Network")
IMPORT_IPV6NETWORKS = Import.from_full_path("ipaddress.IPv6Network")
IMPORT_EXTRA = Import.from_full_path("pydantic.Extra")
IMPORT_FIELD = Import.from_full_path("pydantic.Field")
IMPORT_STRICT_INT = Import.from_full_path("pydantic.StrictInt")
IMPORT_STRICT_FLOAT = Import.from_full_path("pydantic.StrictFloat")
IMPORT_STRICT_STR = Import.from_full_path("pydantic.StrictStr")
IMPORT_STRICT_BOOL = Import.from_full_path("pydantic.StrictBool")
IMPORT_STRICT_BYTES = Import.from_full_path("pydantic.StrictBytes")
IMPORT_DATACLASS = Import.from_full_path("pydantic.dataclasses.dataclass")
