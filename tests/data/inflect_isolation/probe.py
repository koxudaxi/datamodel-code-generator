"""Fresh-process generation and independent inflect consumer probe."""
from __future__ import annotations

import importlib
import json
import os
from pathlib import Path
import sys
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from datamodel_code_generator import DataModelType, Formatter, InputFileType, PythonVersion, generate
from datamodel_code_generator.__main__ import main

scenario, entrypoint, backend, output = sys.argv[1:]
output = Path(output)
data = Path(__file__).parent
formatters = ['builtin'] if os.environ.get('DATAMODEL_CODE_GENERATOR_TEST_DEFAULT_FORMATTER') == 'builtin' else ['black', 'isort']
options = dict(input_file_type=InputFileType.JsonSchema, output_model_type=DataModelType(backend), target_python_version=PythonVersion.PY_310, disable_timestamp=True, formatters=[Formatter(value) for value in formatters])
if scenario.startswith('failure_'):
    from copy import copy
    from types import SimpleNamespace
    from unittest.mock import patch

    original_find_spec = importlib.util.find_spec
    original_spec = original_find_spec('inflect')

    def unavailable_code(name):
        raise AttributeError('simulated loader incompatibility')

    def failure_spec(name, *args, **kwargs):
        if name != 'inflect':
            return original_find_spec(name, *args, **kwargs)
        if scenario == 'failure_missing_spec':
            return None
        spec = copy(original_spec)
        if scenario == 'failure_missing_get_code':
            spec.loader = object()
        elif scenario == 'failure_no_code':
            spec.loader = SimpleNamespace(get_code=lambda name: None)
        elif scenario == 'failure_code_error':
            spec.loader = SimpleNamespace(get_code=unavailable_code)
        elif scenario == 'failure_future_api':
            spec.loader = SimpleNamespace(get_code=lambda name: compile((data / 'future_api.py').read_text(), str(data / 'future_api.py'), 'exec'))
        return spec

    patcher = patch('importlib.util.find_spec', side_effect=failure_spec)
    patcher.start()

public_before = None
typeguard_before = None
if scenario == 'inflect_first':
    public_before = importlib.import_module('inflect')
    typeguard_before = sys.modules['typeguard']
elif scenario == 'typeguard_first':
    typeguard_before = importlib.import_module('typeguard')


def generate_once():
    if entrypoint == 'cli':
        return main(['--input', str(data / 'catalog.json'), '--input-file-type', 'jsonschema', '--output-model-type', backend, '--output', str(output), '--target-python-version', '3.10', '--disable-timestamp', '--formatters', *formatters])
    generate(data / 'catalog.json', output=output, **options)
    return 0


codes = []
if scenario in {'concurrent', 'parallel_generation'}:
    # Warm only parser/model imports; this schema does not need inflection.
    generate({'title': 'Empty', 'type': 'object'}, **{**options, 'formatters': []})
    barrier = Barrier(4)

    def parallel_generate(index):
        barrier.wait()
        if scenario == 'concurrent' and index == 0:
            module = importlib.import_module('inflect')
            try:
                module.engine().number_to_words(None)
            except Exception as error:
                return type(error).__name__
            return 'accepted invalid input'
        return generate(data / 'catalog.json', **{**options, 'formatters': []})

    with ThreadPoolExecutor(max_workers=4) as executor:
        concurrent_results = list(executor.map(parallel_generate, range(4)))
    concurrent_safe = (concurrent_results[0] == 'TypeCheckError' and len(set(concurrent_results[1:])) == 1) if scenario == 'concurrent' else len(set(concurrent_results)) == 1
else:
    concurrent_safe = True

exit_codes = []
for _ in range(3):
    exit_codes.append(generate_once())
    codes.append(output.read_text())
loaded_after_generation = {'inflect': 'inflect' in sys.modules, 'typeguard': 'typeguard' in sys.modules}
public = importlib.import_module('inflect')
engine = public.engine()
results = []
for method, value in json.loads((data / 'probes.json').read_text()):
    try:
        result = {'value': getattr(engine, method)(value)}
    except Exception as error:
        result = {'error': type(error).__name__}
    results.append(result)
public_identity = public_before is None or public is public_before
typeguard_identity = typeguard_before is None or sys.modules['typeguard'] is typeguard_before
# Generate again after an independent caller imported the public modules.
exit_codes.append(generate_once())
codes.append(output.read_text())
print(json.dumps({'results': results, 'exit_codes': exit_codes, 'same_code': len(set(codes)) == 1, 'public_identity': public_identity, 'typeguard_identity': typeguard_identity, 'concurrent_safe': concurrent_safe, 'loaded_after_generation': loaded_after_generation, 'failed_private_import_cleaned': not scenario.startswith('failure_') or not any(name.startswith('datamodel_code_generator._inflect') for name in sys.modules)}, indent=2))
