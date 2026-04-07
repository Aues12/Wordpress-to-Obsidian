from __future__ import annotations

from core.models import Post
from processors.metadata import normalize_post


def build_pipeline():
    """
    Return the list of processing steps.
    """
    return [
        normalize_post,
    ]


def process_post(post: Post) -> Post:
    """
    Process a single post through all pipeline steps.

    Runs normalization to ensure consistent formatting.
    """
    for step in build_pipeline():
        post = step(post)

    return post


def process_posts(posts: list[Post], verbose: bool = False) -> list[Post]:
    """
    Process a list of posts.

    Runs normalization to ensure consistent formatting.
    """
    processed_posts: list[Post] = []

    for post in posts:
        processed_post = process_post(post)
        processed_posts.append(processed_post)

    if verbose:
        print(f"Processed and normalized {len(processed_posts)} posts.")

    return processed_posts