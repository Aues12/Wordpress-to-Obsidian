# WordPress → Obsidian — Progress & Development Notes

## 1. Purpose

This project aims to build a **modular content processing pipeline** that converts WordPress content into structured Obsidian-ready files.

Core idea:

`WordPress API → JSON → Process → Assemble → Write`

---

## 2. What Has Been Built So Far

### ✅ Import Layer

* `importers/wordpress_api.py`
* Fetches posts from WordPress REST API
* Handles pagination, retries, and category mapping
* Normalizes raw API data
* Exports to:

```text
data/imported.json
```

---

### ✅ Data Model Layer

* `core/models.py`

Two main objects:

#### `Post`

* Represents content during processing
* Contains:

  * title, content, date, slug
  * frontmatter (future use)
  * meta (raw + derived metadata)
  * source_path, source_type

#### `DocumentUnit`

* Represents write-ready output
* Contains:

  * filename
  * content
  * title
  * meta

---

### ✅ Source Layer

* `sources/imported_json.py`

Responsibilities:

* Reads `imported.json`
* Converts data into `Post` objects
* Preserves WordPress metadata inside `post.meta`

---

### ✅ Processing Layer

#### `processors/metadata.py`

Handles normalization:

* title fallback logic
* slug generation (with Turkish support)
* date normalization

Includes:

* `slugify()` (TR-aware)
* `normalize_metadata()`

---

#### `processors/pipeline.py`

Pipeline orchestration:

* Uses a **step list pattern**
* Applies transformations sequentially

Concept:

```text
Post → [step1 → step2 → step3] → Processed Post
```

Current pipeline:

* normalize_metadata

---

### ✅ Assembly Layer

* `assembler.py`

Implements:

* `per_post` mode

Logic:

```text
1 Post → 1 DocumentUnit
```

Each post becomes:

* one markdown file
* filename based on slug

---

### ✅ Writer Layer

* `writer.py`

Implements:

* markdown output (`.md`)

Features:

* creates output directory
* writes one file per unit
* optionally injects title as `# Heading`

---

### ✅ CLI / Entry Point

* `cli/main.py`

Pipeline execution:

```text
load → process → assemble → write
```

Includes:

* print-based logging
* execution time measurement

---

## 3. Architectural Principles (Established)

### 1. Clear Layer Separation

* Import → Source → Process → Assemble → Write

Each layer has a single responsibility.

---

### 2. Stable Data Contracts

* `Post` flows through processing
* `DocumentUnit` is used for output

---

### 3. Stateless Processing

* processors do not store data
* pure input → output transformations

---

### 4. Strategy-Based Output

* `assemble(mode=...)`
* `write(format=...)`

Allows flexible combinations.

---

### 5. Clean Public API Pattern

* `write()` → public
* `_write_markdown()` → internal

Encapsulation via naming convention.

---

### 6. Small First, Then Grow

* minimal working system first
* expansion later

---

## 4. What Works Now (First Milestone ✅)

End-to-end pipeline:

```text
WordPress API
    ↓
imported.json
    ↓
Post objects
    ↓
metadata normalization
    ↓
per_post assembly
    ↓
.md files (Obsidian-ready)
```

This is a **complete working system**.

---

## 5. Key Technical Learnings

* dataclasses (`Post`, `DocumentUnit`)
* `default_factory` for safe mutable defaults
* pipeline pattern (function list execution)
* separation of concerns in architecture
* slug generation (including Turkish normalization)
* session + retry handling in HTTP
* resource ownership (`session.close()` pattern)
* internal vs public functions (`_` prefix)

---

## 6. Next Development Steps

### 🔹 Processing Improvements

* `markdown_cleaner.py`
* `link_converter.py` (URL → wikilink)
* heading normalization
* anchor generation

---

### 🔹 Assembly Extensions

* `corpus` mode (single combined document)
* `book` mode (structured output)
* filtering (by date, tag, category)

---

### 🔹 Writer Extensions

* `docx` output
* JSON export (processed)
* frontmatter injection

---

### 🔹 Config System

* `config.yaml`
* CLI overrides
* pipeline configuration from config

---

### 🔹 CLI Improvements

* argparse integration
* commands:

  * import
  * build
  * preview

---

## 7. Future Vision

This project can evolve into:

* a **content processing engine**
* a **personal publishing pipeline**
* a **knowledge system builder (Obsidian-focused)**

Core strength:

👉 Same data → multiple outputs

---

## 8. Final Note

The system is already in a strong state:

* clean architecture
* modular design
* working pipeline

From here, development becomes **iterative refinement**, not reconstruction.

---

**Status:** Solid foundation established 🕊️
