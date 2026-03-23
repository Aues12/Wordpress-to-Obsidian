# WordPress to Obsidian

This repository contains two main scripts for moving a WordPress blog into an Obsidian workflow:

1. `wordpress_exporter.py` exports WordPress posts as Markdown files with YAML frontmatter.
2. `url_to_wikilink.py` scans Markdown notes in an Obsidian vault and converts internal WordPress links into Obsidian wikilinks.

The link conversion step also uses `post_processing.py` to clean up a few Markdown edge cases after replacements are made.

## Quick Start and Installation

This is the exact end-to-end sequence for a first run:

1. Clone the repository:

   ```
   git clone https://github.com/Aues12/Wordpress-to-Obsidian.git
   cd Wordpress-to-Obsidian
   ```

2. (Optional but recommended) create and activate a virtual environment:

   ```
   python -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies:

   ```
   pip install -r requirements.txt
   ```

4. Configure the placeholder values in the source files:
   - In `wordpress_exporter.py`, set `SITE_URL` to your WordPress site URL.
   - In `url_to_wikilink.py`, set `SITE_URL` to the same site and `VAULT_PATH` to your Obsidian vault path.

5. Export your WordPress posts to Markdown:

   ```
   python wordpress_exporter.py
   ```

   Optional examples:

   ```
   python wordpress_exporter.py --newest 50
   python wordpress_exporter.py --oldest 50
   ```

6. Move or copy the exported Markdown files into your Obsidian vault if needed.

7. Run a dry run of the link conversion script to inspect what would change:

   ```
   python url_to_wikilink.py --vault "/path/to/your/Obsidian Vault" --site "https://example.com"
   ```

8. Apply the changes when the dry-run output looks correct:

   ```
   python url_to_wikilink.py --apply --vault "/path/to/your/Obsidian Vault" --site "https://example.com"
   ```

## Configuration requirements

Before running the scripts, update the placeholder configuration values in the source code:

### `wordpress_exporter.py`

- Set `SITE_URL` to your WordPress site URL.
- Optionally change `SAVE_DIR` if you want the exported Markdown files written to a different folder.

### `url_to_wikilink.py`

- Set `SITE_URL` to the same WordPress site URL used in the exporter.
- Set `VAULT_PATH` to the path of your Obsidian vault.

Both scripts ship with example placeholder values, so they will need to be customized before use.

## 1) Exporter module

I wrote this script to export my WordPress blog posts to the Obsidian note-taking app. Since Obsidian uses Markdown (`.md`) files, `wordpress_exporter.py` exports post data as **Markdown files** by using the **WordPress REST API**.

Each blog post is turned into an individual **Markdown (`.md`)** file.

The `wordpress_exporter.py` module also pulls metadata, including:

- title
- publication date
- last modified date
- slug
- canonical link
- categories

These values are stored in the **YAML frontmatter** of each Markdown file. If you have different preferences, you can change these parameters in the source code before using the script.

By default, the script pulls all posts that are available.

To pull a limited number of the newest or oldest posts, you can use command-line arguments such as:

```
--newest N
--oldest N
```

Replace `N` with the desired number of posts.

Example:

```
python wordpress_exporter.py --newest 50
```

This command exports the 50 newest posts.

---

## 2) Text-processor (url to wikilink) module

I also use URL links often in my writing. These links almost always refer to another blog post. I wanted to use the wikilink system available in **Obsidian**, which allows different notes to connect to one another.

For this purpose, the `url_to_wikilink.py` module scans Markdown files in the vault and converts internal WordPress URL links into **Obsidian wikilinks**. This allows cross-referencing inside the Obsidian platform.

The script scans Markdown files in the vault and converts links such as:
```
[Post Title](https://example.com/post-title/)
```
into:
```
[[Post Title]]
```
If the link text differs from the actual post title, the script creates a wikilink with an alias:
```
[Short Quote](https://example.com/post-title/)
```
becomes:
```
[[Post Title|Short Quote]]
```
This enables internal cross-referencing between notes inside Obsidian while preserving the original link text when necessary.

This script runs in **dry-run mode** by default, meaning it does not make any actual changes and only reports statistics about the detected links.

### Command-line flags

`url_to_wikilink.py` supports the following command-line flags:

- `--apply`  
  Writes the converted content back to the Markdown files. Without this flag, the script stays in dry-run mode.

- `--backup`  
  Creates a `.bak` backup file before writing changes.

- `--vault PATH`  
  Overrides the default `VAULT_PATH` value in the script and tells the tool which Obsidian vault to scan.

- `--site URL`  
  Overrides the default `SITE_URL` value in the script and tells the tool which domain should count as an internal WordPress link.

Examples:

You can use the `--apply` command-line parameter by itself to apply the changes:

```
python url_to_wikilink.py --apply
```

Dry run with explicit overrides:

```
python url_to_wikilink.py --vault "/path/to/vault" --site "https://example.com"
```

Apply changes and create backups:

```
python url_to_wikilink.py --apply --backup --vault "/path/to/vault" --site "https://example.com"
```

### How matching works

The wikilink conversion step builds a `slug -> title` map from the YAML frontmatter in your Markdown notes.

- The script looks for `slug` and `title` fields in each note's frontmatter.
- If a note has a `slug` but no `title`, the filename stem is used as a fallback title.
- Internal WordPress links are matched by extracting the final slug from the URL path and looking it up in that map.
- Only links in the **body** of the Markdown file are rewritten; frontmatter is left unchanged.

Links are intentionally skipped in these cases:

- the link points to a different domain
- the link is external
- the link is a `mailto:`, `tel:`, or `#fragment` link
- the link uses a query-style WordPress URL such as `?p=123`
- no note in the vault has a matching `slug`

Because of this, successful matching depends on your notes already containing usable `slug` values in frontmatter.

### Cache and troubleshooting

To avoid rebuilding the slug map on every run, `url_to_wikilink.py` stores a cache file at:

```
.cache/slug_to_title_map.json
```

This file is created inside the vault directory.

If the script is not matching links you expect it to match:

1. Confirm that the notes in your vault contain correct `slug` and `title` frontmatter.
2. Confirm that `--site` or `SITE_URL` matches the same domain used in your Markdown links.
3. Check whether the links are query-style URLs such as `?p=123`, which are intentionally skipped.
4. Delete `.cache/slug_to_title_map.json` and run the script again if your slugs or titles changed after a previous run.
