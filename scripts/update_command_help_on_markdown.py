from __future__ import annotations  # noqa: INP001

import io
import os
import re
import sys
from pathlib import Path

from datamodel_code_generator.__main__ import Exit, arg_parser  # noqa: PLC2701

os.environ["COLUMNS"] = "94"
os.environ["LINES"] = "24"

START_MARK: str = "<!-- start command help -->"
END_MARK: str = "<!-- end command help -->"
BASH_CODE_BLOCK: str = "```bash"
CODE_BLOCK_END: str = "```"

CURRENT_DIR = Path(__file__).parent
PROJECT_DIR = CURRENT_DIR.parent
DOC_DIR = PROJECT_DIR / "docs"

TARGET_MARKDOWN_FILES: list[Path] = [
    DOC_DIR / "index.md",
    PROJECT_DIR / "README.md",
]

REPLACE_MAP = {"(default: UTF-8)": "(default: utf-8)", "'": r"''"}


def get_help() -> str:
    with io.StringIO() as f:
        arg_parser.print_help(file=f)
        output = f.getvalue()
    for k, v in REPLACE_MAP.items():
        output = output.replace(k, v)
    # Remove any terminal codes
    return re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", output)


def inject_help(markdown_text: str, help_text: str) -> str:
    # Inject help_text into markdown_text at the position between <!-- start command help --> and <!-- end command
    # help --> the start and end markers are included in the returned markdown_text

    start_pos = markdown_text.find(START_MARK)
    end_pos = markdown_text.find(END_MARK)
    if start_pos == -1 or end_pos == -1:
        msg = f"Could not find {START_MARK} or {END_MARK} in markdown_text"
        raise ValueError(msg)
    return (
        markdown_text[: start_pos + len(START_MARK)]
        + "\n"
        + BASH_CODE_BLOCK
        + "\n"
        + help_text
        + CODE_BLOCK_END
        + "\n"
        + markdown_text[end_pos:]
    )


def main() -> Exit:
    help_text = get_help()
    arg_parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate the file content is up to date",
    )
    args = arg_parser.parse_args()
    validate: bool = args.validate

    for file_path in TARGET_MARKDOWN_FILES:
        with file_path.open("r") as f:
            markdown_text = f.read()
        new_markdown_text = inject_help(markdown_text, help_text)
        if validate and new_markdown_text != markdown_text:
            return Exit.ERROR
        with file_path.open("w") as f:
            f.write(new_markdown_text)
    return Exit.OK


if __name__ == "__main__":
    sys.exit(main())
