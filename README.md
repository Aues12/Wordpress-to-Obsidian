# WordPress → Obsidian Tools

There currently 2 modules in this library. The first is an exporter module that pulls posts from a WordPress blog, and the second is a text-processor module that converts URL links to Obsidian-style wikilinks. Further explanation is given below.

## 1) Exporter

I wrote this script to export my WordPress blog posts to Obsidian note taking app. Since Obsidian uses Markdown (.md) file format, wordpress_exporter.py exports the post data as Markdown files – using the WordPress REST API.

Each blog post is turn into an individual Markdown (.md) file.

wordpress_exporter.py module also pulls some metadata. Which are:

- title
- publication date
- last modified date
- slug
- canonical link
- categories

These values are stored in the YAML frontmatter of each Markdown file. If you have different preference, you can change these parameters from source code before using it.

By default, the script pulls all posts that are available.

To pull limited amount of newest or oldest posts, you can use command-line arguments. Such as:

```
--newest N
--oldest N
```

Replace N with desired amount of posts.

Example:

```
python wordpress_exporter.py --newest 50
```

This command exports the 50 newest posts.

---

## 2) Text-processor

I also use URL links a lot in my writings. These almost always refer to a link of another blog post. I wanted to utilize the wikilink system available in Obsidian, which is a feature that allows connecting different Obsidian notes.

For this purpose, url_to_wikilink.py module scans the .md files and converts URL links to Obsidian wikilink format. This allows cross-referencing and linkage inside Obsidian platform.

The script scans Markdown files in the vault and converts links such as:

```
[Example](https://example.com/my-post/)
```

into:

```
[[My Post]]
```

This enables internal cross-referencing between notes inside Obsidian.

This script runs in dry-run mode as default, meaning it doesn’t make any actual changes but only reports statistics about the detected links.

You can use “--apply” parameter in command-line to apply the changes:

```
python url_to_wikilink.py --apply
```
