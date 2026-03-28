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

### Clone the repository

```bash
git clone https://github.com/Aues12/WordPress-to-Obsidian.git
cd WordPress-to-Obsidian
```

### Create virtual environment:

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
* Write Markdown files to `output/`

Available CLI options:

* `--refresh` fetches fresh data from WordPress before building
* `--newest N` builds/writes only the newest `N` posts
* `--oldest N` builds/writes only the oldest `N` posts

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
* Markdown export
* Turkish-aware slug generation
* Basic metadata normalization

---

## Future Roadmap

### Processing

* Markdown cleaning
* Link conversion (URL → wikilinks)

### Assembly

* Corpus mode
* Book mode

### Writer

* Frontmatter support

### CLI

* Configurable output directory

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
