from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from datamodel_code_generator.__main__ import Exit, main
from freezegun import freeze_time

DATA_PATH: Path = Path(__file__).parent / 'data'


@freeze_time('2019-07-26')
def test_main():
    with TemporaryDirectory() as output_dir:
        output_file: Path = Path(output_dir) / 'output.py'
        return_code: Exit = main(
            ['--input', str(DATA_PATH / 'api.yaml'), '--output', str(output_file)]
        )
        assert return_code == Exit.OK
        assert (
            output_file.read_text()
            == '''# generated by datamodel-codegen:
#   filename:  api.yaml
#   timestamp: 2019-07-26T00:00:00+00:00

from typing import List, Optional

from pydantic import BaseModel



class Pet(BaseModel):
    id: None
    name: None
    tag: Optional[None] = None


class Pets(BaseModel):
    __root__: None = None


class Error(BaseModel):
    code: None
    message: None


class api(BaseModel):
    apiKey: Optional[None] = None
    apiVersionNumber: Optional[None] = None


class apis(BaseModel):
    __root__: None = None
'''
        )

    with pytest.raises(SystemExit):
        main()
