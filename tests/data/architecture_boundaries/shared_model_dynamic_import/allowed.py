from collections.abc import Callable

import importlib


CONCRETE_BACKEND = "datamodel_code_generator.model.pydantic_v2.base_model"

load_module = importlib.import_module


def use_shadowed_alias(load_module: Callable[[str], None]) -> None:
    load_module(CONCRETE_BACKEND)


class NeutralImporter:
    def import_module(self) -> None:
        pass


neutral_importlib = NeutralImporter()
neutral_importlib.import_module()
