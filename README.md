# FSC Legacy - Biodiversity ID Signpost Extractor

Convert legacy FSC idsignpost HTML pages into a single, searchable Markdown catalog of biodiversity identification resources for Britain and Ireland.

The legacy HTML pages can be found at [https://www.fscbiodiversity.uk/idsignpost](<https://www.fscbiodiversity.uk/idsignpost>)

## Overview

This repository exists to transform legacy idsignpost HTML pages into a unified Markdown catalog. The extraction script parses HTML metadata and content from individual resource pages, producing clean Markdown with standardized formatting for identification guides, keys, and field resources covering British and Irish wildlife and flora.

## What `extract_idsignpost.py` Does

The [scripts/extract_idsignpost.py](scripts/extract_idsignpost.py) script is the core tool that:

1. **Parses HTML files** from the `idsignpost/` directory
2. **Extracts structured metadata** from `<div id="main">` blocks including:
   - Title (from `<h1>` tags)
   - Submission metadata (author and date)
   - Field data (Description, Author(s), Free status, Availability, Web links, Keywords, etc.)
3. **Converts to clean Markdown** using BeautifulSoup and Markdownify
4. **Normalizes formatting and links**:
   - Repairs URLs split across HTML boundaries (e.g., `</a>@N07/path`)
   - Decodes percent-encoded characters in URLs (`%20` → space, etc.)
   - Wraps all links in angle brackets for proper Markdown syntax: `[url](<url>)`
   - Cleans up HTML entities (double-unescapes)
   - Removes excess whitespace
   - Adds blank line after headings for readability
   - Handles multi-line field values with proper indentation
   - Formats dates to ISO format (YYYY-MM-DDTHH:MM:SS)
5. **Outputs a unified markdown file** with each resource as a `##` heading followed by bullet-point metadata

### Key Features

- **Smart field detection**: Maps CSS classes like `field-name-field-description` to friendly labels using [`FIELD_LABELS`](scripts/extract_idsignpost.py#L18-L26)
- **Text cleaning**: [clean_text](scripts/extract_idsignpost.py#L30-L38) double-unescapes HTML entities, normalizes line breaks, and removes excess whitespace
- **Label derivation**: [derive_label](scripts/extract_idsignpost.py#L108-L127) extracts field labels from both explicit `.field-label` nodes and CSS class names
- **Split URL fixing**: [fix_split_urls](scripts/extract_idsignpost.py#L40-L60) repairs URLs that are split across HTML link elements and following text (e.g., when `@N07/collections/...` appears outside the `<a>` tag)
- **URL normalization**: [normalize_markdown_links](scripts/extract_idsignpost.py#L76-L99) decodes percent-encoded characters (`%20` → space, etc.), and wraps all URLs in angle brackets for proper Markdown formatting
- **Nested list handling**: [render_markdown](scripts/extract_idsignpost.py#L144-L177) intelligently formats single-line vs. multi-line values, including nested bullets for multi-value fields
- **Date parsing**: [format_submitted](scripts/extract_idsignpost.py#L191-L206) and [to_iso_datetime](scripts/extract_idsignpost.py#L209-L217) convert "Submitted by X on Day, DD/MM/YYYY - HH:MM" to structured format
- **Selective processing**: [gather_files](scripts/extract_idsignpost.py#L180-L188) globs `*.html` files, excluding `about.html`

## Installation

This project uses [uv](https://docs.astral.sh/uv/) for dependency management.

```bash
# Clone the repository
git clone <repo-url>
cd FSCLegacy-fscbiodiversity.uk-idsignpost

# Install dependencies with uv (recommended)
uv sync
```

Dependencies (from [pyproject.toml](pyproject.toml) and [uv.lock](uv.lock)):

- `beautifulsoup4>=4.12.3` - HTML parsing
- `markdownify>=0.12.1` - HTML to Markdown conversion

## Usage

All scripts are run using `uv run python scripts/<script-name>.py`.

### Extract HTML to Markdown

#### Full Extraction

Regenerate the complete Markdown catalog from all HTML files:

```bash
uv run python scripts/extract_idsignpost.py --output idsignpost.md
```

#### Test Mode

Process a sample of files (default 5) to verify parsing:

```bash
uv run python scripts/extract_idsignpost.py --test 5
```

#### Custom Path

Specify a different HTML directory:

```bash
uv run python scripts/extract_idsignpost.py --path ./my-html-files --output output.md
```

#### Command-Line Options

- `--path`: Directory containing idsignpost HTML files (default: `./idsignpost`)
- `--test [N]`: Process only N files for testing (default: 5)
- `--output`: Write output to file instead of stdout

### Convert Markdown to JSON

The [scripts/md_to_json.py](scripts/md_to_json.py) script parses the generated Markdown catalog into structured JSON format for programmatic access. It:

1. **Parses Markdown entries** by splitting on `##` heading delimiters
2. **Distinguishes field types**:
   - Single-line fields: `Title: value`
   - Multi-line fields: Values spanning multiple indented lines (joined with newlines)
   - Multi-value fields: Nested bullet lists, converted to JSON arrays
3. **Adds filename field**: Each entry includes the source HTML filename
4. **Preserves text formatting**: Maintains paragraph breaks and structure in multi-line fields
5. **Outputs clean JSON**: UTF-8 encoded with configurable indentation

#### Usage

Convert the markdown catalog to JSON format:

```bash
# Output to stdout
uv run python scripts/md_to_json.py

# Save to file
uv run python scripts/md_to_json.py --output idsignpost.json

# Pretty-print with sorted keys
uv run python scripts/md_to_json.py --output idsignpost.json --pretty

# Compact JSON (no indentation)
uv run python scripts/md_to_json.py --output idsignpost.json --indent 0
```

#### Command-Line Options

- `--input`: Input markdown file (default: `idsignpost.md`)
- `--output`: Output JSON file (if not specified, outputs to stdout)
- `--indent`: JSON indentation level (default: 2, use 0 for compact)
- `--pretty`: Pretty-print JSON with sorted keys

#### JSON Output Format

Each entry in the JSON array contains:

```json
{
  "filename": "resource-name.html",
  "Title": "Resource Title",
  "Submitted": "author_name; 2015-06-09T17:02:00",
  "Description": "Detailed description text...",
  "Author(s)": "Author Name(s)",
  "Free": "Yes",
  "Available as": ["Online", "PDF"],
  "Web link": "https://example.com/resource",
  "Keywords": "keyword1 keyword2 keyword3"
}
```

Multi-value fields are arrays, single-line and multi-line fields are strings.

### Convert JSON to CSV

The [scripts/json_to_csv.py](scripts/json_to_csv.py) script converts the JSON catalog to CSV (comma-separated values) format for use in spreadsheets, databases, and data analysis tools. It:

1. **Reads JSON entries** from the structured JSON catalog
2. **Maintains canonical field order**: Columns appear in the same order as the original markdown format (filename, Title, Submitted, Description, etc.)
3. **Normalizes field structure**: Ensures all entries have consistent columns
4. **Handles field types**:
   - Single-line fields: Output as-is
   - Multi-line fields: Preserved with newlines (or converted to spaces with `--no-newlines`)
   - Array fields: Joined with a configurable delimiter (default: semicolon)
5. **Produces RFC 4180 compliant CSV**: Proper escaping, quoted fields, UTF-8 encoding
6. **Flexible output**: Command-line options for customization

#### Usage

Convert the JSON catalog to CSV:

```bash
# Basic conversion (output to idsignpost.csv)
uv run python scripts/json_to_csv.py

# Specify custom input/output paths
uv run python scripts/json_to_csv.py --input my-catalog.json --output my-catalog.csv

# Use pipe character as array delimiter instead of semicolon
uv run python scripts/json_to_csv.py --output idsignpost.csv --delimiter "|"

# Replace newlines with spaces for single-line fields
uv run python scripts/json_to_csv.py --output idsignpost.csv --no-newlines
```

#### Command-Line Options

- `--input`: Input JSON file (default: `idsignpost.json`)
- `--output`: Output CSV file (default: `idsignpost.csv`)
- `--delimiter`: Separator for array fields (default: `;`)
- `--no-newlines`: Replace newlines with spaces in multi-line fields

#### CSV Output Format

The CSV file has columns matching the original markdown field order:

```
filename,Title,Submitted,Description,Author(s),Free,Available as,Web link,Keywords,...
resource-name.html,Resource Title,author; 2015-06-09T17:02:00,Description text,Author Name,Yes,Online;PDF,https://example.com,keyword1;keyword2
```

**Column order**: Fields appear in the canonical order (filename, Title, Submitted, Description, Author(s), Free, Available as, Web link, Additional web link, Keywords, Major group(s), Body), followed by any additional fields alphabetically.

**Field handling**:
- Single-line fields: Direct value
- Multi-line fields: Newlines preserved (or space-separated with `--no-newlines`)
- Array fields: Values joined by chosen delimiter (e.g., `Online;PDF;Publication`)

## Project Structure

```plaintext
├── idsignpost/              # Source HTML files (legacy FSC pages)
├── idsignpost.md            # Generated Markdown catalog
├── idsignpost.json          # Generated JSON catalog
├── idsignpost.csv           # Generated CSV catalog
├── scripts/                 # Python scripts
│   ├── extract_idsignpost.py  # HTML to Markdown converter
│   ├── md_to_json.py          # Markdown to JSON converter
│   └── json_to_csv.py         # JSON to CSV converter
├── pyproject.toml           # Python project configuration
├── uv.lock                  # Locked dependencies
└── README.md                # This file
```

## Output Format

Each resource entry follows this structure:

```markdown
## filename.html

- Title: Resource Title
- Submitted: author_name; 2015-06-09T17:02:00
- Description: Detailed description text
- Author(s): Author Name(s)
- Free: Yes/No
- Available as: Publication, Online, PDF
- Web link: [https://example.com/resource](<https://example.com/resource>)
- Keywords: keyword1 keyword2 keyword3
```

**Link Format**: All links are normalized to the format `[url](<url>)` where:
- Display text is the decoded URL (with `%20` and other encodings removed)
- URL target is also decoded and wrapped in angle brackets
- This ensures URLs are human-readable in both the Markdown source and rendered output

Multi-line field values are indented:

```markdown
- Description:
  First paragraph of description.
  
  Second paragraph of description.
```

Multi-value fields use nested bullets:

```markdown
- Available as:
  - Online
  - PDF
  - Publication
```

## Workflow

1. Place HTML files in the `idsignpost/` directory
2. Run `uv run python scripts/extract_idsignpost.py --test` to verify parsing on a sample
3. Run `uv run python scripts/extract_idsignpost.py --output idsignpost.md` for full extraction
4. Optionally run `uv run python scripts/md_to_json.py --output idsignpost.json --pretty` to generate JSON
5. Optionally run `uv run python scripts/json_to_csv.py --output idsignpost.csv` to generate CSV
6. Review and commit the updated files

## Legacy Context

This is a preservation project for the Field Studies Council (FSC) biodiversity identification resources website. The original HTML pages contained metadata about identification guides, keys, and field resources for British and Irish wildlife covering:

- Invertebrates (insects, spiders, crustaceans, molluscs)
- Vertebrates (mammals, birds, reptiles, amphibians, fish)
- Plants (wildflowers, trees, bryophytes, algae, fungi)
- Marine life (seaweeds, hydroids, barnacles)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

**Software**: The extraction and conversion scripts are freely available under the MIT License.

**Data and Content**: The biodiversity identification resource metadata in the catalog files is sourced from the Field Studies Council's legacy website and various contributors. This catalog data is provided for archival and reference purposes. Users should respect the intellectual property rights of original authors and publishers when using the resource information.
