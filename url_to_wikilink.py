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
import json

from post_processing import cleanup_markdown_after_wikilinks


# ======================================================
# CONFIG
# ======================================================

# Replace with your WordPress site URL (used to detect internal links)
SITE_URL = "https://example.com"
# Replace with your Obsidian vault path
VAULT_PATH = Path("/path/to/your/Obsidian Vault")

MAKE_BACKUPS = False
DRY_RUN_DEFAULT = True


# ======================================================
# REGEX
# ======================================================

# Markdown link: [text](url)
MD_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


# ======================================================
# DATA MODELS
# ======================================================

@dataclass
class ApplyStats:
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
    netloc = (netloc or "").strip().lower()
    return netloc[4:] if netloc.startswith("www.") else netloc



def to_absolute_url(possibly_relative_url: str, site_url: str) -> str:
    u = (possibly_relative_url or "").strip()

    if u.startswith(("mailto:", "tel:", "#")):
        return u

    if u.startswith("//"):
        scheme = urlparse(site_url).scheme or "https"
        return f"{scheme}:{u}"

    if "://" in u:
        return u

    return site_url.rstrip("/") + "/" + u.lstrip("/")



def iter_markdown_files(vault_path: Path) -> Iterator[Path]:
    yield from vault_path.rglob("*.md")



def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")



def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")



def parse_frontmatter(text: str) -> Tuple[dict, int]:
    """Frontmatter varsa (--- ... ---) dict ve body başlangıç index'i döndürür.

    Yoksa ({}, 0) döner.
    """

    if not text.startswith("---"):
        return {}, 0

    end = text.find("\n---", 3)
    if end == -1:
        return {}, 0

    front_matter_block = text[3:end].strip("\n")
    try:
        data = yaml.safe_load(front_matter_block) or {}
        if not isinstance(data, dict):
            return {}, 0

        end_line = text.find("\n", end + 1)
        body_start = end_line + 1 if end_line != -1 else end + 4
        return data, body_start
    except Exception:
        return {}, 0



def build_slug_to_title_map(vault_path: Path) -> Dict[str, str]:
    """Vault'taki frontmatter'lardan slug->title map üretir."""
    slug_to_title: Dict[str, str] = {}

    for p in iter_markdown_files(vault_path):
        text = read_text(p)
        front_matter, _ = parse_frontmatter(text)
        slug = front_matter.get("slug")
        title = front_matter.get("title")

        if isinstance(slug, str) and slug.strip():
            slug = slug.strip()

            if not isinstance(title, str) or not title.strip():
                title = p.stem

            slug_to_title[slug] = title.strip()

    return slug_to_title


def save_slug_to_title_map(slug_to_title: Dict[str, str], output_path: Path) -> None:
    """slug->title map'i JSON olarak kaydeder."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(slug_to_title, file, ensure_ascii=False, indent=2, sort_keys=True)



def load_slug_to_title_map(input_path: Path) -> Dict[str, str]:
    """Kaydedilmiş slug->title map'i JSON'dan yükler."""
    with input_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError(f"Slug map file must contain a JSON object: {input_path}")

    cleaned: Dict[str, str] = {}
    for key, value in data.items():
        if isinstance(key, str) and isinstance(value, str):
            cleaned[key] = value

    return cleaned



def get_or_build_slug_to_title_map(
    vault_path: Path,
    cache_path: Path | None = None,
    force_rebuild: bool = False,
) -> Dict[str, str]:
    """
    Cache dosyası varsa onu yükler.
    Yoksa veya force_rebuild=True ise map'i yeniden üretip kaydeder.
    """
    if cache_path is None:
        cache_path = vault_path / ".cache" / "slug_to_title_map.json"

    if cache_path.exists() and not force_rebuild:
        return load_slug_to_title_map(cache_path)

    slug_to_title = build_slug_to_title_map(vault_path)
    save_slug_to_title_map(slug_to_title, cache_path)

    return slug_to_title



def normalize_site_url(url: str) -> str:
    """Ensures the URL has a scheme for reliable parsing."""
    url = (url or "").strip()
    if not url:
        return ""
    if "://" not in url:
        # urlparse needs a scheme to correctly identify the netloc
        return f"https://{url}"
    return url



def extract_internal_slug(url: str, site_url: str) -> Optional[str]:
    """URL bizim domain'imize aitse slug döndürür, değilse None.

    - /2026/02/21/bilisler-diyalektigi/ -> bilisler-diyalektigi
    - ?p=123 gibi query linklerinde slug döndürmez (None)
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
# Phase 2: Link Dönüştürme
# ======================================================


def split_emphasis(text: str) -> Tuple[str, str, str]:
    """Tamamı vurgulanmış metinleri ayırır.

    Örn:
      "*Metin*" -> ("*", "Metin", "*")
      "**Metin**" -> ("**", "Metin", "**")
      "_Metin_" -> ("_", "Metin", "_")

    Eğer tam sarmalama yoksa: ("", text, "")

    Not: Bu minimal bir koruma; karmaşık/nested durumlarda dokunmaz.
    """

    s = text
    for mark in ("**", "__", "*", "_"):
        if s.startswith(mark) and s.endswith(mark) and len(s) >= 2 * len(mark) + 1:
            return mark, s[len(mark) : -len(mark)], mark
    return "", text, ""



def parse_wikilink(core: str) -> Optional[Tuple[str, Optional[str]]]:
    """core [[Target]] veya [[Target|Alias]] ise (target, alias?) döndürür."""
    t = core.strip()
    if not (t.startswith("[[") and t.endswith("]]")):
        return None

    inside = t[2:-2]
    if "|" in inside:
        target, alias = inside.split("|", 1)
        return target.strip(), alias.strip()
    return inside.strip(), None


def escape_wikilink_part(text: str) -> str:
    """
    Wikilink içinde [] varsa parser güvenliği için sona boşluk ekler.
    """
    if "[" in text or "]" in text:
        return text.rstrip() + " "
    return text


def make_wikilink(real_title: str, display_text: str) -> str:
    """
    real_title ve display_text'e göre uygun wikilink üretir.

    - Aynıysa alias kullanmaz
    - Farklıysa alias ekler
    - Başlıkta [] varsa parser güvenliği için normalize eder
    """

    display = (display_text or "").strip()
    safe_title = escape_wikilink_part(real_title)
    safe_display = escape_wikilink_part(display)

    if not display or display == real_title:
        return f"[[{safe_title}]]"

    return f"[[{safe_title}|{safe_display}]]"


# ======================================================
# CORE: REWRITE BODY
# ======================================================

def find_markdown_links(text: str):
    # Parser for markdown links in [text](url) form 
    # that correctly handles nested brackets and parentheses.
    i = 0
    n = len(text)

    while i < n:
        start = text.find("[", i)
        if start == -1:
            return

        depth = 1
        j = start + 1

        while j < n and depth:
            if text[j] == "[":
                depth += 1
            elif text[j] == "]":
                depth -= 1
            j += 1

        if depth != 0:
            i = start + 1
            continue

        if j >= n or text[j] != "(":
            i = start + 1
            continue

        k = j + 1
        par = 1

        while k < n and par:
            if text[k] == "(":
                par += 1
            elif text[k] == ")":
                par -= 1
            k += 1

        if par != 0:
            i = start + 1
            continue

        link_text = text[start+1:j-1]
        url = text[j+1:k-1]

        yield start, k, link_text, url

        i = k


def rewrite_body(body: str, slug_map: Dict[str, str], site_url: str) -> Tuple[str, int, int, int]:
    internal_found = 0
    converted = 0
    unmatched = 0

    parts = []
    last = 0

    for start, end, link_text_raw, url in find_markdown_links(body):
        parts.append(body[last:start])

        slug = extract_internal_slug(url.strip(), site_url)
        if slug is None:
            parts.append(body[start:end])
            last = end
            continue

        internal_found += 1

        real_title = slug_map.get(slug)
        if real_title is None:
            unmatched += 1
            parts.append(body[start:end])
            last = end
            continue

        pre, core, suf = split_emphasis(link_text_raw)

        wk = parse_wikilink(core)
        if wk is not None:
            _target, alias = wk
            display = alias if alias is not None else _target
            new_wk = make_wikilink(real_title, display)
            parts.append(f"{pre}{new_wk}{suf}")
            converted += 1
            last = end
            continue

        new_wk = make_wikilink(real_title, core)
        parts.append(f"{pre}{new_wk}{suf}")
        converted += 1
        last = end

    parts.append(body[last:])
    new_body = "".join(parts)

    return new_body, internal_found, converted, unmatched


# ======================================================
# APPLY
# ======================================================


def process_vault(vault_path: Path, site_url: str, apply: bool, backups: bool) -> ApplyStats:
    stats = ApplyStats(unmatched_examples=[])

    slug_map = get_or_build_slug_to_title_map(vault_path)

    if not slug_map:
        print("Uyarı: slug->title map boş. Frontmatter'da 'slug' alanı yok olabilir.")

    for md_path in iter_markdown_files(vault_path):
        stats.files_scanned += 1

        original = read_text(md_path)

        front_matter, body_start = parse_frontmatter(original)
        body = original[body_start:] if body_start > 0 else original

        # 1️⃣ linkleri wikilink'e çevir
        new_body, internal_found, converted, unmatched = rewrite_body(
            body, slug_map, site_url
        )

        # 2️⃣ markdown post-processing
        new_body = cleanup_markdown_after_wikilinks(new_body)

        # 3️⃣ istatistikler
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
    parser = argparse.ArgumentParser(description="Obsidian Phase 2: convert WP URLs to wikilinks")
    parser.add_argument("--apply", action="store_true", help="Değişiklikleri dosyalara yaz")
    parser.add_argument("--backup", action="store_true", help=".bak yedeği oluştur")
    parser.add_argument("--vault", type=str, default=str(VAULT_PATH), help="Vault path")
    parser.add_argument("--site", type=str, default=SITE_URL, help="Site URL (domain)")

    args = parser.parse_args()

    vault = Path(args.vault)
    if not vault.exists():
        print(f"Hata: Vault bulunamadı: {vault}")
        sys.exit(1)

    apply = bool(args.apply)
    backups = bool(args.backup)

    site_url = normalize_site_url(args.site)
    if not site_url:
        print(f"Hata: Site URL'si belirtilmemiş veya geçersiz: '{args.site}'")
        sys.exit(1)

    stats = process_vault(vault, site_url, apply=apply, backups=backups)
    print_stats(stats, apply=apply)


if __name__ == "__main__":
    main()