from __future__ import annotations
from pathlib import Path

from config.loader import load_config
from importer.wordpress_api import ensure_json_export
from sources.imported_json import load_imported_json
from processors.pipeline import process_posts
from assembler import assemble
from writer import write

import argparse
from datetime import datetime

config = load_config()
JSON_PATH = Path(config["paths"]["json_file"])
BASE_URL = config["wordpress"]["base_url"]

def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--order",
        choices=["newest", "oldest"],
        default="newest",
        help="Order posts by date"
    )

    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of posts"
    )

    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Fetch fresh data from WordPress"
    )

    parser.add_argument(
        "--mode",
        choices=["per_post", "book"],
        default="per_post",
        help="Output mode"
    )

    parser.add_argument(
        "--frontmatter",
        action="store_true",
        help="Include frontmatter"
    )


    return parser.parse_args()


def order_and_limit_posts(posts, order: str = "newest", limit: int | None = None):
    # sort posts by date order
    reverse = order == "newest"
    posts = sorted(posts, key=lambda p: p.date or "", reverse=reverse)

    # limit the number of posts
    if limit is not None:
        posts = posts[:limit]

    return posts


def main() -> None:
    args = parse_args()

    ensure_json_export(
        base_url=BASE_URL,
        json_path=JSON_PATH,
        refresh=args.refresh,
    )

    print("Starting build...")

    posts = load_imported_json(verbose=True)
    posts = process_posts(posts, verbose=True)

    posts = order_and_limit_posts(
        posts,
        order=args.order,
        limit=args.limit
    )

    units = assemble(posts, mode=args.mode, verbose=True, include_frontmatter=args.frontmatter)

    print(f"[INFO] Writing {len(units)} markdown files...")
    print(f"[INFO] Output mode: {args.mode}")
    write(units, format="md", output_dir="output", verbose=True)

    print("Build completed. ✅")


if __name__ == "__main__":
    main()