#!/usr/bin/env python3
"""Extract idsignpost HTML entries into markdown."""

from __future__ import annotations

import argparse
import html
import re
from datetime import datetime
import sys
from pathlib import Path

from bs4 import BeautifulSoup, Tag
from markdownify import markdownify
from urllib.parse import unquote

FIELD_LABELS = {
    "field-description": "Description",
    "field-author-s": "Author(s)",
    "field-free": "Free",
    "field-available-as": "Available as",
    "field-web-link": "Web link",
    "field-additional-web-link": "Additional web link",
    "field-taxa": "Keywords",
    "field-major-taxon-group": "Major group(s)",
    "body": "Body",
}


def clean_text(value: str) -> str:
    if not value:
        return ""
    for _ in range(2):
        value = html.unescape(value)
    value = value.replace("\r", "\n")
    value = re.sub(r"[ \t]+\n", "\n", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def fix_split_urls(fragment: str) -> str:
    """Fix URLs that are split between a link and following text.
    
    E.g., <a href="...url">...url</a>@N07/rest handles cases where the @ symbol
    and following path were outside the link tag in the original HTML.
    
    We need to:
    1. Extract the URL continuation after </a>
    2. Append it to the href attribute
    3. Append it to the link text
    4. Remove the text after </a>
    """
    # Pattern: <a href="([^"]*)">([^<]*)</a>([@/][^\s<]*)
    # Captures: (1) href value, (2) link text, (3) URL continuation
    pattern = r'<a\s+href="([^"]*)">([^<]*)</a>([@/][^\s<]*)'
    
    def fix_match(match: re.Match) -> str:
        href = match.group(1)
        link_text = match.group(2)
        continuation = match.group(3)
        complete_url = href + continuation
        complete_text = link_text + continuation
        return f'<a href="{complete_url}">{complete_text}</a>'
    
    return re.sub(pattern, fix_match, fragment)


def to_markdown(fragment: str) -> str:
    fragment = fix_split_urls(fragment)
    text = markdownify(fragment, heading_style="ATX", bullets="-")
    text = clean_text(text)
    return normalize_markdown_links(text)


URL_LINK_PATTERN = re.compile(r"\[(?P<text>[^\]]+)\]\((?P<url>[^)]+)\)")
ANGLE_LINK_PATTERN = re.compile(r"<(?P<url>https?://[^>]+)>")


def normalize_markdown_links(text: str) -> str:
    def format_link(match: re.Match) -> str:
        raw_url = match.group("url").strip()
        # Skip if already wrapped in angle brackets
        if raw_url.startswith("<") and raw_url.endswith(">"):
            return match.group(0)
        decoded_url = unquote(raw_url)
        link_text = match.group("text")
        # Always decode the display text to remove %20 and other encodings
        display_text = unquote(link_text)
        return f"[{display_text}](<{decoded_url}>)"

    def format_angle(match: re.Match) -> str:
        raw_url = match.group("url").strip()
        decoded_url = unquote(raw_url)
        return f"[{decoded_url}](<{decoded_url}>)"

    # First pass: normalize bare angle-bracketed URLs
    text = ANGLE_LINK_PATTERN.sub(format_angle, text)
    # Second pass: normalize markdown links (but skip if URL already has angle brackets)
    return URL_LINK_PATTERN.sub(format_link, text)


def derive_label(field: Tag) -> str:
    label_node = field.select_one(".field-label")
    if label_node:
        label = clean_text(label_node.get_text(" ", strip=True)).rstrip(":")
        if label:
            return label
    class_attr = field.get("class")
    if not class_attr:
        return "Field"
    class_names = class_attr if isinstance(class_attr, list) else [class_attr]
    for class_name in class_names:
        if class_name.startswith("field-name-"):
            raw = class_name[len("field-name-") :].strip("-")
            if raw in FIELD_LABELS:
                return FIELD_LABELS[raw]
            friendly = raw.replace("-", " ").strip()
            return friendly.title() if friendly else "Field"
    return "Field"


def extract_fields(main: BeautifulSoup) -> list[tuple[str, list[str]]]:
    fields: list[tuple[str, list[str]]] = []
    for field in main.select(".field"):
        label = derive_label(field)
        items = field.select(".field-item")
        if items:
            values = [to_markdown(item.decode_contents()) for item in items]
        else:
            values = [to_markdown(field.decode_contents())]
        values = [value for value in values if value]
        if values:
            fields.append((label, values))
    return fields


def extract_main(file_path: Path) -> tuple[dict[str, str], list[tuple[str, list[str]]]] | None:
    html_text = file_path.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(html_text, "html.parser")
    main = soup.find("div", id="main")
    if not main:
        return None

    for link_wrapper in main.select(".link-wrapper"):
        link_wrapper.decompose()

    title_node = main.find("h1")
    title = clean_text(title_node.get_text(" ", strip=True)) if title_node else ""

    submitted_node = main.select_one(".meta.submitted")
    submitted = format_submitted(submitted_node) if submitted_node else ""

    fields = extract_fields(main)
    content = ""
    if not fields:
        main_clone = BeautifulSoup(str(main), "html.parser")
        inner = main_clone.find("div", id="main") or main_clone
        for selector in ("h1", ".meta", ".tabs", ".link-wrapper"):
            for node in inner.select(selector):
                node.decompose()
        content = to_markdown(inner.decode_contents())

    data = {"title": title, "submitted": submitted, "content": content}
    return data, fields


def append_multiline(lines: list[str], text: str, indent: int) -> None:
    prefix = " " * indent
    for line in text.splitlines():
        lines.append(f"{prefix}{line}" if line else "")


def render_markdown(
    filename: str, data: dict[str, str], fields: list[tuple[str, list[str]]]
) -> str:
    lines: list[str] = [f"## {filename}", ""]

    if data["title"]:
        lines.append(f"- Title: {data['title']}")
    if data["submitted"]:
        lines.append(f"- Submitted: {data['submitted']}")

    if fields:
        for label, values in fields:
            if len(values) == 1 and "\n" not in values[0]:
                lines.append(f"- {label}: {values[0]}")
                continue

            lines.append(f"- {label}:")
            if len(values) == 1:
                append_multiline(lines, values[0], 2)
            else:
                for value in values:
                    if "\n" not in value:
                        lines.append(f"  - {value}")
                    else:
                        lines.append("  -")
                        append_multiline(lines, value, 4)
    elif data["content"]:
        lines.append("- Content:")
        append_multiline(lines, data["content"], 2)
    else:
        lines.append("- Content: (empty)")

    lines.append("")
    return "\n".join(lines)


def gather_files(base_path: Path, limit: int | None) -> list[Path]:
    files = [
        file_path
        for file_path in sorted(base_path.glob("*.html"))
        if file_path.name.lower() != "about.html"
    ]
    if limit is not None:
        return files[:limit]
    return files


def format_submitted(node: BeautifulSoup) -> str:
    raw = clean_text(node.get_text(" ", strip=True))
    match = re.match(
        r"^Submitted by\s+(?P<author>.+?)\s+on\s+(?P<date>.+)$",
        raw,
        flags=re.IGNORECASE,
    )
    if not match:
        return raw

    author = match.group("author")
    date_text = match.group("date")
    iso_date = to_iso_datetime(date_text)
    if iso_date:
        return f"{author}; {iso_date}"
    return f"{author}; {date_text}"


def to_iso_datetime(date_text: str) -> str | None:
    cleaned = date_text.strip()
    for fmt in ("%a, %d/%m/%Y - %H:%M", "%A, %d/%m/%Y - %H:%M"):
        try:
            parsed = datetime.strptime(cleaned, fmt)
        except ValueError:
            continue
        return parsed.strftime("%Y-%m-%dT%H:%M:%S")
    return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract <div id=\"main\"> content from idsignpost HTML files."
    )
    parser.add_argument(
        "--path",
        default="./idsignpost",
        help="Directory containing idsignpost HTML files.",
    )
    parser.add_argument(
        "--test",
        nargs="?",
        const=5,
        type=int,
        help="Process only a sample of N files (default: 5).",
    )
    parser.add_argument(
        "--output",
        help="Write markdown output to a file instead of stdout.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    base_path = Path(args.path)
    if args.test is not None and args.test < 1:
        raise SystemExit("--test must be at least 1.")

    files = gather_files(base_path, args.test)
    if not files:
        raise SystemExit(f"No HTML files found in {base_path}.")

    sections: list[str] = []
    for file_path in files:
        result = extract_main(file_path)
        if result is None:
            print(f"Skipping {file_path}: no <div id=\"main\"> found.", file=sys.stderr)
            continue
        data, fields = result
        sections.append(render_markdown(file_path.name, data, fields))

    output = "\n".join(sections).rstrip() + "\n"
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    else:
        print(output, end="")


if __name__ == "__main__":
    main()
