"""Import and exercise both generated split modules in a fresh process."""

import importlib
import json
import sys
from pathlib import Path

output = Path(sys.argv[1])
sys.path.insert(0, str(output.parent))
shared = importlib.import_module(f"{output.name}.shared").SharedModel
results = []
for module_name, field_name in (("schema_a.model", "data"), ("schema_b.model", "info")):
    model = importlib.import_module(f"{output.name}.{module_name}").Model
    value = model.model_validate({field_name: {"id": 7, "name": "shared"}})
    nested = getattr(value, field_name)
    results.append({
        "module": module_name,
        "fields": list(model.model_fields),
        "dump": value.model_dump(),
        "nested_fields": list(type(nested).model_fields),
        "canonical": type(nested) is shared,
        "inherits_shared": isinstance(nested, shared),
    })
print(json.dumps(results, indent=2))
