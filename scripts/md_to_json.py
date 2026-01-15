#!/usr/bin/env python3
"""Convert idsignpost.md to JSON format."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def parse_markdown_entry(lines: list[str]) -> dict[str, str | list[str]]:
    """Parse a single markdown entry into a dictionary."""
    entry: dict[str, str | list[str]] = {}
    current_field = None
    current_value: list[str] = []
    in_multiline = False

    for line in lines:
        # Skip empty lines at the start
        if not line.strip():
            continue

        # Match field: value pattern
        field_match = re.match(r"^- ([^:]+):\s*(.*)$", line)
        if field_match:
            # Save previous field if exists
            if current_field:
                _save_field(entry, current_field, current_value)

            current_field = field_match.group(1)
            value_part = field_match.group(2).strip()

            if value_part:
                # Single-line value
                current_value = [value_part]
                in_multiline = False
            else:
                # Multi-line or multi-value field
                current_value = []
                in_multiline = True
            continue

        # Match nested list item
        nested_match = re.match(r"^  - (.+)$", line)
        if nested_match and current_field:
            value = nested_match.group(1).strip()
            if value:
                current_value.append(value)
            in_multiline = True
            continue

        # Match indented content (multi-line field value)
        indent_match = re.match(r"^  (.*)$", line)
        if indent_match and current_field and in_multiline:
            content = indent_match.group(1)
            current_value.append(content)
            continue

    # Save the last field
    if current_field:
        _save_field(entry, current_field, current_value)

    return entry


def _save_field(
    entry: dict[str, str | list[str]], field: str, values: list[str]
) -> None:
    """Save a field to the entry dictionary."""
    if not values:
        entry[field] = ""
        return

    # Join multi-line content
    if len(values) == 1:
        entry[field] = values[0]
    else:
        # Check if it's a multi-value field (multiple items) or multi-line text
        # Multi-line text will have empty strings or continuation lines
        has_empty = "" in values
        if has_empty or all(not v or v[0].islower() for v in values[1:] if v):
            # Multi-line text - join with newlines
            entry[field] = "\n".join(values).strip()
        else:
            # Multi-value field - keep as array
            entry[field] = [v for v in values if v]


def parse_markdown_file(file_path: Path) -> list[dict[str, str | list[str]]]:
    """Parse the entire markdown file into a list of entries."""
    content = file_path.read_text(encoding="utf-8")
    entries = []

    # Split by ## headings
    sections = re.split(r"^## (.+)$", content, flags=re.MULTILINE)

    # First element is content before first heading (should be empty or whitespace)
    sections = sections[1:]  # Skip it

    # Process pairs of (filename, content)
    for i in range(0, len(sections), 2):
        if i + 1 >= len(sections):
            break

        filename = sections[i].strip()
        content_lines = sections[i + 1].strip().split("\n")

        entry_data = parse_markdown_entry(content_lines)
        entry_data["filename"] = filename

        entries.append(entry_data)

    return entries


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Convert idsignpost.md to JSON format."
    )
    parser.add_argument(
        "--input",
        default="idsignpost.md",
        help="Input markdown file (default: idsignpost.md)",
    )
    parser.add_argument(
        "--output",
        help="Output JSON file. If not specified, outputs to stdout.",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="JSON indentation level (default: 2, use 0 for compact)",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON with sorted keys",
    )
    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    args = parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file '{input_path}' not found.", file=sys.stderr)
        sys.exit(1)

    entries = parse_markdown_file(input_path)

    # Prepare JSON output
    indent = args.indent if args.indent > 0 else None
    json_output = json.dumps(
        entries,
        indent=indent,
        ensure_ascii=False,
        sort_keys=args.pretty,
    )

    if args.output:
        Path(args.output).write_text(json_output + "\n", encoding="utf-8")
        print(f"Wrote {len(entries)} entries to {args.output}", file=sys.stderr)
    else:
        print(json_output)


if __name__ == "__main__":
    main()
