"""obsidian_maintenance_phase2.py

Phase 2 — Apply Link Conversion (WordPress URL → Obsidian wikilink)
-----------------------------------------------------------------
Bu script Obsidian vault'undaki .md dosyalarında, BODY kısmındaki
WordPress iç linklerini Obsidian wikilink'lerine dönüştürür.

✅ Amaç
- [metin](https://friendlyrhapsody.com/.../slug/)  →  [[Gerçek Başlık]]
- Eğer metin, gerçek başlıktan farklıysa (kısaltma/alıntı) → alias kullan:
    [[Gerçek Başlık|Görünen Metin]]
- Metindeki italik/kalın vurguları korur ("orijinal metni bozma"):
    [*Metin*](url) → *[[Gerçek Başlık|Metin]]*

⚠️ Notlar
- Sadece SITE_URL domain'ine ait linkler dönüştürülür.
- Harici linklere dokunulmaz.
- Frontmatter'a dokunulmaz; sadece body üzerinde çalışır.
- Varsayılan olarak DRY-RUN çalışır (dosyaya yazmaz).

Gereksinimler:
  pip install pyyaml

Kullanım:
  1) CONFIG bölümünü doldur
  2) Dry-run:
     python obsidian_maintenance_phase2.py
  3) Uygula:
     python obsidian_maintenance_phase2.py --apply
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

SITE_URL = "https://friendlyrhapsody.com"
VAULT_PATH = Path("/Users/eminaliertenu/Documents/Obsidian Vault")

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


def make_wikilink(real_title: str, display_text: str) -> str:
    """
    real_title ve display_text'e göre uygun wikilink üretir.

    - Eğer görünen metin başlıkla aynıysa:
        [[Başlık]]
    - Farklıysa alias kullanır:
        [[Başlık|Görünen Metin]]
    """

    display = (display_text or "").strip()

    # Aynıysa alias kullanma
    if not display or display == real_title:
        return f"[[{real_title}]]"

    # Farklıysa alias ekle
    return f"[[{real_title}|{display}]]"


# ======================================================
# CORE: REWRITE BODY
# ======================================================


def rewrite_body(body: str, slug_map: Dict[str, str], site_url: str) -> Tuple[str, int, int, int]:
    """
    Body içindeki Markdown linklerini tarar ve WordPress internal linklerini
    Obsidian wikilink formatına dönüştürür.

    Dönüşüm yalnızca:
    - Link internal ise
    - Slug vault içinde karşılık buluyorsa

    Returns:
        (new_body, internal_found, converted, unmatched)
    """

    # İstatistik sayaçları
    internal_found = 0   # Kaç internal WP link bulundu?
    converted = 0        # Kaçı başarıyla wikilink'e çevrildi?
    unmatched = 0        # Internal olup slug map'te bulunamayanlar

    def repl(m: re.Match) -> str:
        """
        Tek bir Markdown link eşleşmesini işler.
        Regex her [text](url) için bu fonksiyonu çağırır.
        """
        nonlocal internal_found, converted, unmatched

        link_text_raw = m.group(1)
        url = m.group(2).strip()

        # 1️⃣ URL'den slug çıkar (internal değilse dokunma)
        slug = extract_internal_slug(url, site_url)
        if slug is None:
            return m.group(0)

        internal_found += 1

        # 2️⃣ Slug vault'ta var mı?
        real_title = slug_map.get(slug)
        if real_title is None:
            unmatched += 1
            return m.group(0)

        # 3️⃣ Vurgu (italik/kalın) varsa dış kabuğu koru
        pre, core, suf = split_emphasis(link_text_raw)

        # 4️⃣ Eğer core zaten wikilink ise içeriğini parse et
        wk = parse_wikilink(core)
        if wk is not None:
            _target, alias = wk
            display = alias if alias is not None else _target
            new_wk = make_wikilink(real_title, display)
            converted += 1
            return f"{pre}{new_wk}{suf}"

        # 5️⃣ Normal durumda görünen metni alias kararı için kullan
        new_wk = make_wikilink(real_title, core)
        converted += 1
        return f"{pre}{new_wk}{suf}"

    # Body içindeki tüm Markdown linklerini dönüştür
    new_body = MD_LINK_RE.sub(repl, body)
    return new_body, internal_found, converted, unmatched


# ======================================================
# APPLY
# ======================================================


def process_vault(vault_path: Path, site_url: str, apply: bool, backups: bool) -> ApplyStats:
    stats = ApplyStats(unmatched_examples=[])
    slug_map = build_slug_to_title_map(vault_path)

    if not slug_map:
        print("Uyarı: slug->title map boş. Frontmatter'da 'slug' alanı yok olabilir.")

    for md_path in iter_markdown_files(vault_path):
        stats.files_scanned += 1

        original = read_text(md_path)
        front_matter, body_start = parse_frontmatter(original)
        body = original[body_start:] if body_start > 0 else original

        new_body, internal_found, converted, unmatched = rewrite_body(body, slug_map, site_url)

        # Eğer unmatched varsa örnek topla (ilk 10 tane)
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
        print(f"Vault bulunamadı: {vault}")
        sys.exit(1)

    apply = bool(args.apply)
    backups = bool(args.backup)

    stats = process_vault(vault, args.site, apply=apply, backups=backups)
    print_stats(stats, apply=apply)


if __name__ == "__main__":
    main()