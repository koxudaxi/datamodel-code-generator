"""Import each package level and exercise every declared public model."""

import importlib
import json
import sys
from pathlib import Path

output = Path(sys.argv[1])
case = json.loads(Path(__file__).with_suffix('.json').read_text())[sys.argv[2]]
sys.path.insert(0, str(output.parent))
results = []
for suffix in case['modules']:
    module = importlib.import_module(output.name + (f'.{suffix}' if suffix else ''))
    exports = []
    for name in getattr(module, '__all__', ()):
        model = getattr(module, name)
        exports.append({
            'name': name,
            'origin': model.__module__.removeprefix(output.name + '.'),
            'is_definition': getattr(importlib.import_module(model.__module__), model.__name__) is model,
            'fields': list(model.model_fields),
            'dump': model.model_validate(case['payload']).model_dump(),
        })
    results.append({'module': suffix, 'exports': exports})
print(json.dumps(results, indent=2))
