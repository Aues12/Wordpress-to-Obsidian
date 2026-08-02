# WordPress to Obsidian

A modular Python library for converting WordPress content into structured, Obsidian-ready markdown files.

---

## Overview

This project provides a clean and extensible pipeline to transform content from WordPress into local files suitable for knowledge management systems like Obsidian.

Core pipeline:

```
WordPress API → JSON → Process → Assemble → Write
```

---

## Features

* Fetch posts from WordPress REST API
* Normalize and process content
* Convert posts into structured objects
* Export as Markdown files
* Build output in `per_post` or `book` mode
* Optional YAML frontmatter generation
* Modular architecture (easy to extend)

---

## Project Structure

```
Wordpress-to-Obsidian/
├─ cli/
│  └─ main.py
├─ config/
│  └─ loader.py
├─ core/
│  └─ models.py
├─ data/
│  └─ imported.json
├─ importer/
│  └─ wordpress_api.py
├─ processors/
│  ├─ metadata.py
│  └─ pipeline.py
├─ sources/
│  └─ imported_json.py
├─ assembler.py
├─ config.json
└─ writer.py
```

---

## Installation

Requires Python 3.9 or newer.

### Clone the repository

```bash
git clone https://github.com/Aues12/WordPress-to-Obsidian.git
cd WordPress-to-Obsidian
```

### Quickstart

(Optional but recommended) Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate
```

### Install dependencies

```bash
pip install -r requirements.txt
```

Dependencies:

* requests
* PyYAML
* markdownify

For running tests:

* pytest

---

## Usage

### 1. Fetch data from WordPress

```python
from importer.wordpress_api import export_posts_to_json

export_posts_to_json(
    base_url="https://your-site.com",
    output_file="data/imported.json"
)
```

Use this manual fetch step when you want to generate or refresh `data/imported.json`
outside the CLI workflow. In normal usage, `python -m cli.main` already checks for the
JSON file and fetches it automatically when needed, or when you pass `--refresh`.

---

### 2. Configure the CLI

Create/edit the `config.json` file in the project root:

```json
{
  "wordpress": {
    "base_url": "https://your-site.com"
  },
  "paths": {
    "json_file": "data/imported.json",
    "output_dir": "output"
  },
  "frontmatter": {
    "include_frontmatter": false,
    "fields": [
      "title",
      "date",
      "modified",
      "slug",
      "category_names"
    ]
  }
}
```

---

### 3. Run the pipeline

```bash
python -m cli.main
```

This will:

* Load `config.json`
* Reuse existing JSON or fetch fresh data from WordPress
* Load JSON
* Process posts
* Assemble output
* Write Markdown files to the configured output directory

Available CLI options:

* `--refresh` fetches fresh data from WordPress before building
* `--order {newest,oldest}` controls post selection order before limiting
* `--write_order {newest,oldest}` controls ordering inside the written output
* `--limit N` limits the number of posts to build
* `--mode {per_post,book}` switches between one-file-per-post and combined book output
* `--frontmatter` includes YAML frontmatter in the assembled output

Examples:

```bash
# Build the 10 newest posts as individual markdown files
python -m cli.main --order newest --limit 10 --mode per_post

# Build a single combined book in oldest-to-newest order
python -m cli.main --order newest --limit 20 --write_order oldest --mode book
```

---

## Testing

Run the test suite with:

```bash
python -m pytest
```

If `pytest` is not installed yet, install it with:

```bash
pip install pytest
```

---

## Core Concepts

### Post

Represents content during processing.

### DocumentUnit

Represents write-ready output.

### Pipeline

A sequence of transformations applied to each post.

### Assembler

Defines how posts are grouped (e.g., per_post, corpus).

### Writer

Handles output format (e.g., markdown, docx).

---

## Current Capabilities

* per_post assembly
* Book assembly
* Markdown export
* Turkish-aware slug generation
* Basic metadata normalization
* HTML to Markdown conversion
* Optional YAML frontmatter
* Config-driven output directory

---

## Future Roadmap

### Processing

* Markdown cleaning
* Link conversion (URL → wikilinks)

### Assembly

* Corpus mode

### Writer

* Additional output formats

---

## Design Principles

* Modular architecture
* Clear separation of concerns
* Stateless processing
* Extensibility over complexity

---

## Example Output

```
output/
├─ post-1.md
├─ post-2.md
└─ post-3.md
```

---

## License

MIT

---

## Final Note

This project is designed as a foundation for building flexible content pipelines and personal knowledge systems.
