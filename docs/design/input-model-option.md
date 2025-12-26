# --input-model オプション実装プラン

## 概要

Pythonモジュール内のオブジェクト（Pydanticモデル、msgspec Struct、または dict）を直接指定してコード生成するCLIオプション。
`module.path:ObjectName` 形式（uvicorn/gunicorn/entry_pointsと同じデファクトスタンダード）。

## 使用例

```bash
# PydanticモデルからTypedDictを生成
datamodel-codegen \
    --input-model mypackage.models:UserModel \
    --output-model-type typing.TypedDict \
    --output generated/user.py

# Pydantic v2モデルからdataclassを生成
datamodel-codegen \
    --input-model mypackage.models:UserModel \
    --output-model-type dataclasses.dataclass \
    --output new_models.py

# dict (JSON Schema) からモデルを生成
datamodel-codegen \
    --input-model mypackage.schemas:USER_SCHEMA \
    --input-file-type jsonschema \
    --output user.py

# dict (OpenAPI) からモデルを生成
datamodel-codegen \
    --input-model mypackage.specs:OPENAPI_SPEC \
    --input-file-type openapi \
    --output models.py
```

## 変更が必要なファイル

### 1. src/datamodel_code_generator/arguments.py

```python
base_options.add_argument(
    "--input-model",
    help="Python import path to a Pydantic v2 model or schema dict "
         "(e.g., 'mypackage.module:ClassName' or 'mypackage.schemas:SCHEMA_DICT'). "
         "For dict input, --input-file-type is required. "
         "Cannot be used with --input or --url.",
    metavar="MODULE:NAME",
)
```

### 2. src/datamodel_code_generator/__main__.py

#### 2.1 Configクラスにフィールド追加（行444付近）

```python
input_model: Optional[str] = None  # noqa: UP045
```

#### 2.2 モデルローダー関数を追加

```python
def _load_pydantic_model_schema(input_model: str) -> dict[str, Any]:
    """Load JSON Schema from a Pydantic model import path.

    Args:
        input_model: Import path in 'module.path:ClassName' format

    Returns:
        JSON Schema dict from model.model_json_schema()

    Raises:
        Error: If format is invalid or model cannot be loaded
    """
    import importlib

    modname, sep, qualname = input_model.partition(":")
    if not sep or not qualname:
        msg = (
            f"Invalid --input-model format: {input_model!r}. "
            "Expected 'module.path:ClassName' format."
        )
        raise Error(msg)

    try:
        module = importlib.import_module(modname)
    except ImportError as e:
        msg = f"Cannot import module {modname!r}: {e}"
        raise Error(msg) from e

    try:
        model_class = getattr(module, qualname)
    except AttributeError as e:
        msg = f"Module {modname!r} has no attribute {qualname!r}"
        raise Error(msg) from e

    if not hasattr(model_class, "model_json_schema"):
        # Pydantic v1 compatibility
        if hasattr(model_class, "schema"):
            return model_class.schema()
        msg = f"{qualname!r} is not a Pydantic model (no model_json_schema method)"
        raise Error(msg)

    return model_class.model_json_schema()
```

#### 2.3 入力チェック修正（行965付近）

```python
# Before
if not config.input and not config.url and sys.stdin.isatty():

# After
if not config.input and not config.url and not config.input_model and sys.stdin.isatty():
    print(
        "Not Found Input: require `stdin` or arguments `--input`, `--url`, or `--input-model`",
        file=sys.stderr,
    )
```

#### 2.4 相互排他チェック追加（行972付近、checkの前）

```python
if config.input_model and (config.input or config.url):
    print(
        "Error: --input-model cannot be used with --input or --url",
        file=sys.stderr,
    )
    return Exit.ERROR
```

#### 2.5 入力解決修正（行1112付近）

```python
# Before
input_=config.url or config.input or sys.stdin.read(),

# After
if config.input_model:
    input_schema = _load_pydantic_model_schema(config.input_model)
    input_ = input_schema
else:
    input_ = config.url or config.input or sys.stdin.read()

# generate()呼び出し
result = generate(
    input_=input_,
    ...
)
```

#### 2.6 input_file_type の設定

`--input-model` 使用時の `input_file_type` 設定ロジック：

```python
if config.input_model:
    input_schema, is_raw_dict = _load_model_schema(config.input_model)
    input_ = input_schema

    if is_raw_dict:
        # dict の場合: --input-file-type 必須
        if not config.input_file_type:
            print(
                "Error: --input-file-type is required when --input-model points to a dict",
                file=sys.stderr,
            )
            return Exit.ERROR
        input_file_type = config.input_file_type
    else:
        # Pydantic v2 の場合: 常に JsonSchema
        # jsonschema 以外が指定されていたらエラー
        if config.input_file_type and config.input_file_type != InputFileType.JsonSchema:
            print(
                f"Error: --input-file-type must be 'jsonschema' (or omitted) "
                f"when --input-model points to a Pydantic model, "
                f"got '{config.input_file_type.value}'",
                file=sys.stderr,
            )
            return Exit.ERROR
        input_file_type = InputFileType.JsonSchema
```

| 入力型 | --input-file-type | 動作 |
|--------|------------------|------|
| Pydantic v2 | 省略 or jsonschema | OK (常にJsonSchema) |
| Pydantic v2 | その他 | **エラー** |
| dict | 指定あり | 指定値を使用 |
| dict | 指定なし | **エラー**（必須） |

### 3. テストファイル

#### tests/test_input_model.py

```python
import pytest
from pathlib import Path

from datamodel_code_generator.__main__ import main, Exit


class TestInputModel:
    """Tests for --input-model option."""

    def test_basic_usage(self, tmp_path: Path) -> None:
        """Test basic --input-model usage."""
        output_file = tmp_path / "output.py"

        exit_code = main([
            "--input-model", "pydantic:BaseModel",
            "--output", str(output_file),
        ])

        assert exit_code == Exit.OK
        assert output_file.exists()

    def test_invalid_format_no_colon(self) -> None:
        """Test error when colon is missing."""
        exit_code = main([
            "--input-model", "pydantic.BaseModel",  # Missing colon
        ])
        assert exit_code == Exit.ERROR

    def test_invalid_module(self) -> None:
        """Test error when module doesn't exist."""
        exit_code = main([
            "--input-model", "nonexistent.module:Model",
        ])
        assert exit_code == Exit.ERROR

    def test_invalid_class(self) -> None:
        """Test error when class doesn't exist in module."""
        exit_code = main([
            "--input-model", "pydantic:NonexistentClass",
        ])
        assert exit_code == Exit.ERROR

    def test_not_pydantic_model(self) -> None:
        """Test error when class is not a Pydantic model or dict."""
        exit_code = main([
            "--input-model", "pathlib:Path",
        ])
        assert exit_code == Exit.ERROR

    def test_pydantic_with_non_jsonschema_input_file_type(self) -> None:
        """Test error when Pydantic model used with non-jsonschema input-file-type."""
        exit_code = main([
            "--input-model", "pydantic:BaseModel",
            "--input-file-type", "openapi",
        ])
        assert exit_code == Exit.ERROR

    def test_mutual_exclusion_with_input(self, tmp_path: Path) -> None:
        """Test --input-model cannot be used with --input."""
        exit_code = main([
            "--input-model", "pydantic:BaseModel",
            "--input", str(tmp_path / "schema.json"),
        ])
        assert exit_code == Exit.ERROR

    def test_mutual_exclusion_with_url(self) -> None:
        """Test --input-model cannot be used with --url."""
        exit_code = main([
            "--input-model", "pydantic:BaseModel",
            "--url", "https://example.com/schema.json",
        ])
        assert exit_code == Exit.ERROR

    def test_output_to_typeddict(self, tmp_path: Path) -> None:
        """Test generating TypedDict from Pydantic model."""
        output_file = tmp_path / "output.py"

        exit_code = main([
            "--input-model", "pydantic:BaseModel",
            "--output-model-type", "typing.TypedDict",
            "--output", str(output_file),
        ])

        assert exit_code == Exit.OK
        content = output_file.read_text()
        assert "TypedDict" in content


class TestInputModelDict:
    """Tests for --input-model with dict."""

    def test_dict_with_input_file_type(self, tmp_path: Path) -> None:
        """Test dict input with --input-file-type specified."""
        # Create a test module with a schema dict
        test_module = tmp_path / "test_schemas.py"
        test_module.write_text('''
USER_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "age": {"type": "integer"}
    }
}
''')

        output_file = tmp_path / "output.py"

        import sys
        sys.path.insert(0, str(tmp_path))
        try:
            exit_code = main([
                "--input-model", "test_schemas:USER_SCHEMA",
                "--input-file-type", "jsonschema",
                "--output", str(output_file),
            ])
        finally:
            sys.path.remove(str(tmp_path))

        assert exit_code == Exit.OK
        assert output_file.exists()

    def test_dict_without_input_file_type_error(self, tmp_path: Path) -> None:
        """Test that dict without --input-file-type raises error."""
        test_module = tmp_path / "test_schemas.py"
        test_module.write_text('SCHEMA = {"type": "object"}')

        import sys
        sys.path.insert(0, str(tmp_path))
        try:
            exit_code = main([
                "--input-model", "test_schemas:SCHEMA",
                # No --input-file-type
            ])
        finally:
            sys.path.remove(str(tmp_path))

        assert exit_code == Exit.ERROR

    def test_dict_openapi(self, tmp_path: Path) -> None:
        """Test dict input as OpenAPI spec."""
        test_module = tmp_path / "test_specs.py"
        test_module.write_text('''
OPENAPI_SPEC = {
    "openapi": "3.0.0",
    "info": {"title": "Test", "version": "1.0"},
    "paths": {},
    "components": {
        "schemas": {
            "User": {
                "type": "object",
                "properties": {"name": {"type": "string"}}
            }
        }
    }
}
''')

        output_file = tmp_path / "output.py"

        import sys
        sys.path.insert(0, str(tmp_path))
        try:
            exit_code = main([
                "--input-model", "test_specs:OPENAPI_SPEC",
                "--input-file-type", "openapi",
                "--output", str(output_file),
            ])
        finally:
            sys.path.remove(str(tmp_path))

        assert exit_code == Exit.OK
        content = output_file.read_text()
        assert "User" in content
```

### 4. ドキュメント

#### docs/using_as_module.md への追記

```markdown
## Using with --input-model

The `--input-model` option allows generating code from Python objects directly:

### Pydantic Models

\`\`\`bash
# Generate TypedDict from a Pydantic model
datamodel-codegen \
    --input-model mypackage.models:UserModel \
    --output-model-type typing.TypedDict \
    --output user_typed_dict.py

# Generate dataclass from a Pydantic model
datamodel-codegen \
    --input-model mypackage.models:UserModel \
    --output-model-type dataclasses.dataclass \
    --output user_dataclass.py
\`\`\`

### Schema Dicts

You can also use dict objects containing JSON Schema or OpenAPI specs:

\`\`\`bash
# Generate from a JSON Schema dict (--input-file-type required)
datamodel-codegen \
    --input-model mypackage.schemas:USER_SCHEMA \
    --input-file-type jsonschema \
    --output user.py

# Generate from an OpenAPI dict
datamodel-codegen \
    --input-model mypackage.specs:OPENAPI_SPEC \
    --input-file-type openapi \
    --output models.py
\`\`\`

**Note:** When using dict input, `--input-file-type` is required to specify the schema format.

### Supported Types

| Type | --input-file-type |
|------|-------------------|
| Pydantic v2 BaseModel | Omit or `jsonschema` |
| dict | **Required** |

The `--input-model` option accepts a Python import path in `module.path:ObjectName` format,
the same format used by uvicorn, gunicorn, and Python entry points.
```

## 実装順序

1. [ ] arguments.py に `--input-model` オプション追加
2. [ ] Config クラスに `input_model` フィールド追加
3. [ ] `_load_pydantic_model_schema()` 関数追加
4. [ ] 入力チェック・相互排他チェック修正
5. [ ] 入力解決ロジック修正
6. [ ] テスト追加
7. [ ] ドキュメント更新

## 考慮事項

### サポート対象

| 入力型 | サポート | 判定方法 | Schema生成 | --input-file-type |
|--------|---------|---------|-----------|-------------------|
| dict | ✓ | `isinstance(obj, dict)` | そのまま | **必須** |
| Pydantic v2 | ✓ | `hasattr(..., "model_json_schema")` | `obj.model_json_schema()` | 省略 or jsonschema |
| Pydantic v1 | ✗ | - | - | - |
| msgspec | ✗ (将来) | - | - | - |

- **dict**: JSON Schema, OpenAPI, その他のスキーマをPython dictとして定義可能
- **Pydantic v2のみ**: ランタイムとの互換性を保つため、v1はサポートしない
- **msgspec**: 初期実装では非サポート。要望があれば将来追加

```python
def _load_model_schema(input_model: str) -> tuple[dict[str, Any], bool]:
    """Load schema from a Python object import path.

    Args:
        input_model: Import path in 'module.path:ObjectName' format

    Returns:
        Tuple of (schema_dict, is_raw_dict)
        - is_raw_dict=True: Input was a raw dict, respect --input-file-type
        - is_raw_dict=False: Input was Pydantic v2, always JSON Schema

    Raises:
        Error: If format is invalid or object cannot be loaded
    """
    import importlib

    modname, sep, qualname = input_model.partition(":")
    if not sep or not qualname:
        msg = (
            f"Invalid --input-model format: {input_model!r}. "
            "Expected 'module.path:ObjectName' format."
        )
        raise Error(msg)

    try:
        module = importlib.import_module(modname)
    except ImportError as e:
        msg = f"Cannot import module {modname!r}: {e}"
        raise Error(msg) from e

    try:
        obj = getattr(module, qualname)
    except AttributeError as e:
        msg = f"Module {modname!r} has no attribute {qualname!r}"
        raise Error(msg) from e

    # 1. dict - そのまま返す（--input-file-type 必須）
    if isinstance(obj, dict):
        return obj, True

    # 2. Pydantic v2
    if hasattr(obj, "model_json_schema"):
        return obj.model_json_schema(), False

    raise Error(
        f"{qualname!r} is not a supported type. "
        "Supported: dict, Pydantic v2 BaseModel"
    )
```

### ネストしたクラス

`module:OuterClass.InnerClass` 形式もサポートする？

```python
for attr in qualname.split('.'):
    obj = getattr(obj, attr)
```

→ 初期実装ではシンプルに `module:ClassName` のみサポート。

### --watch との非互換

`--input-model` はファイルを監視できないので `--watch` と併用不可。

```python
if config.watch and config.input_model:
    print("Error: --watch cannot be used with --input-model")
    return Exit.ERROR
```

## ステータス

**プランニング中** - 2025-12-25
