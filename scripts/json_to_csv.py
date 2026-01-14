#!/usr/bin/env python3
"""Convert idsignpost.json to CSV format."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path


# Canonical field order matching the markdown format
FIELD_ORDER = [
    "filename",
    "Title",
    "Submitted",
    "Description",
    "Author(s)",
    "Free",
    "Available as",
    "Web link",
    "Additional web link",
    "Keywords",
    "Major group(s)",
    "Body",
]


def json_to_csv(
    json_entries: list[dict],
    array_delimiter: str = ";",
    preserve_newlines: bool = True,
) -> tuple[list[str], list[dict]]:
    """Convert JSON entries to CSV-compatible format.
    
    Args:
        json_entries: List of entry dictionaries from JSON
        array_delimiter: Delimiter for joining array fields (default: ";")
        preserve_newlines: Keep newlines in multi-line fields (default: True)
    
    Returns:
        Tuple of (fieldnames, rows) suitable for csv.DictWriter
    """
    if not json_entries:
        return [], []
    
    # Collect all unique field names to create consistent columns
    all_fields = set()
    for entry in json_entries:
        all_fields.update(entry.keys())
    
    # Order fields according to FIELD_ORDER, then add any extras alphabetically
    fieldnames = []
    for field in FIELD_ORDER:
        if field in all_fields:
            fieldnames.append(field)
            all_fields.remove(field)
    
    # Add any remaining fields alphabetically
    fieldnames.extend(sorted(all_fields))
    
    # Convert entries for CSV output
    rows = []
    for entry in json_entries:
        row = {}
        for field in fieldnames:
            value = entry.get(field, "")
            
            # Handle different value types
            if isinstance(value, list):
                # Join array values with delimiter
                row[field] = array_delimiter.join(str(v) for v in value)
            elif isinstance(value, str):
                # Optionally normalize newlines
                if not preserve_newlines:
                    row[field] = value.replace("\n", " ").replace("\r", "")
                else:
                    row[field] = value
            else:
                row[field] = str(value)
        
        rows.append(row)
    
    return fieldnames, rows


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Convert idsignpost.json to CSV format."
    )
    parser.add_argument(
        "--input",
        default="idsignpost.json",
        help="Input JSON file (default: idsignpost.json)",
    )
    parser.add_argument(
        "--output",
        default="idsignpost.csv",
        help="Output CSV file (default: idsignpost.csv)",
    )
    parser.add_argument(
        "--delimiter",
        default=";",
        help="Delimiter for array fields (default: semicolon)",
    )
    parser.add_argument(
        "--no-newlines",
        action="store_true",
        help="Replace newlines with spaces in multi-line fields",
    )
    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    args = parse_args()
    
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file '{input_path}' not found.", file=sys.stderr)
        sys.exit(1)
    
    # Load JSON
    try:
        json_text = input_path.read_text(encoding="utf-8")
        entries = json.loads(json_text)
    except json.JSONDecodeError as e:
        print(f"Error: Failed to parse JSON: {e}", file=sys.stderr)
        sys.exit(1)
    
    if not isinstance(entries, list):
        print("Error: JSON root must be an array of entries.", file=sys.stderr)
        sys.exit(1)
    
    # Convert to CSV format
    fieldnames, rows = json_to_csv(
        entries,
        array_delimiter=args.delimiter,
        preserve_newlines=not args.no_newlines,
    )
    
    # Write CSV
    output_path = Path(args.output)
    try:
        with output_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        
        print(
            f"Wrote {len(rows)} entries to {output_path}",
            file=sys.stderr,
        )
    except IOError as e:
        print(f"Error: Failed to write CSV: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
