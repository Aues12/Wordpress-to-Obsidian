"""url_to_wikilink.py

Phase 2 — Apply Link Conversion (WordPress URL → Obsidian wikilink)
-----------------------------------------------------------------
This script scans Markdown files inside an Obsidian vault and converts
internal WordPress links in the BODY section into Obsidian wikilinks.

Goal
- [text](https://example.com/.../slug/)  →  [[Real Title]]
- If the link text differs from the real title (short quote, abbreviation, etc.), use an alias:
    [[Real Title|Displayed Text]]
- Preserve simple emphasis (italics/bold) without altering the original formatting:
    [*Text*](url) → *[[Real Title|Text]]*

Notes
- Only links that belong to SITE_URL are converted.
- External links are left untouched.
- Frontmatter is not modified; only the body is rewritten.
- By default, the script runs in DRY-RUN mode (no file writes).

Requirements
  pip install pyyaml

Usage
  1) Fill the CONFIG section
  2) Dry-run:
     python url_to_wikilink.py
  3) Apply changes:
     python url_to_wikilink.py --apply
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Tuple
from urllib.parse import urlparse, parse_qs
import argparse
import re
import sys

import yaml


# ======================================================
# CONFIG
# ======================================================

# Replace with your WordPress site URL (used to detect internal links)
SITE_URL = "https://example.com"

# Replace with your Obsidian vault path
VAULT_PATH = Path("/path/to/your/Obsidian Vault")


# ======================================================
# REGEX
# ======================================================

# Markdown link pattern: [text](url)
MD_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


# ======================================================
# DATA MODELS
# ======================================================


@dataclass
class ApplyStats:
    """Aggregated stats for a full vault run."""

    files_scanned: int = 0
    files_changed: int = 0
    links_found_internal: int = 0
    links_converted: int = 0
    links_unmatched: int = 0
    unmatched_examples: List[str] = None


# ======================================================
# HELPERS
# ======================================================


def normalize_netloc(netloc: str) -> str:
    """Normalize a hostname/netloc for comparison (lowercase, strip 'www.')."""

    netloc = (netloc or "").strip().lower()
    return netloc[4:] if netloc.startswith("www.") else netloc



def to_absolute_url(possibly_relative_url: str, site_url: str) -> str:
    """Convert a relative URL to an absolute URL using the provided site_url."""

    u = (possibly_relative_url or "").strip()

    # Ignore non-http links
    if u.startswith(("mailto:", "tel:", "#")):
        return u

    # Scheme-relative URLs: //example.com/path
    if u.startswith("//"):
        scheme = urlparse(site_url).scheme or "https"
        return f"{scheme}:{u}"

    # Already absolute
    if "://" in u:
        return u

    # Relative to site
    return site_url.rstrip("/") + "/" + u.lstrip("/")



def iter_markdown_files(vault_path: Path) -> Iterator[Path]:
    """Yield all Markdown files under the vault path recursively."""

    yield from vault_path.rglob("*.md")



def read_text(path: Path) -> str:
    """Read text as UTF-8, ignoring decode errors."""

    return path.read_text(encoding="utf-8", errors="ignore")



def write_text(path: Path, text: str) -> None:
    """Write text as UTF-8."""

    path.write_text(text, encoding="utf-8")



def parse_frontmatter(text: str) -> Tuple[dict, int]:
    """Parse YAML frontmatter if present.

    Returns:
        (frontmatter_dict, body_start_index)

    If no frontmatter is present, returns ({}, 0).
    """

    if not text.startswith("---"):
        return {}, 0

    end = text.find("\n---", 3)
    if end == -1:
        return {}, 0

    fm_block = text[3:end].strip("\n")
    try:
        data = yaml.safe_load(fm_block) or {}
        if not isinstance(data, dict):
            return {}, 0

        end_line = text.find("\n", end + 1)
        body_start = end_line + 1 if end_line != -1 else end + 4
        return data, body_start
    except Exception:
        return {}, 0



def build_slug_to_title_map(vault_path: Path) -> Dict[str, str]:
    """Build a slug->title map from Markdown frontmatter in the vault."""

    slug_to_title: Dict[str, str] = {}

    for p in iter_markdown_files(vault_path):
        text = read_text(p)
        fm, _ = parse_frontmatter(text)
        slug = fm.get("slug")
        title = fm.get("title")

        if isinstance(slug, str) and slug.strip():
            slug = slug.strip()

            # If no explicit title exists, fall back to filename stem
            if not isinstance(title, str) or not title.strip():
                title = p.stem

            slug_to_title[slug] = title.strip()

    return slug_to_title



def extract_internal_slug(url: str, site_url: str) -> Optional[str]:
    """Extract the slug from an internal WordPress URL.

    Returns the last path segment if the URL belongs to site_url, otherwise None.

    Examples:
      /2026/02/21/some-post/ -> some-post
      URLs with ?p=123 are ignored (return None)
    """

    abs_url = to_absolute_url(url, site_url)

    if abs_url.startswith(("mailto:", "tel:", "#")):
        return None

    parsed = urlparse(abs_url)

    if normalize_netloc(parsed.netloc) != normalize_netloc(urlparse(site_url).netloc):
        return None

    q = parse_qs(parsed.query)
    if "p" in q:
        return None

    parts = [p for p in parsed.path.strip("/").split("/") if p]
    if not parts:
        return None

    return parts[-1]


# ======================================================
# Phase 2: Link Conversion
# ======================================================


def split_emphasis(text: str) -> Tuple[str, str, str]:
    """Split simple full-wrap emphasis (minimal preservation).

    Examples:
      "*Text*" -> ("*", "Text", "*")
      "**Text**" -> ("**", "Text", "**")
      "_Text_" -> ("_", "Text", "_")

    If there is no full-wrap emphasis, returns ("", text, "").

    Note: This is intentionally minimal and does not attempt to handle nested cases.
    """

    s = text
    for mark in ("**", "__", "*", "_"):
        if s.startswith(mark) and s.endswith(mark) and len(s) >= 2 * len(mark) + 1:
            return mark, s[len(mark) : -len(mark)], mark
    return "", text, ""



def parse_wikilink(core: str) -> Optional[Tuple[str, Optional[str]]]:
    """Parse [[Target]] or [[Target|Alias]] and return (target, alias?)."""

    t = core.strip()
    if not (t.startswith("[[") and t.endswith("]]")):
        return None

    inside = t[2:-2]
    if "|" in inside:
        target, alias = inside.split("|", 1)
        return target.strip(), alias.strip()
    return inside.strip(), None



def make_wikilink(real_title: str, display_text: str) -> str:
    """Create the most compact wikilink for the given title and display text.

    - If display_text matches the title: [[Title]]
    - Otherwise: [[Title|Display Text]]
    """

    display = (display_text or "").strip()

    if not display or display == real_title:
        return f"[[{real_title}]]"

    return f"[[{real_title}|{display}]]"


# ======================================================
# CORE: REWRITE BODY
# ======================================================


def rewrite_body(body: str, slug_map: Dict[str, str], site_url: str) -> Tuple[str, int, int, int]:
    """Rewrite Markdown body content by converting internal WP links to wikilinks.

    Conversion happens only when:
    - the URL is internal to site_url, and
    - the extracted slug exists in slug_map.

    Returns:
        (new_body, internal_found, converted, unmatched)
    """

    internal_found = 0
    converted = 0
    unmatched = 0

    def repl(m: re.Match) -> str:
        """Process a single [text](url) match."""

        nonlocal internal_found, converted, unmatched

        link_text_raw = m.group(1)
        url = m.group(2).strip()

        # 1) Extract internal slug (if not internal, keep original markdown)
        slug = extract_internal_slug(url, site_url)
        if slug is None:
            return m.group(0)

        internal_found += 1

        # 2) Resolve slug -> real title
        real_title = slug_map.get(slug)
        if real_title is None:
            unmatched += 1
            return m.group(0)

        # 3) Preserve simple emphasis wrapper
        pre, core, suf = split_emphasis(link_text_raw)

        # 4) If core is already a wikilink, reuse its display text
        wk = parse_wikilink(core)
        if wk is not None:
            _target, alias = wk
            display = alias if alias is not None else _target
            new_wk = make_wikilink(real_title, display)
            converted += 1
            return f"{pre}{new_wk}{suf}"

        # 5) Normal case: use the link text as the display text
        new_wk = make_wikilink(real_title, core)
        converted += 1
        return f"{pre}{new_wk}{suf}"

    new_body = MD_LINK_RE.sub(repl, body)
    return new_body, internal_found, converted, unmatched


# ======================================================
# APPLY
# ======================================================


def process_vault(vault_path: Path, site_url: str, apply: bool, backups: bool) -> ApplyStats:
    """Scan the vault and apply conversions file-by-file."""

    stats = ApplyStats(unmatched_examples=[])
    slug_map = build_slug_to_title_map(vault_path)

    if not slug_map:
        print("Warning: slug->title map is empty. Frontmatter may be missing the 'slug' field.")

    for md_path in iter_markdown_files(vault_path):
        stats.files_scanned += 1

        original = read_text(md_path)
        fm, body_start = parse_frontmatter(original)
        body = original[body_start:] if body_start > 0 else original

        new_body, internal_found, converted, unmatched = rewrite_body(body, slug_map, site_url)

        # Collect a few unmatched examples (up to 10) for debugging
        if unmatched > 0 and len(stats.unmatched_examples) < 10:
            for m in MD_LINK_RE.finditer(body):
                url = m.group(2).strip()
                slug = extract_internal_slug(url, site_url)
                if slug and slug not in slug_map:
                    rel = md_path.relative_to(vault_path)
                    example = f"{rel} -> slug: {slug}"
                    if example not in stats.unmatched_examples:
                        stats.unmatched_examples.append(example)
                        if len(stats.unmatched_examples) >= 10:
                            break

        stats.links_found_internal += internal_found
        stats.links_converted += converted
        stats.links_unmatched += unmatched

        if new_body != body:
            stats.files_changed += 1

            if apply:
                if backups:
                    backup_path = md_path.with_suffix(md_path.suffix + ".bak")
                    if not backup_path.exists():
                        write_text(backup_path, original)

                updated = (original[:body_start] + new_body) if body_start > 0 else new_body
                write_text(md_path, updated)

    return stats



def print_stats(stats: ApplyStats, apply: bool) -> None:
    """Print a summary report."""

    mode = "APPLY" if apply else "DRY-RUN"
    print(f"[{mode}] Files scanned: {stats.files_scanned}")
    print(f"[{mode}] Files changed: {stats.files_changed}")
    print()
    print("Links")
    print(f"- Internal WP links found: {stats.links_found_internal}")
    print(f"- Converted to wikilinks: {stats.links_converted}")
    print(f"- Unmatched internal slugs: {stats.links_unmatched}")

    if stats.unmatched_examples:
        print("Unmatched examples (max 10):")
        for ex in stats.unmatched_examples:
            print(f"  - {ex}")


# ======================================================
# CLI / ENTRY
# ======================================================


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert WP URLs to Obsidian wikilinks")
    parser.add_argument("--apply", action="store_true", help="Write changes to files")
    parser.add_argument("--backup", action="store_true", help="Create .bak backups")
    parser.add_argument("--vault", type=str, default=str(VAULT_PATH), help="Path to the Obsidian vault")
    parser.add_argument("--site", type=str, default=SITE_URL, help="Site URL (used to detect internal links)")

    args = parser.parse_args()

    vault = Path(args.vault)
    if not vault.exists():
        print(f"Vault not found: {vault}")
        sys.exit(1)

    apply = bool(args.apply)
    backups = bool(args.backup)

    stats = process_vault(vault, args.site, apply=apply, backups=backups)
    print_stats(stats, apply=apply)


if __name__ == "__main__":
    main()
