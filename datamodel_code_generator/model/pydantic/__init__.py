from typing import List

from .base_model import BaseModel
from .custom_root_type import CustomRootType
from .dataclass import DataClass


def dump_resolve_reference_action(class_names: List[str]) -> str:
    return '\n'.join(
        f'{class_name}.update_forward_refs()' for class_name in class_names
    )
