from pathlib import Path

from datamodel_code_generator import is_schema

DATA_PATH: Path = Path(__file__).parent / 'data'


def test_is_schema():
    def assert_is_schema(file: Path, should_be_schema: bool) -> None:
        __tracebackhide__ = True
        if file.is_dir():
            return
        if file.suffix not in ('.yaml', '.json'):
            return
        result = is_schema(file.read_text())
        assert result == should_be_schema, f'{file} was the wrong type!'

    for file in (DATA_PATH / 'json').rglob('*'):
        if str(file).endswith('broken.json'):
            continue
        assert_is_schema(file, False)
    for file in (DATA_PATH / 'jsonschema').rglob('*'):
        if str(file).endswith(('external_child.json', 'external_child.yaml')):
            continue
        if 'reference_same_hierarchy_directory' in str(file):
            continue
        assert_is_schema(file, True)
