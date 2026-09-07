"""Import each package level and exercise every declared public model."""

import ast
import importlib
import json
import sys
from pathlib import Path

output = Path(sys.argv[1])
for path in output.rglob('*.py'):
    ast.parse(path.read_text(), feature_version=tuple(map(int, sys.argv[3].split('.'))))
case = json.loads(Path(__file__).with_suffix('.json').read_text())[sys.argv[2]]
sys.path.insert(0, str(output.parent))
results = []
for suffix in case['modules']:
    module = importlib.import_module(output.name + (f'.{suffix}' if suffix else ''))
    exports = []
    for name in getattr(module, '__all__', ()):
        model = getattr(module, name)
        validated = model.model_validate(case['payload'])
        exports.append({
            'name': name,
            'origin': model.__module__.removeprefix(output.name + '.'),
            'is_definition': getattr(importlib.import_module(model.__module__), model.__name__) is model,
            'fields': list(model.model_fields),
            'dump': validated.model_dump(),
        })
        if sys.argv[2].startswith('cycle'):
            imported = {}
            exec(f'from {module.__name__} import {name}', imported)
            starred = {}
            exec(f'from {module.__name__} import *', starred)
            exports[-1]['access_identity'] = [
                vars(module)[name] is model,
                getattr(module, name) is model,
                imported[name] is model,
                starred[name] is model,
            ]
            exports[-1]['nested_identity'] = [
                getattr(importlib.import_module(type(value).__module__), type(value).__name__) is type(value)
                for value in vars(validated).values()
                if hasattr(type(value), "model_fields")
            ]
    results.append({'module': suffix, 'exports': exports})
    if sys.argv[2].startswith('cycle'):
        try:
            getattr(module, 'missing_for_export_probe')
        except AttributeError as error:
            results[-1]['unknown_attribute'] = 'missing_for_export_probe' in str(error)
print(json.dumps(results, indent=2))
