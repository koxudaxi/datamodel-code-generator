"""Import generated models in a fresh process and observe native identity/validation."""
import importlib
import importlib.util
import json
import sys
from pathlib import Path
from pydantic import TypeAdapter, ValidationError
from typing import get_args, get_origin, get_type_hints
sys.path.insert(0, str(Path(__file__).parents[4]))
record = json.loads(sys.argv[2])
spec = importlib.util.spec_from_file_location('generic_output', sys.argv[1])
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
rows = []
for source, payload, invalid in zip(record['sources'], record['payloads'], record['invalid'], strict=True):
    module_name, name = source.split(':')
    native = getattr(importlib.import_module('tests.data.python.input_model.' + module_name), name)
    generated = getattr(module, name)
    native_fields = getattr(native, 'model_fields', None)
    native_annotations = {field: info.annotation for field, info in native_fields.items()} if native_fields is not None else get_type_hints(native)
    row = {'name': name, 'fields': list(generated.model_fields), 'annotations_equal': {
        field: generated.model_fields[field].annotation == annotation
        for field, annotation in native_annotations.items()
    }, 'type_identity': {field: generated.model_fields[field].annotation is annotation
        for field, annotation in native_annotations.items() if get_origin(annotation) is None and isinstance(annotation, type)}, 'results': {}}
    leaf_ids = {}
    for label, annotations in [('native', native_annotations), ('generated', {field: info.annotation for field, info in generated.model_fields.items()})]:
        leaf_ids[label] = {}
        for field, annotation in annotations.items():
            pending = [annotation]
            leaves = []
            while pending:
                item = pending.pop()
                if get_origin(item) is None and isinstance(item, type):
                    leaves.append(id(item))
                else:
                    pending.extend(get_args(item))
            leaf_ids[label][field] = leaves
    row['type_leaf_identity'] = {field: leaves == leaf_ids['generated'][field] for field, leaves in leaf_ids['native'].items()}
    for label, model in [('native', native), ('generated', generated)]:
        adapter = TypeAdapter(model)
        try:
            row['results'][label] = {'valid': adapter.dump_python(adapter.validate_python(payload), mode='json')}
        except ValidationError as error:
            row['results'][label] = {'valid_error': [(list(item['loc']), item['type']) for item in error.errors()]}
        try:
            adapter.validate_python(invalid)
        except ValidationError as error:
            row['results'][label]['invalid'] = [(list(item['loc']), item['type']) for item in error.errors()]
        else:
            row['results'][label]['invalid'] = None
    rows.append(row)
print(json.dumps(rows, indent=2))
