"""Run a real CLI/API in a fresh process and report imported generator modules."""
from __future__ import annotations

import json
import runpy
import sys
from pathlib import Path

entrypoint, backend, input_path, output_path, record_path = sys.argv[1:]
if entrypoint == 'cli':
    sys.argv = [
        'datamodel-codegen', '--input', input_path, '--input-file-type', 'jsonschema',
        '--output-model-type', backend, '--output', output_path, '--disable-timestamp',
        '--formatters', 'builtin',
    ]
    try:
        runpy.run_module('datamodel_code_generator', run_name='__main__', alter_sys=True)
    except SystemExit as error:
        if error.code:
            raise
else:
    from datamodel_code_generator import DataModelType, Formatter, GenerateConfig, InputFileType, generate

    generate(Path(input_path), config=GenerateConfig(
        input_file_type=InputFileType.JsonSchema, output_model_type=DataModelType(backend),
        output=Path(output_path), disable_timestamp=True, formatters=[Formatter.BUILTIN],
    ))
Path(record_path).write_text(json.dumps({
    'modules': [name for name in sys.modules if name.startswith('datamodel_code_generator')],
}), encoding='utf-8')
