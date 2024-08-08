import io
import re
from pathlib import Path

from datamodel_code_generator.__main__ import arg_parser

START_MARK: str = '<!-- start command help -->'
END_MARK: str = '<!-- end command help -->'
BASH_CODE_BLOCK: str = '```bash'
CODE_BLOCK_END: str = '```'

CURRENT_DIR = Path(__file__).parent
PROJECT_DIR = CURRENT_DIR.parent
DOC_DIR = PROJECT_DIR / 'docs'

TARGET_MARKDOWN_FILES: list[Path] = [
    DOC_DIR / 'index.md',
    PROJECT_DIR / 'README.md',
]


def get_help():
    with io.StringIO() as f:
        arg_parser.print_help(file=f)
        raw_output = f.getvalue()
        # Remove any terminal codes
    return re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', raw_output)


def inject_help(markdown_text: str, help_text: str) -> str:
    # Inject help_text into markdown_text at the position between <!-- start command help --> and <!-- end command
    # help --> the start and end markers are included in the returned markdown_text

    start_pos = markdown_text.find(START_MARK)
    end_pos = markdown_text.find(END_MARK)
    if start_pos == -1 or end_pos == -1:
        raise ValueError(f'Could not find {START_MARK} or {END_MARK} in markdown_text')
    return (
        markdown_text[: start_pos + len(START_MARK)]
        + '\n'
        + BASH_CODE_BLOCK
        + '\n'
        + help_text
        + CODE_BLOCK_END
        + '\n'
        + markdown_text[end_pos:]
    )


def main():
    help_text = get_help()
    for file_path in TARGET_MARKDOWN_FILES:
        with file_path.open('r') as f:
            markdown_text = f.read()
        new_markdown_text = inject_help(markdown_text, help_text)
        with file_path.open('w') as f:
            f.write(new_markdown_text)


if __name__ == '__main__':
    main()
