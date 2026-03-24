import json
import time
from pathlib import Path

from core.models import Post

DEFAULT_INPUT_FILE = "data/imported.json"


def load_imported_json(
    input_file: str | Path = DEFAULT_INPUT_FILE,
    verbose: bool = False,
    ) -> list[Post]:
    """
    Load imported WordPress JSON and convert it into Post objects.
    """
    start_time = time.time()
    input_path = Path(input_file)

    if verbose:
        print(f"Loading imported JSON: {input_path}")

    with input_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    raw_posts = payload.get("posts", [])
    if not isinstance(raw_posts, list):
        raise ValueError("'posts' field must be a list.")

    posts: list[Post] = []

    for item in raw_posts:
        post = Post(
            title=item.get("title", "") or "",
            content=item.get("content", "") or "",
            date=item.get("date"),
            slug=item.get("slug"),
            meta={
                "id": item.get("id"),
                "modified": item.get("modified"),
                "status": item.get("status"),
                "link": item.get("link"),
                "categories": item.get("categories", []) or [],
                "category_names": item.get("category_names", []) or [],
            },
            source_path=str(input_path),
            source_type="json",
        )
        posts.append(post)

    if verbose:
        elapsed = time.time() - start_time
        print(f"Loaded {len(posts)} posts in {elapsed:.2f} seconds")

    return posts
