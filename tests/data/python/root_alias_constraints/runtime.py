"""Compare generated root acceptance with the original JSON Schema in a fresh process."""
import importlib.util
import json
import sys
from pathlib import Path

from jsonschema import Draft7Validator
from pydantic import ValidationError

schema_path = Path(sys.argv[1])
output_path = Path(sys.argv[2])
spec = importlib.util.spec_from_file_location("generated_root_constraints", output_path)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
validator = Draft7Validator(json.loads(schema_path.read_text()))
payloads = json.loads(Path(__file__).with_name("cases.json").read_text())[schema_path.stem]
results = []
for payload in payloads:
    try:
        module.Root.model_validate(payload)
        accepted = True
    except ValidationError:
        accepted = False
    results.append({"payload": payload, "native": validator.is_valid(payload), "generated": accepted})
print(json.dumps(results, indent=2))
