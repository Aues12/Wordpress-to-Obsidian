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

    group = parser.add_mutually_exclusive_group()

    group.add_argument(
        "--newest",
        type=int,
        help="Select N newest posts"
    )

    group.add_argument(
        "--oldest",
        type=int,
        help="Select N oldest posts"
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

    return parser.parse_args()


def select_posts(posts, newest=None, oldest=None):
    # Date parsing helper (if string)
    def get_date(post):
        return datetime.fromisoformat(post.date) if isinstance(post.date, str) else post.date

    if newest is not None:
        posts = sorted(posts, key=get_date, reverse=True)
        selected = posts[:newest]
        print(f"[INFO] Selected newest {len(selected)} posts")
        return selected

    if oldest is not None:
        posts = sorted(posts, key=get_date)
        selected = posts[:oldest]
        print(f"[INFO] Selected oldest {len(selected)} posts")
        return selected

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

    posts = select_posts(
        posts,
        newest=args.newest,
        oldest=args.oldest
    )

    units = assemble(posts, mode=args.mode, verbose=True)

    print(f"[INFO] Writing {len(units)} markdown files...")
    print(f"[INFO] Output mode: {args.mode}")
    write(units, format="md", output_dir="output", verbose=True)

    print("Build completed. ✅")


if __name__ == "__main__":
    main()