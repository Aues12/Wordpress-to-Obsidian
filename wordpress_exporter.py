"""
WordPress-to-Obsidian Migrator
--------------------------------
This script:
- Pulls posts from a WordPress site
- Retrieves metadata such as date and categories
- Saves each post as an individual Markdown (.md) file

Notes:
- A resilient network layer is implemented using requests.Session + Retry.
- YAML frontmatter is generated safely using PyYAML.

New feature:
- The --newest N argument allows fetching the N newest posts (date DESC).
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
# 1️⃣ BASIC CONFIGURATION
# ======================================================

# Replace this with your WordPress site URL
SITE_URL = "https://example.com"

# Directory where exported Markdown files will be saved
SAVE_DIR = "obsidian_posts"

POSTS_API = f"{SITE_URL}/wp-json/wp/v2/posts"
CATEGORIES_API = f"{SITE_URL}/wp-json/wp/v2/categories"

os.makedirs(SAVE_DIR, exist_ok=True)


# ======================================================
# 2️⃣ SESSION + RETRY CONFIGURATION
# ======================================================


def create_session():
    """Create a requests session with retry support and connection reuse."""

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
# 3️⃣ HELPER FUNCTIONS
# ======================================================


def fetch_all(url, params=None):
    """Fetch all pages from a paginated WordPress API endpoint."""

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
                f"HTTP error: {response.status_code} | url={url} | page={page} | body={response.text[:300]}"
            ) from e

        # WordPress returns the total number of pages in this header
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

        # Stop if the last page has been reached
        if total_pages is not None and page >= total_pages:
            break

        page += 1

    return results


def fetch(url, number: int, sort_by: str = "newest"):
    """
    Fetch a limited number of posts.

    Parameters
    ----------
    url : str
        WordPress API endpoint.

    number : int
        Number of posts to fetch.

    sort_by : str
        "newest" → newest posts first (DESC)
        
        "oldest" → oldest posts first (ASC)
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
        # WordPress REST API query parameters
        params = {
            "per_page": per_page,
            "page": page,
            "orderby": "date",
            "order": order,
        }

        response = session.get(url, params=params, timeout=30)

        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise requests.HTTPError(
                f"HTTP error: {response.status_code} | url={url} | page={page} | body={response.text[:300]}"
            ) from e

        data = response.json()
        if not data:
            break

        results.extend(data)
        page += 1

    return results[:number]



def clean_filename(name):
    """Sanitize titles so they are safe to use as filenames."""

    return re.sub(r"[\\/:*?\"<>|]", "-", name).strip()


# ======================================================
# 4️⃣ MAIN PROCESS
# ======================================================


def main():

    parser = argparse.ArgumentParser(description="WordPress → Obsidian Migrator")

    parser.add_argument(
        "--newest",
        type=int,
        default=0,
        metavar="N",
        help="Fetch the N newest posts (date DESC). Default: fetch all posts.",
    )

    parser.add_argument(
        "--oldest",
        type=int,
        default=0,
        metavar="N",
        help="Fetch the N oldest posts (date ASC). Default: fetch all posts.",
    )

    args = parser.parse_args()

    if args.newest > 0:
        print(f"Fetching {args.newest} newest posts (date DESC)...")
        posts = fetch(POSTS_API, number=args.newest, sort_by="newest")

    elif args.oldest > 0:
        print(f"Fetching {args.oldest} oldest posts (date ASC)...")
        posts = fetch(POSTS_API, number=args.oldest, sort_by="oldest")

    else:
        print("Fetching all posts...")
        posts = fetch_all(POSTS_API)

    print("Fetching categories...")
    categories = fetch_all(CATEGORIES_API)
    category_map = {c["id"]: c["name"] for c in categories}

    print("Generating Markdown files...")

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

        # Generate YAML frontmatter safely
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

    print("✅ Done! Obsidian notes were successfully generated.")


# ======================================================

if __name__ == "__main__":
    main()
