"""Run from the B38 worktree with PYTHONPATH set to baseline or changed src."""
import ast
import hashlib
import inspect
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time
import tracemalloc

import datamodel_code_generator as dcg

source = Path(os.environ['PYTHONPATH']).resolve()
assert Path(dcg.__file__).resolve().is_relative_to(source)
root = Path(__file__).resolve().parents[1]
schema = root / 'tests/data/jsonschema/explicit_alias_names.json'
aliases = json.loads((root / 'tests/data/aliases/explicit_alias_names.json').read_text())
results = {
    'python': sys.executable,
    'source': str(source),
    'module': dcg.__file__,
    'source_sha256': {name: hashlib.sha256((source / 'datamodel_code_generator' / name).read_bytes()).hexdigest() for name in ['parser/base.py', 'parser/jsonschema.py', 'reference.py']},
    'generate_signature_sha256': hashlib.sha256(str(inspect.signature(dcg.generate)).encode()).hexdigest(),
    'timing_note': 'Concurrent campaign load; sanity only. Run each source serially under low load for comparison.',
    'cases': {},
}
for name in ['normal', 'global', 'scoped', 'choices', 'neutral_reserved']:
    backend = dcg.DataModelType.DataclassesDataclass if name == 'neutral_reserved' else dcg.DataModelType.PydanticV2BaseModel
    kwargs = dict(input_file_type=dcg.InputFileType.JsonSchema, aliases=aliases[name], output_model_type=backend,
                  snake_case_field=True, disable_timestamp=True, formatters=[dcg.Formatter.BUILTIN])
    start = time.perf_counter()
    code = dcg.generate(schema, **kwargs)
    cold = time.perf_counter() - start
    digest = hashlib.sha256(code.encode()).hexdigest()
    warm = []
    for _ in range(20):
        start = time.perf_counter()
        output = dcg.generate(schema, **kwargs)
        warm.append(time.perf_counter() - start)
        assert output == code
    tracemalloc.start()
    for _ in range(3):
        assert dcg.generate(schema, **kwargs) == code
    peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    cli = []
    for _ in range(3):
        start = time.perf_counter()
        output = subprocess.check_output([
            sys.executable, '-m', 'datamodel_code_generator', '--input', str(schema), '--input-file-type', 'jsonschema',
            '--aliases', json.dumps(aliases[name]), '--output-model-type', backend.value, '--snake-case-field',
            '--disable-timestamp', '--formatters', 'builtin',
        ], text=True)
        cli.append(time.perf_counter() - start)
        assert output == code + "\n"
    tree = ast.parse(code)
    results['cases'][name] = {
        'sha256': digest,
        'cli_sha256': hashlib.sha256(output.encode()).hexdigest(),
        'class_field_order': {node.name: [field.target.id for field in node.body if isinstance(field, ast.AnnAssign)]
                              for node in tree.body if isinstance(node, ast.ClassDef)},
        'api_cold_seconds': cold,
        'api_warm_median_seconds': statistics.median(warm),
        'cli_median_seconds': statistics.median(cli),
        'warm_peak_bytes': peak,
    }
print(json.dumps(results, indent=2))
