"""llms.txt generator for datamodel-code-generator documentation.

Generates llms.txt and llms-full.txt from zensical.toml nav structure.
See https://llmstxt.org/ for the llms.txt specification.

Usage:
    python scripts/build_llms_txt.py
    python scripts/build_llms_txt.py --check  # CI: check if files are up to date
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

try:
    import tomllib
except ImportError:
    import tomli as tomllib

ROOT_DIR = Path(__file__).parent.parent
DOCS_DIR = ROOT_DIR / "docs"
ZENSICAL_TOML = ROOT_DIR / "zensical.toml"

OPTIONAL_PATTERNS = [
    "faq.md",
    "development-contributing.md",
    "cli-reference/manual/*.md",
]

MAX_DESCRIPTION_LINES = 2
MAX_DESCRIPTION_LENGTH = 150
TRUNCATED_DESCRIPTION_LENGTH = 147

EMOJI_PATTERN = re.compile(
    r"["
    r"\U0001F300-\U0001F9FF"
    r"\U0001FA00-\U0001FA6F"
    r"\U0001FA70-\U0001FAFF"
    r"\U00002702-\U000027B0"
    r"\U0001F680-\U0001F6FF"
    r"\U0001F1E0-\U0001F1FF"
    r"\U00002600-\U000026FF"
    r"\U00002300-\U000023FF"
    r"\U0000FE00-\U0000FE0F"
    r"\U0000200D"
    r"]+",
    flags=re.UNICODE,
)


@dataclass
class PageInfo:
    """Information about a documentation page."""

    title: str
    path: str
    url: str
    description: str
    content: str
    depth: int = 0
    is_section: bool = False


@dataclass
class NavSection:
    """A navigation section with optional children."""

    title: str
    path: str | None = None
    children: list[NavSection] = field(default_factory=list)
    depth: int = 0


def parse_zensical_toml(path: Path) -> dict[str, Any]:
    """Parse zensical.toml and extract project configuration."""
    if not path.exists():
        print(f"Error: {path} not found", file=sys.stderr)
        sys.exit(1)

    try:
        with path.open("rb") as f:
            config = tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        print(f"Error parsing {path}: {e}", file=sys.stderr)
        sys.exit(1)

    project = config.get("project", {})
    return {
        "site_name": project.get("site_name", ""),
        "site_description": project.get("site_description", ""),
        "site_url": project.get("site_url", "").rstrip("/"),
        "nav": project.get("nav", []),
    }


def flatten_nav(nav: list[dict[str, Any]], depth: int = 0) -> list[NavSection]:
    """Recursively flatten navigation structure."""
    sections: list[NavSection] = []

    for item in nav:
        for title, value in item.items():
            if isinstance(value, str):
                sections.append(NavSection(title=title, path=value, depth=depth))
            elif isinstance(value, list):
                section = NavSection(title=title, depth=depth)
                section.children = flatten_nav(value, depth + 1)
                sections.append(section)

    return sections


def remove_emoji(text: str) -> str:
    """Remove emoji characters from text."""
    return EMOJI_PATTERN.sub("", text).strip()


def extract_page_info(md_path: Path, url: str, depth: int = 0) -> PageInfo | None:
    """Extract title and description from a Markdown file."""
    if not md_path.exists():
        print(f"Warning: {md_path} not found, skipping", file=sys.stderr)
        return None

    try:
        content = md_path.read_text(encoding="utf-8")
    except OSError as e:
        print(f"Warning: Cannot read {md_path}: {e}", file=sys.stderr)
        return None

    lines = content.split("\n")
    title = md_path.stem.replace("-", " ").replace("_", " ").title()
    description = ""

    in_code_block = False
    found_h1 = False
    description_lines: list[str] = []

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue

        if in_code_block:
            continue

        if stripped.startswith("# ") and not found_h1:
            title = remove_emoji(stripped[2:].strip())
            found_h1 = True
            continue

        if found_h1:
            if stripped.startswith("## "):
                break

            if stripped.startswith("!!!"):
                continue
            if stripped.startswith("[!["):
                continue
            if stripped.startswith("!["):
                continue
            if stripped.startswith("<"):
                continue
            if stripped.startswith("---"):
                continue
            if not stripped:
                if description_lines:
                    break
                continue

            description_lines.append(stripped)
            if len(description_lines) >= MAX_DESCRIPTION_LINES:
                break

    if description_lines:
        description = " ".join(description_lines)
        description = remove_emoji(description)
        if len(description) > MAX_DESCRIPTION_LENGTH:
            description = description[:TRUNCATED_DESCRIPTION_LENGTH] + "..."

    return PageInfo(
        title=title,
        path=str(md_path.relative_to(DOCS_DIR)),
        url=url,
        description=description,
        content=content,
        depth=depth,
    )


def is_optional_page(path: str) -> bool:
    """Check if a page should be in the Optional section."""
    return any(fnmatch(path, pattern) for pattern in OPTIONAL_PATTERNS)


def collect_pages(sections: list[NavSection], site_url: str, depth: int = 0) -> list[PageInfo]:
    """Collect all pages from navigation sections."""
    pages: list[PageInfo] = []

    for section in sections:
        if section.path:
            md_path = DOCS_DIR / section.path
            path_without_ext = section.path.rsplit(".", 1)[0]
            if path_without_ext == "index":
                url = f"{site_url}/"
            elif path_without_ext.endswith("/index"):
                url = f"{site_url}/{path_without_ext[:-6]}/"
            else:
                url = f"{site_url}/{path_without_ext}/"

            page = extract_page_info(md_path, url, depth)
            if page:
                pages.append(page)

        if section.children:
            pages.extend(collect_pages(section.children, site_url, depth + 1))

    return pages


def _format_page_link(page: PageInfo) -> str:
    """Format a page as a markdown link with optional description."""
    desc = f": {page.description}" if page.description else ""
    return f"- [{page.title}]({page.url}){desc}"


def _render_optional_sections(sections: list[NavSection], page_map: dict[str, PageInfo]) -> list[str]:
    """Render optional sections as a flat list of links."""
    lines: list[str] = []
    for section in sections:
        if section.path:
            page = page_map.get(section.path)
            if page:
                lines.append(_format_page_link(page))
        elif section.children:
            for child in section.children:
                if child.path:
                    page = page_map.get(child.path)
                    if page:
                        lines.append(_format_page_link(page))
    return lines


def generate_llms_txt(config: dict[str, Any], sections: list[NavSection], pages: list[PageInfo]) -> str:
    """Generate llms.txt content."""
    lines: list[str] = []

    lines.extend((f"# {config['site_name']}", "", f"> {config['site_description']}", ""))

    page_map = {p.path: p for p in pages}

    main_sections: list[NavSection] = []
    optional_sections: list[NavSection] = []

    for section in sections:
        if section.path and is_optional_page(section.path):
            optional_sections.append(section)
        elif section.children:
            has_optional = all(child.path and is_optional_page(child.path) for child in section.children)
            if has_optional:
                optional_sections.append(section)
            else:
                main_sections.append(section)
        else:
            main_sections.append(section)

    def render_section(section: NavSection) -> list[str]:
        result: list[str] = []

        if section.path:
            page = page_map.get(section.path)
            if page:
                result.append(_format_page_link(page))
        elif section.children:
            if section.depth == 0:
                result.extend((f"## {section.title}", ""))
            else:
                result.extend((f"### {section.title}", ""))

            for child in section.children:
                result.extend(render_section(child))

            result.append("")

        return result

    for section in main_sections:
        section_lines = render_section(section)
        lines.extend(section_lines)

    if optional_sections:
        lines.extend(("## Optional", ""))
        lines.extend(_render_optional_sections(optional_sections, page_map))
        lines.append("")

    while lines and not lines[-1]:
        lines.pop()
    lines.append("")

    return "\n".join(lines)


def generate_llms_full_txt(pages: list[PageInfo]) -> str:
    """Generate llms-full.txt with all documentation content."""
    parts: list[str] = []

    for page in pages:
        parts.extend((f"# {page.title}", "", f"Source: {page.url}", ""))

        content = page.content.strip()
        if content.startswith("# "):
            first_newline = content.find("\n")
            if first_newline != -1:
                content = content[first_newline + 1 :].strip()

        parts.extend((content, "", "---", ""))

    return "\n".join(parts)


def main() -> int:
    """Run the llms.txt generator."""
    parser = argparse.ArgumentParser(description="Generate llms.txt files from documentation")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check if files are up to date without modifying",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DOCS_DIR,
        help="Output directory (default: docs/)",
    )
    args = parser.parse_args()

    config = parse_zensical_toml(ZENSICAL_TOML)
    sections = flatten_nav(config["nav"])
    pages = collect_pages(sections, config["site_url"])

    llms_txt = generate_llms_txt(config, sections, pages)
    llms_full_txt = generate_llms_full_txt(pages)

    llms_txt_path = args.output_dir / "llms.txt"
    llms_full_txt_path = args.output_dir / "llms-full.txt"

    if args.check:
        errors = []

        if not llms_txt_path.exists():
            errors.append(f"{llms_txt_path} does not exist")
        elif llms_txt_path.read_text(encoding="utf-8") != llms_txt:
            errors.append(f"{llms_txt_path} is out of date")

        if not llms_full_txt_path.exists():
            errors.append(f"{llms_full_txt_path} does not exist")
        elif llms_full_txt_path.read_text(encoding="utf-8") != llms_full_txt:
            errors.append(f"{llms_full_txt_path} is out of date")

        if errors:
            for error in errors:
                print(f"Error: {error}", file=sys.stderr)
            print(
                "\nRun 'python scripts/build_llms_txt.py' to regenerate.",
                file=sys.stderr,
            )
            return 1

        print("llms.txt files are up to date")
        return 0

    args.output_dir.mkdir(parents=True, exist_ok=True)

    llms_txt_path.write_text(llms_txt, encoding="utf-8")
    print(f"Generated {llms_txt_path}")

    llms_full_txt_path.write_text(llms_full_txt, encoding="utf-8")
    print(f"Generated {llms_full_txt_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
