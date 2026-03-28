from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# --- Basic defaults ---
DEFAULT_TIMEOUT = 30
DEFAULT_PER_PAGE = 20

JSON_PATH = Path("data/imported.json")


class WordPressAPIError(RuntimeError):
    """Raised when a WordPress API request fails."""


# --- Session setup ---

def create_session() -> requests.Session:
    """
    Create a requests session with retry logic.

    This helps avoid failures due to temporary network issues
    or rate limiting (e.g. 429, 500 errors).
    """
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


# --- Helpers ---

def _join_url(base_url: str, endpoint: str) -> str:
    """
    Safely combine base URL and endpoint.
    """
    base = base_url.rstrip("/")
    tail = endpoint.lstrip("/")
    return f"{base}/{tail}"


# --- Core fetch logic ---

def fetch_all(
    session: requests.Session,
    url: str,
    params: dict[str, Any] | None = None,
    *,
    per_page: int = DEFAULT_PER_PAGE,
    timeout: int = DEFAULT_TIMEOUT,
) -> list[dict[str, Any]]:
    """
    Fetch all pages from a paginated WordPress endpoint.

    WordPress returns results in pages. This function loops
    through all pages and combines them into a single list.
    """
    results: list[dict[str, Any]] = []
    params = params or {}

    total_pages: int | None = None
    page = 1

    while True:
        query = {**params, "per_page": per_page, "page": page}
        response = session.get(url, params=query, timeout=timeout)

        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise WordPressAPIError(
                f"HTTP error {response.status_code} while fetching {url} "
                f"(page={page})."
            ) from exc

        # Try to read total page count from headers
        if total_pages is None:
            raw_total_pages = response.headers.get("X-WP-TotalPages")
            if raw_total_pages:
                try:
                    total_pages = int(raw_total_pages)
                except ValueError:
                    total_pages = None

        data = response.json()
        if not data:
            break

        if not isinstance(data, list):
            raise WordPressAPIError(
                f"Expected list response, got {type(data).__name__}."
            )

        results.extend(data)

        # Stop if we reached last page
        if total_pages is not None and page >= total_pages:
            break

        page += 1

    return results


# --- Category mapping ---

def build_category_map(
    session: requests.Session,
    base_url: str,
    *,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[int, str]:
    """
    Fetch categories and build id -> name mapping.

    This allows us to attach readable category names to posts.
    """
    categories_url = _join_url(base_url, "/wp-json/wp/v2/categories")
    categories = fetch_all(session, categories_url, timeout=timeout)

    return {
        category["id"]: category["name"]
        for category in categories
        if isinstance(category, dict) and "id" in category and "name" in category
    }


# --- Normalization ---

def normalize_post(
    post: dict[str, Any],
    category_map: dict[int, str] | None = None,
) -> dict[str, Any]:
    """
    Convert raw WordPress post into a clean, stable structure.

    This ensures the rest of the system works with predictable fields.
    """
    category_map = category_map or {}

    category_ids = post.get("categories", []) or []
    category_names = [
        category_map.get(category_id, f"cat_{category_id}")
        for category_id in category_ids
    ]

    return {
        "id": post.get("id"),
        "date": post.get("date"),
        "modified": post.get("modified"),
        "slug": post.get("slug"),
        "status": post.get("status"),
        "link": post.get("link"),
        "title": (post.get("title") or {}).get("rendered", ""),
        "content": (post.get("content") or {}).get("rendered", ""),
        "categories": category_ids,
        "category_names": category_names
            }


# --- High-level API ---

def fetch_posts(
    base_url: str,
    *,
    session: requests.Session | None = None,
    post_params: dict[str, Any] | None = None,
    include_categories: bool = True,
    timeout: int = DEFAULT_TIMEOUT,
    per_page: int = DEFAULT_PER_PAGE,
                ) -> list[dict[str, Any]]:
    """
    Fetch all posts from WordPress and normalize them.
    """
    owns_session = session is None
    session = session or create_session()

    try:
        posts_url = _join_url(base_url, "/wp-json/wp/v2/posts")

        category_map = (
            build_category_map(session, base_url, timeout=timeout)
            if include_categories
            else {}
        )

        posts = fetch_all(
            session,
            posts_url,
            params=post_params,
            per_page=per_page,
            timeout=timeout,
        )

        return [normalize_post(post, category_map=category_map) for post in posts]

    finally:
        if owns_session:
            session.close()


# --- Export ---

def export_posts_to_json(
    base_url: str,
    output_file: str | Path,
    *,
    post_params: dict[str, Any] | None = None,
    include_categories: bool = True,
    timeout: int = DEFAULT_TIMEOUT,
    per_page: int = DEFAULT_PER_PAGE,
    pretty: bool = True,
                        ) -> Path:
    """
    Fetch posts and save them into imported.json.

    This acts as the "raw data layer" of the system.
    """
    posts = fetch_posts(
        base_url,
        post_params=post_params,
        include_categories=include_categories,
        timeout=timeout,
        per_page=per_page,
    )

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "site_url": base_url,
        "count": len(posts),
        "posts": posts,
    }

    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(
            payload,
            handle,
            ensure_ascii=False,
            indent=2 if pretty else None,
        )

    return output_path


def ensure_json_export(base_url: str, json_path: Path, refresh: bool = False) -> None:
    """
    Ensure that WordPress posts are available as a local JSON file.

    This function checks whether the given JSON file already exists.
    - If the file exists and `refresh` is False, it does nothing (uses cached data).
    - If the file does not exist, or `refresh` is True, it fetches posts
      from the WordPress API and writes them to the JSON file.

    Parameters
    ----------
    base_url : str
        Base URL of the WordPress site (e.g., "https://your-site.com").

    json_path : Path
        Path where the JSON file should be stored (e.g., data/imported.json).

    refresh : bool, optional
        If True, forces re-fetching data from WordPress even if the JSON file exists.
        Default is False.

    Notes
    -----
    - Creates parent directories if they do not exist.
    - Acts as a simple caching mechanism to avoid repeated API calls.
    - Intended to be used both in CLI pipelines and standalone scripts.
    """

    json_path.parent.mkdir(parents=True, exist_ok=True)

    if json_path.exists() and not refresh:
        print(f"[INFO] Using existing JSON: {json_path}")
        return

    print(f"[INFO] Fetching fresh data from WordPress: {base_url}")
    export_posts_to_json(
        base_url=base_url,
        output_file=str(json_path)
    )


import time

def main():
    start_time = time.time()
    print("Starting export...")

    base_url = "https://friendlyrhapsody.com"
    output_file = "data/imported.json"
    
    ensure_json_export(base_url, JSON_PATH, refresh=True)

    elapsed = time.time() - start_time

    print(f"Export completed: {Path(output_file)}")
    print(f"Elapsed time: {elapsed:.2f} seconds")

if __name__ == "__main__":
    main()

