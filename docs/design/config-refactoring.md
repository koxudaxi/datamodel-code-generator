# Config Refactoring Design Document

## 概要

`datamodel-code-generator` の設定管理を改善し、モジュールとしての使いやすさを向上させる設計提案。

## 現状の問題点

### 1. 重複した定義（3箇所）

```
┌─────────────────────────────────────────────────────────────┐
│  generate()         │  arguments.py      │  Parser.__init__ │
│  117 params         │  132 CLI args      │  107 params      │
│  (型, デフォルト値)    │  (help, choices)   │  (型, デフォルト値) │
└─────────────────────────────────────────────────────────────┘
         ↑                    ↑                    ↑
         └────────── 全て手動で同期が必要 ──────────┘
```

### 2. モジュールAPIの使いにくさ

```python
# 現状: 117個のフラットなパラメータ
result = generate(
    input_=schema,
    output_model_type=DataModelType.PydanticV2BaseModel,
    snake_case_field=True,
    use_schema_description=True,
    use_field_description=True,
    # ... 100個以上続く
)
```

- パラメータが多すぎてIDE補完が使いにくい
- typoがあっても実行時まで気づかない
- ドキュメントが不十分

## 提案: Single Source of Truth アーキテクチャ

### Pydanticモデルをソースとする

```
┌─────────────────────────────────────────────────────────────┐
│              GeneratorConfig (Pydantic Model)               │
│  ─────────────────────────────────────────────────────────  │
│  snake_case_field: bool = Field(                            │
│      default=False,                                         │
│      description="Convert field names to snake_case",       │
│      json_schema_extra={"cli_name": "--snake-case-field"}   │
│  )                                                          │
└─────────────────────────────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
   ┌─────────┐      ┌───────────┐      ┌───────────┐
   │generate()│     │ CLI Parser│      │  Parser   │
   └─────────┘      └───────────┘      └───────────┘
        │                  │                  │
        ▼                  ▼                  ▼
   ┌─────────┐      ┌───────────┐      ┌───────────┐
   │ API Docs│      │ --help    │      │ Validation│
   │ 自動生成 │      │ 自動生成  │      │  自動     │
   └─────────┘      └───────────┘      └───────────┘
```

### JSON Schema vs Pydantic

| 観点 | JSON Schema | Pydantic |
|------|-------------|----------|
| 可読性 | △ | ◎ |
| IDE補完 | × | ◎ |
| 型チェック | × | ◎ |
| バリデーション | × | ◎ |
| Python開発者 | △ | ◎ |
| ドキュメント生成 | ◎ | ◎ (model_json_schema) |

**結論**: Pydanticモデルをソースとし、必要に応じてJSON Schemaを生成する。

## パラメータ分析結果

### レイヤー間の分布

```
┌─────────────────────────────────────────────────────────────────┐
│                        パラメータ分布                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│                    ┌─────────────────┐                          │
│                    │   全レイヤー共通  │                          │
│                    │      91個       │                          │
│                    └─────────────────┘                          │
│                                                                 │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────┐          │
│  │ generate │    │   generate   │    │    Parser    │          │
│  │   only   │    │   + CLI      │    │     only     │          │
│  │   4個    │    │    19個      │    │     13個     │          │
│  └──────────┘    └──────────────┘    └──────────────┘          │
│                                                                 │
│                    ┌──────────────┐                             │
│                    │   CLI only   │                             │
│                    │     22個     │                             │
│                    └──────────────┘                             │
└─────────────────────────────────────────────────────────────────┘
```

### カテゴリ別分類

| カテゴリ | 数 | 説明 | 例 |
|---------|-----|------|-----|
| **全レイヤー共通** | 91 | コア設定 | `snake_case_field`, `reuse_model` |
| **generate + CLI** | 19 | 高レベル設定 | `output_model_type`, `input_file_type` |
| **CLI only** | 22 | UI/ユーティリティ | `--help`, `--watch`, `--check` |
| **Parser only** | 13 | 内部実装 | `data_model_type`, `remote_text_cache` |
| **generate only** | 4 | generate専用 | `settings_path`, `command_line` |

### Parser Only パラメータ（内部実装用）

```python
data_model_type: type[DataModel]           # get_data_model_types()から取得
data_model_root_type: type[DataModel]      # get_data_model_types()から取得
data_model_field_type: type[DataModelFieldBase]
data_type_manager_type: type[DataTypeManager]
dump_resolve_reference_action: Callable    # get_data_model_types()から取得
known_third_party: list[str]               # get_data_model_types()から取得
remote_text_cache: DefaultPutDict          # generate()内で作成
base_path: Path | None                     # input_から計算
defer_formatting: bool                     # outputから計算
```

### CLI Only パラメータ（UI/ユーティリティ）

```
--help, --version                    # 情報表示
--debug, --profile, --no-color       # デバッグ
--check                              # 検証モード
--watch, --watch-delay               # ファイル監視
--input, --url                       # 入力指定（generate()ではinput_引数）
--no-use-union-operator              # 反転フラグ（CLIでの使いやすさ）
```

## Config モデル設計

### 最終設計: Unpack[TypedDict] + ドッグフーディング

既存ユーザーのメンテナンス負荷をゼロにするため、`Unpack[TypedDict]`を採用。
TypedDictはdatamodel-code-generator自身で生成（ドッグフーディング）。

### アーキテクチャ

```
┌─────────────────────────────────────────────────────────────┐
│  config.py: GeneratorConfig (Pydantic)                       │
│  - Single Source of Truth                                   │
│  - バリデーションロジック                                      │
└──────────────────────────┬──────────────────────────────────┘
                           │ ビルド時
                           │ model_json_schema() → JSON Schema
                           │ datamodel-codegen --output-model-type typing.TypedDict
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  _generated/config_extras.py: GeneratorExtras (TypedDict)   │
│  - 自動生成（ドッグフーディング）                              │
│  - IDE補完用                                                 │
│  - NotRequired[T] で全フィールドオプショナル                    │
└─────────────────────────────────────────────────────────────┘
```

### クラス階層

```python
# src/datamodel_code_generator/config.py
class GeneratorConfig(BaseModel):
    """generate()用設定（110個）"""
    model_config = ConfigDict(extra="forbid")

    snake_case_field: bool = False
    reuse_model: bool = False
    output_model_type: DataModelType = DataModelType.PydanticBaseModel
    # ... 110個のパラメータ


class CLIConfig(GeneratorConfig):
    """CLI用設定（+9個のUI/ユーティリティ）"""
    check: bool = False
    debug: bool = False
    disable_warnings: bool = False
    watch: bool = False
    watch_delay: float = 0.5
    # ... CLI専用設定
```

```python
# src/datamodel_code_generator/_generated/config_extras.py (自動生成)
from typing_extensions import TypedDict, NotRequired

class GeneratorExtras(TypedDict, total=False):
    snake_case_field: NotRequired[bool]
    reuse_model: NotRequired[bool]
    output_model_type: NotRequired[DataModelType]
    # ... 110個（自動生成）
```

### 構造図

```
CLIConfig (119個)
    └── 継承 → GeneratorConfig (110個)

GeneratorExtras (TypedDict, 110個)
    └── GeneratorConfigから自動生成（ドッグフーディング）

Parser.__init__
    └── 13個の内部パラメータ（変換・計算用、公開APIではない）
```

### フィールド差異（実験で確認済み）

```
CLI only (9個):
  check, debug, disable_warnings, force_optional, input,
  url, use_default, watch, watch_delay

generate() only (7個):
  apply_default_values_for_required_fields, command_line,
  custom_class_name_generator, force_optional_for_required_fields,
  graphql_scopes, input_filename, settings_path
```

## 後方互換性の維持

### generate() の実装

```python
from typing_extensions import Unpack
from ._generated.config_extras import GeneratorExtras

def generate(
    input_: Path | str | ParseResult | Mapping[str, Any],
    *,
    config: GeneratorConfig | None = None,
    **extras: Unpack[GeneratorExtras],
) -> str | GeneratedModules | None:
    """Generate Python data models from schema definitions."""

    # 両方指定はエラー
    if config is not None and extras:
        raise TypeError(
            "Cannot use both 'config' and keyword arguments. "
            "Use either config=GeneratorConfig(...) or keyword arguments, not both."
        )

    # extrasをモデルにパース → バリデーション実行
    if config is None:
        config = GeneratorConfig(**extras)

    # Parser専用パラメータを計算
    data_model_types = get_data_model_types(config.output_model_type, ...)

    parser = parser_class(
        source=source,
        # configから必要な引数を渡す
        snake_case_field=config.snake_case_field,
        reuse_model=config.reuse_model,
        # ...
        # Parser専用（変換・計算されたもの）
        data_model_type=data_model_types.data_model,
        data_model_root_type=data_model_types.root_model,
        # ...
    )
    # ...
```

### 使用例

```python
# 方法1: キーワード引数（既存の使い方 - 変更不要）
result = generate(
    input_=schema,
    output_model_type=DataModelType.PydanticV2BaseModel,
    snake_case_field=True,
)

# 方法2: configオブジェクト（新しい使い方 - 設定の再利用向き）
config = GeneratorConfig(
    output_model_type=DataModelType.PydanticV2BaseModel,
    snake_case_field=True,
)
result = generate(input_=schema, config=config)

# 複数スキーマに同じ設定を適用
for schema in schemas:
    generate(input_=schema, config=config)

# エラー: 両方指定は不可
generate(input_=schema, config=config, snake_case_field=True)  # TypeError
```

### 既存ユーザーへの影響

| 使い方 | 動作 | 警告 | 変更必要 |
|--------|------|------|---------|
| `**kwargs`のみ | ◎ | なし | なし |
| `config=`のみ | ◎ | なし | - |
| 両方 | TypeError | - | - |

**既存のコードは一切変更不要。**

## パフォーマンス考慮

### 設定オブジェクト作成のコスト

```
スキーマ解析 >> コード生成 >> フォーマット >>> 設定オブジェクト作成
   (重い)        (中程度)      (中程度)           (ほぼゼロ)
```

- 設定オブジェクトの作成は1回のみ
- Pydanticのオーバーヘッドは全体の処理時間に比べて無視できる
- msgspec等への最適化は不要

## メリット

| 観点 | 現状 | 提案後 |
|------|------|--------|
| 定義箇所 | 3箇所で重複 | 1箇所（Single Source of Truth） |
| 同期の手間 | 手動で全て同期 | 継承で自動 |
| バリデーション | なし | Pydanticが自動 |
| typo検出 | 実行時まで不明 | `extra="forbid"`で即座に検出 |
| IDE補完 | 117個のパラメータ一覧 | 階層的に補完 |
| ドキュメント | 手動で別途作成 | JSON Schemaから生成可能 |

## ビルドプロセス

### 新しいCLIオプション: `--input-model`

Pydanticモデルを直接指定してコード生成する新オプション。
`module.path:ClassName` 形式（uvicorn, gunicorn, entry pointsと同じデファクトスタンダード）。

```bash
datamodel-codegen \
    --input-model datamodel_code_generator.config:GeneratorConfig \
    --output-model-type typing.TypedDict \
    --class-name GeneratorExtras \
    --output src/datamodel_code_generator/_generated/config_extras.py
```

### 実装

```python
# arguments.py
base_options.add_argument(
    "--input-model",
    help="Python import path to a Pydantic model (e.g., 'mypackage.module:ClassName'). "
         "Uses the same format as uvicorn/gunicorn.",
    metavar="MODULE:CLASS",
)
```

```python
# __main__.py
if args.input_model:
    import importlib

    modname, _, qualname = args.input_model.partition(":")
    if not qualname:
        raise Error("--input-model must be in 'module:ClassName' format")

    module = importlib.import_module(modname)
    model_class = getattr(module, qualname)

    if not hasattr(model_class, "model_json_schema"):
        raise Error(f"{qualname} is not a Pydantic model")

    input_schema = model_class.model_json_schema()
    # continue with generate...
```

### tox統合

```ini
# tox.ini
[testenv:generate-config]
description = Generate TypedDict from GeneratorConfig
commands =
    datamodel-codegen \
        --input-model datamodel_code_generator.config:GeneratorConfig \
        --output-model-type typing.TypedDict \
        --class-name GeneratorExtras \
        --output {toxinidir}/src/datamodel_code_generator/_generated/config_extras.py

[testenv:check-config]
description = Check generated TypedDict is up to date
commands =
    datamodel-codegen \
        --input-model datamodel_code_generator.config:GeneratorConfig \
        --output-model-type typing.TypedDict \
        --class-name GeneratorExtras \
        --check \
        --output {toxinidir}/src/datamodel_code_generator/_generated/config_extras.py
```

### CI統合

```yaml
# .github/workflows/ci.yml
- name: Check generated config is up to date
  run: tox run -e check-config
```

### 形式について

`module.path:ClassName` 形式はPythonエコシステムのデファクトスタンダード：

| ツール | 例 |
|--------|-----|
| uvicorn | `uvicorn main:app` |
| gunicorn | `gunicorn myapp.wsgi:application` |
| entry_points | `console_scripts = foo = foomod:main` |
| **datamodel-codegen** | `--input-model mypackage.config:MyModel` |

参考: [Python Packaging User Guide - Entry points specification](https://packaging.python.org/en/latest/specifications/entry-points/)

## 実装フェーズ

### Phase 1: GeneratorConfig定義

1. `src/datamodel_code_generator/config.py` を作成
2. 既存`__main__.py`の`Config`クラスから110個のフィールドを移動
3. `CLIConfig(GeneratorConfig)` を作成（+9個のCLI専用）
4. 単体テストを追加

### Phase 2: TypedDict生成

1. `scripts/generate_config_extras.py` を作成
2. `tox run -e generate-config` でTypedDict生成
3. `_generated/config_extras.py` をリポジトリにコミット
4. CI で同期チェック

### Phase 3: generate()の更新

1. `generate(config=..., **extras: Unpack[...])` シグネチャに変更
2. 両方指定時のTypeError実装
3. 既存テストが全て通ることを確認

### Phase 4: ドキュメント更新

1. `using_as_module.md` を更新
2. APIドキュメント生成（JSON Schemaから）
3. マイグレーションガイドは不要（既存コード変更不要のため）

## Breaking Changes と移行時の懸念

### 解決済みの懸念

以下は問題にならない：

| 懸念 | 理由 |
|------|------|
| デフォルト値の差異 | Configモデルで統一すれば自動的に解決 |
| pyproject.toml互換性 | 既存の kebab → snake 変換ロジックをそのまま使用 |
| バリデーション追加 | バリデーションは追加しない（現状の動作を維持） |
| 型の差異 | Configモデルで広い型を採用すれば問題なし |
| **起動時間への影響** | 後述 |

### 起動時間への影響（lazy import との共存）

#### 現状の起動時間

```
--version (fast path):     44ms   ← Pydanticをロードしない
--help (fast path):        44ms   ← Pydanticをロードしない
generate() import:         26ms   ← Pydantic部分ロード
通常CLI実行:               177ms  ← 全てロード
```

#### 影響なしの理由

1. **CLI fast path は影響を受けない**
   - `--version`, `--help` は `sys.argv` をチェックして早期リターン
   - Configモデルをロードする前に終了

2. **通常実行時は既にPydanticがロードされている**
   - `__main__.py` の行49: `from pydantic import BaseModel`
   - CLIの `Config` クラス（pyproject.toml用）で既に使用中
   - 新しいConfigモデルを追加しても追加コストはほぼゼロ

3. **モジュール使用時も同様**
   - `from datamodel_code_generator import generate` で既にPydanticがロード
   - `util.py` 経由で `is_pydantic_v2()` が使われている

#### 推奨配置

```python
# src/datamodel_code_generator/config.py （新規ファイル）
from pydantic import BaseModel, Field

class ParserConfig(BaseModel):
    ...

class GeneratorConfig(ParserConfig):
    ...
```

```python
# src/datamodel_code_generator/__init__.py
# TYPE_CHECKING内でインポート（型ヒント用）
if TYPE_CHECKING:
    from datamodel_code_generator.config import GeneratorConfig, ParserConfig

# 公開APIとして必要な場合は __all__ に追加
# ユーザーは from datamodel_code_generator.config import GeneratorConfig でインポート
```

この配置なら：
- fast path に影響なし
- 既存のインポート時間に影響なし
- Configを使わないユーザーには追加コストなし

### 実際の懸念事項

#### 1. Parser を直接使うユーザーへの影響

上級者が Parser を直接使用している場合：

```python
# 現在
from datamodel_code_generator.parser.jsonschema import JsonSchemaParser
parser = JsonSchemaParser(
    source=schema,
    snake_case_field=True,  # 個別引数
)

# 移行後（警告付きで動作）
parser = JsonSchemaParser(
    source=schema,
    snake_case_field=True,  # DeprecationWarning
)

# 推奨
parser = JsonSchemaParser(
    source=schema,
    config=ParserConfig(snake_case_field=True),
)
```

**懸念**: Parser は公開 API として文書化されていないが、使われている可能性。

#### 2. テストへの影響

多数のテストが kwargs を使用：

```python
# tests/ 内で多用されているパターン
result = generate(
    input_=schema,
    snake_case_field=True,
    # ...
)
```

**対策**:
- 警告を出しつつ動作を維持
- テストは徐々に config= 形式に移行
- `pytest -W ignore::DeprecationWarning` でCI を一時的に通す

#### 3. サードパーティ統合への影響

datamodel-code-generator を内部で使っているツール：
- IDE プラグイン
- CI/CD パイプライン
- カスタムラッパー

**対策**:
- 少なくとも1つのマイナーバージョンで非推奨警告を出す
- CHANGELOG に移行ガイドを記載
- breaking change はメジャーバージョンでのみ

#### 4. 移行期間の提案

```
v0.X.0  - GeneratorConfig 追加、kwargs は警告付きで動作
v0.X+1  - ドキュメントで config= を推奨
v0.X+2  - 警告をより目立たせる
v1.0.0  - kwargs を削除（optional、ユーザーフィードバック次第）
```

#### 5. 互換性テストの追加

```python
def test_backward_compatibility():
    """既存の呼び出し方法が動作することを確認"""
    # 旧形式（警告は出るが動作する）
    with pytest.warns(DeprecationWarning):
        result = generate(
            input_=schema,
            snake_case_field=True,
        )
    assert result is not None

def test_new_api():
    """新しい呼び出し方法が動作することを確認"""
    config = GeneratorConfig(snake_case_field=True)
    result = generate(input_=schema, config=config)
    assert result is not None

def test_mixed_api():
    """混合呼び出しが動作することを確認"""
    config = GeneratorConfig(output_model_type=DataModelType.PydanticV2BaseModel)
    with pytest.warns(DeprecationWarning):
        result = generate(
            input_=schema,
            config=config,
            snake_case_field=True,  # configにマージ
        )
    assert result is not None
```

## 決定事項

### 1. Configモデルの構造
**決定: A (フラット)** - 既存互換、pyproject.toml互換

### 2. 公開API
**決定: B (サブモジュール)** - `from datamodel_code_generator.config import GeneratorConfig`

### 3. 既存`__main__.py`の`Config`クラスとの関係
**決定: B (継承)** - `CLIConfig(GeneratorConfig)` の継承構造

### 4. kwargs の扱い
**決定: Unpack[TypedDict]** - 警告なし、型安全、IDE補完対応

### 5. config と kwargs の両方指定
**決定: TypeError** - 両方指定時はエラー

### 6. TypedDictの生成方法
**決定: ドッグフーディング** - datamodel-code-generator自身で生成

## ステータス

**設計完了** - 2025-12-25

実装準備完了。全レイヤーで動作確認済み。

## 関連ファイル

- `src/datamodel_code_generator/__init__.py` - generate()関数
- `src/datamodel_code_generator/__main__.py` - 既存Configクラス（行140-562）
- `src/datamodel_code_generator/arguments.py` - CLI引数定義
- `src/datamodel_code_generator/parser/base.py` - Parser基底クラス
- `src/datamodel_code_generator/cli_options.py` - CLIオプションメタデータ
- `docs/using_as_module.md` - モジュール使用ドキュメント
