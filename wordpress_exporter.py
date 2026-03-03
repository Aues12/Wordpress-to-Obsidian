"""
WordPress-to-Obsidian Migrator
--------------------------------
Bu script:
- WordPress yazılarını çeker
- Tarih + kategori bilgilerini alır
- Her yazıyı ayrı bir .md dosyası olarak kaydeder

Notlar:
- requests.Session + Retry kullanılarak daha dayanıklı ağ katmanı sağlanmıştır.
- YAML frontmatter güvenli şekilde PyYAML ile üretilir.

Yeni:
- --newest N argümanı ile en yeni N postu (date DESC) çekilebilir.
"""

import os
import re
import argparse
import requests
import yaml
import html
from markdownify import markdownify

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ======================================================
# 1️⃣ TEMEL AYARLAR
# ======================================================

SITE_URL = "https://friendlyrhapsody.com"  # ← Burayı değiştir
SAVE_DIR = "obsidian_posts"

POSTS_API = f"{SITE_URL}/wp-json/wp/v2/posts"
CATEGORIES_API = f"{SITE_URL}/wp-json/wp/v2/categories"

os.makedirs(SAVE_DIR, exist_ok=True)


# ======================================================
# 2️⃣ SESSION + RETRY KONFİGÜRASYONU
# ======================================================


def create_session():
    """Retry destekli, bağlantı yeniden kullanan bir Session oluşturur."""

    retry_strategy = Retry(
        total=5,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)

    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    return session


session = create_session()


# ======================================================
# 3️⃣ YARDIMCI FONKSİYONLAR
# ======================================================


def fetch_all(url, params=None):
    """Tüm sayfaları dolaşarak sonuçları çeker."""
    results = []
    params = params or {}

    total_pages = None
    page = 1

    while True:
        query = {**params, "per_page": 20, "page": page}
        response = session.get(url, params=query, timeout=30)

        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise requests.HTTPError(
                f"HTTP hata: {response.status_code} | url={url} | page={page} | body={response.text[:300]}"
            ) from e

        if total_pages is None:
            header_val = response.headers.get("X-WP-TotalPages")
            if header_val:
                print(f"Total page number for {url}: {header_val}")
                try:
                    total_pages = int(header_val)
                except ValueError:
                    total_pages = None

        data = response.json()
        if not data:
            break

        results.extend(data)

        if total_pages is not None and page >= total_pages:
            break

        page += 1

    return results


def fetch(url, number: int, sort_by: str = "newest"):
    """En yeni (date DESC) N postu çeker.

    newest <= 0 ise boş liste döndürür.
    """

    if number <= 0:
        return []

    results = []
    page = 1

    per_page = 20

    if sort_by == "newest":
        order = "desc"
    elif sort_by == "oldest":
        order = "asc"

    while len(results) < number:
        # WP REST API  parametreleri
        params = {
            "per_page": per_page,
            "page": page,
            "orderby": "date",
            "order": order,
        }
        query = params
        response = session.get(url, params=query, timeout=30)

        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise requests.HTTPError(
                f"HTTP hata: {response.status_code} | url={url} | page={page} | body={response.text[:300]}"
            ) from e

        data = response.json()
        if not data:
            break

        results.extend(data)
        page += 1

    return results[:number]
    


def clean_filename(name):
    return re.sub(r"[\/:*?\"<>|]", "-", name).strip()


# ======================================================
# 4️⃣ ANA İŞLEM
# ======================================================


def main():
      
    parser = argparse.ArgumentParser(description="WordPress → Obsidian Migrator")
    parser.add_argument(
        "--newest",
        type=int,
        default=0,
        metavar="N",
        help="En yeni N postu çek (date DESC). Varsayılan: tüm postlar.",
    )

    parser.add_argument(
        "--oldest",
        type=int,
        default=0,
        metavar="N",
        help="En eski N postu çek (date ASC). Varsayılan: tüm postlar.",
    )

    args = parser.parse_args()

    if args.newest > 0:
        print(f"En yeni {args.newest} yazılar çekiliyor (date DESC)...")
        posts = fetch(POSTS_API, number=args.newest, sort_by="newest")
    elif args.oldest > 0:
        print(f"En eski {args.oldest} yazılar çekiliyor (date ASC)...")
        posts = fetch(POSTS_API, number=args.oldest, sort_by="oldest")

    else:
        print("Yazılar çekiliyor...")
        posts = fetch_all(POSTS_API)

    print("Kategoriler çekiliyor...")
    categories = fetch_all(CATEGORIES_API)
    category_map = {c["id"]: c["name"] for c in categories}

    print("Dosyalar oluşturuluyor...")

    for post in posts:
        title = html.unescape(post["title"]["rendered"]).strip()
        slug = post["slug"]
        date = post.get("date")
        modified = post.get("modified")
        canonical = post.get("link")

        category_names = [
            category_map.get(cid, f"cat_{cid}") for cid in post.get("categories", [])
        ]

        content_html = post["content"]["rendered"]
        content_md = markdownify(content_html)

        # YAML frontmatter güvenli üretim
        metadata = {
            "title": title,
            "date": date,
            "modified": modified,
            "slug": slug,
            "canonical": canonical,
        }

        if category_names:
            metadata["categories"] = category_names

        frontmatter_yaml = yaml.safe_dump(
            metadata,
            allow_unicode=True,
            sort_keys=False,
        )

        filename = os.path.join(SAVE_DIR, clean_filename(title) + ".md")

        with open(filename, "w", encoding="utf-8") as f:
            f.write("---\n")
            f.write(frontmatter_yaml)
            f.write("---\n")
            f.write(content_md)

    print("✅ Tamamlandı! Obsidian bağlantı ağı oluşturuldu.")


# ======================================================

if __name__ == "__main__":
    main()
