# 🛠️ Development

Install the package in editable mode:

```sh
$ git clone git@github.com:koxudaxi/datamodel-code-generator.git
$ pip install -e datamodel-code-generator
```

# 🤝 Contribute

We are waiting for your contributions to `datamodel-code-generator`.

## 📝 How to contribute

```bash
## 1. Clone your fork repository
$ git clone git@github.com:<your username>/datamodel-code-generator.git
$ cd datamodel-code-generator

## 2. Install [uv](https://docs.astral.sh/uv/getting-started/installation/)
$ curl -LsSf https://astral.sh/uv/install.sh | sh

## 3. Install tox with uv
$ uv tool install --python-preference only-managed --python 3.13 tox --with tox-uv

## 4. Create developer environment
$ tox run -e dev

.tox/dev is a Python environment you can use for development purposes

## 5. Install pre-commit hooks
$ uv tool install prek
$ prek install

## 6. Create new branch and rewrite code.
$ git checkout -b new-branch

## 7. Run unittest under Python 3.13 (you should pass all test and coverage should be 100%)
$ tox run -e 3.13

## 8. Format and lint code (will print errors that cannot be automatically fixed)
$ tox run -e fix

## 9. Check README help text is up to date
$ tox run -e readme

## 10. Check CLI documentation is up to date
$ tox run -e cli-docs

## 11. Commit and Push...
```

## 🧪 E2E test assertions

E2E tests that validate generated output must use the shared assertion helpers
instead of direct `assert` statements. The helpers compare complete generated
files, generated modules, warnings, errors, and HTTP request behavior with
consistent diffs and update hints.

Use helpers such as `run_main_and_assert`, `run_main_url_and_assert`,
`create_assert_file_content`, `assert_output`, `assert_directory_content`,
`assert_generated_modules_output`, `assert_generated_file_matches_output`,
`assert_httpx_get_kwargs`, and `assert_warnings_contain` where they fit. Prefer
full expected-file or inline snapshot comparisons for generated output over
substring checks.

The file-output helpers use
[`inline-snapshot`](https://15r10nk.github.io/inline-snapshot/latest/) and
`external_file()` internally. When an expected output file is missing, the
failure message includes the command to create it, such as
`tox run -e <version> -- --inline-snapshot=create`. When an existing expected
file differs from the generated output, the failure includes a diff and the
command to update it, such as
`tox run -e <version> -- --inline-snapshot=fix`. Review the generated files and
the resulting `git diff` before committing. See the inline-snapshot
[`--inline-snapshot` pytest options](https://15r10nk.github.io/inline-snapshot/latest/pytest/#-inline-snapshotcreatefixtrimupdate)
for the meaning of `create` and `fix`.

Direct `assert` statements are blocked in the guarded E2E test modules by
`tests/test_assert_helper_usage.py`. If you add a new E2E test file that checks
generated output, add it to `E2E_TEST_PATHS` in that guard test so new direct
assertions are also rejected. Only use `@pytest.mark.allow_direct_assert` for
cases that cannot reasonably be expressed with the shared helpers, such as
mock setup internals or narrow intermediate-state checks.

## ➕ Adding a New CLI Option

When adding a new CLI option to `datamodel-code-generator`, follow these steps:

### Step 1: Implement the option (Required)

Add the option to `src/datamodel_code_generator/arguments.py`:

```python
arg_parser.add_argument(
    "--my-new-option",
    help="Description of what this option does",
    action="store_true",  # or other action type
)
```

### Step 2: Add a test with documentation marker (Required)

Create a test that demonstrates the option and add the `@pytest.mark.cli_doc()` marker:

```python
@pytest.mark.cli_doc(
    options=["--my-new-option"],
    input_schema="jsonschema/example.json",  # Path relative to tests/data/
    cli_args=["--my-new-option"],
    golden_output="jsonschema/example_with_my_option.py",  # Expected output
)
def test_my_new_option(output_file: Path) -> None:
    """Short description of what the option does.

    This docstring becomes the documentation for the option.
    Explain when and why users would use this option.
    """
    run_main_and_assert(
        input_path=JSON_SCHEMA_DATA_PATH / "example.json",
        output_path=output_file,
        extra_args=["--my-new-option"],
        ...
    )
```

### Step 3: Categorize the option (Optional)

By default, new options appear in "General Options". To place in a specific category, add to `src/datamodel_code_generator/cli_options.py`:

```python
CLI_OPTION_META: dict[str, CLIOptionMeta] = {
    ...
    "--my-new-option": CLIOptionMeta(
        name="--my-new-option",
        category=OptionCategory.MODEL,  # or FIELD, TYPING, TEMPLATE, etc.
    ),
}
```

### Step 4: Generate and verify documentation

```bash
# Regenerate CLI docs
$ pytest --collect-cli-docs -p no:xdist -q
$ python scripts/build_cli_docs.py

# Verify docs are correct
$ tox run -e cli-docs

# If you modified config.py, regenerate config TypedDicts
$ tox run -e config-types
```

### 🔧 Troubleshooting

If `tox run -e cli-docs` fails:

- **"No test found documenting option --xxx"**: Add `@pytest.mark.cli_doc(options=["--xxx"], ...)` to a test
- **"File not found: ..."**: Check that `input_schema` and `golden_output` paths are correct
- **"CLI docs are OUT OF DATE"**: Run `python scripts/build_cli_docs.py` to regenerate

## 📖 CLI Documentation Marker Reference

The `cli_doc` marker supports:

| Parameter | Required | Description |
|-----------|----------|-------------|
| `options` | Yes | List of CLI options this test documents |
| `input_schema` | Yes | Input schema path (relative to `tests/data/`) |
| `cli_args` | Yes | CLI arguments used in the test |
| `golden_output` | Yes* | Expected output file path |
| `model_outputs` | No | Dict of model type → output file (for multi-model tabs) |
| `version_outputs` | No | Dict of Python version → output file |
| `comparison_output` | No | Baseline output without option (for before/after) |
| `primary` | No | Set `True` if this is the main example for the option |

*Either `golden_output` or `model_outputs` is required.

See existing tests in `tests/main/` for examples.
