import json
from pathlib import Path

from core.models import Post

from config.loader import load_config

config = load_config()


DEFAULT_INPUT_FILE = "data/imported.json"


def load_imported_json(
    input_file: str | Path = DEFAULT_INPUT_FILE,
    verbose: bool = False,
    ) -> list[Post]:
    """
    Load imported WordPress JSON and convert it into Post objects.
    """
    input_path = Path(input_file)

    if verbose:
        print(f"Loading imported JSON: {input_path}")

    if not input_path.exists():
        raise FileNotFoundError(f"Imported JSON file not found: {input_path}")

    if input_path.stat().st_size == 0:
        raise ValueError(
            f"Imported JSON file is empty: {input_path}. "
            "Run a fresh export or replace it with valid JSON data."
        )

    with input_path.open("r", encoding="utf-8") as f:
        try:
            payload = json.load(f)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Imported JSON file is not valid JSON: {input_path}"
            ) from exc

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
            frontmatter={field: item.get(field) for field in config["frontmatter"]["fields"]},
            source_path=str(input_path),
            source_type="json",
        )
        posts.append(post)

    return posts
