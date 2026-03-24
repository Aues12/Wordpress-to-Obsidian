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
wp_obsidian/
├─ cli/
│  └─ main.py
├─ core/
│  ├─ models.py
│  ├─ config.py
│  └─ utils.py
├─ data/
│  └─ imported.json
├─ importers/
│  └─ wordpress_api.py
├─ sources/
│  └─ imported_json.py
├─ processors/
│  ├─ metadata.py
│  └─ pipeline.py
├─ assembler.py
├─ writer.py
```

---

## Installation

### Clone the repository

```bash
git clone https://github.com/Aues12/WordPress-to-Obsidian.git
cd wp-to-obsidian
```

### Install dependencies

```bash
pip install -r requirements.txt
```

Dependencies:

* requests

```bash
pip install -r requirements.txt
```

Dependencies:

* requests

---

## Usage

### 1. Fetch data from WordPress

```python
from importers.wordpress_api import export_posts_to_json

export_posts_to_json(
    base_url="https://your-site.com",
    output_file="data/imported.json"
)
```

---

### 2. Run the pipeline

```bash
python -m cli.main
```

This will:

* Load JSON
* Process posts
* Assemble output
* Write Markdown files to `output/`

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

* DOCX export
* Frontmatter support

### CLI

* Argument parsing
* Config integration

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
