"""Import and validate actual protected-namespace inheritance in a fresh process."""

import importlib.util
import json
import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
path = Path(sys.argv[1])
spec = importlib.util.spec_from_file_location('namespace_output', path)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
with warnings.catch_warnings(record=True) as caught:
    spec.loader.exec_module(module)
value = module.Root.model_validate({'child': {'first': 1, 'second': 2, 'middle': 3, 'a': 'wire', 'b': 7}})
print(json.dumps({
    'bases': [base.__name__ for base in module.Child.__bases__],
    'namespaces': module.Child.model_config['protected_namespaces'],
    'fields': list(module.Child.model_fields),
    'attribute': value.child.model_validate,
    'dump': value.model_dump(by_alias=True),
    'warnings': [str(w.message) for w in caught],
}, indent=2))
