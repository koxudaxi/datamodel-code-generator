# Custom Code Formatters

New features of the `datamodel-code-generator` it is custom code formatters.

## Usage
To use the `--custom-formatters` option, you'll need to pass the module with your formatter. For example

**your_module.py**
```python
from datamodel_code_generator.format import CustomCodeFormatter

class CodeFormatter(CustomCodeFormatter):
    def apply(self, code: str) -> str:
        # processed code
        return ...       

```

and run the following command

```sh
$ datamodel-codegen --input {your_input_file} --output {your_output_file} --custom-formatters "{path_to_your_module}.your_module"
```
