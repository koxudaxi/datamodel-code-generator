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

## 5. Create new branch and rewrite code.
$ git checkout -b new-branch

## 6. Run unittest under Python 3.13 (you should pass all test and coverage should be 100%)
$ tox run -e 3.13

## 7. Format and lint code (will print errors that cannot be automatically fixed)
$ tox run -e fix

## 8. Check README help text is up to date
$ tox run -e readme

## 9. Check CLI documentation is up to date
$ tox run -e cli-docs

## 10. Commit and Push...
```

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
