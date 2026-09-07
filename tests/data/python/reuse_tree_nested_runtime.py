"""Validate a directly imported root before touching any shared model API."""

import importlib
import json
import sys
from pathlib import Path

output = Path(sys.argv[1])
case = json.loads(Path(__file__).with_suffix('.json').read_text())[sys.argv[3]]
sys.path.insert(0, str(output.parent))
results = []
for index in json.loads(sys.argv[2]):
    model = getattr(importlib.import_module(f'{output.name}.schema_{index}.root{index}'), f'Root{index}')
    value = model.model_validate({f'data{index}': case} if case else {})
    nested = getattr(value, f'data{index}')
    result = {'root': index, 'fields': list(model.model_fields), 'dump': value.model_dump(by_alias=True)}
    if nested is not None:
        inner = nested.inner
        result['nested'] = [
            {
                'origin': type(item).__module__.removeprefix(output.name + '.'),
                'name': type(item).__name__,
                'identity': getattr(importlib.import_module(type(item).__module__), type(item).__name__) is type(item),
                'fields': list(type(item).model_fields),
            }
            for item in (nested, inner)
        ]
    results.append(result)
print(json.dumps(results, indent=2))
