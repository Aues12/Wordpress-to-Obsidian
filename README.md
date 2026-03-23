# WordPress to Obsidian

This repository contains 2 modules. The first is an exporter that pulls posts from a **WordPress** blog and saves them in **Markdown** format. The second is a text-processing module that converts **URL links** into **Obsidian-style wikilinks**.

## Installation

Clone the repository:

```
git clone https://github.com/Aues12/Wordpress-to-Obsidian.git
cd Wordpress-to-Obsidian
```

(Optional but recommended) create a virtual environment:

```
python -m venv venv
source venv/bin/activate
```

Install dependencies:

```
pip install -r requirements.txt
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

You can use the `--apply` command-line parameter to apply the changes:

```
python url_to_wikilink.py --apply
```
