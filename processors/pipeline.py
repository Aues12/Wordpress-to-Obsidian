from __future__ import annotations

from core.models import Post
from processors.metadata import normalize_metadata


def build_pipeline():
    """
    Return the list of processing steps.
    """
    return [
        normalize_metadata,
    ]


def process_post(post: Post, verbose: bool = False) -> Post:
    """
    Process a single post through all pipeline steps.
    """
    for step in build_pipeline():
        if verbose:
            print(f"Running step: {step.__name__}")
        post = step(post)

    return post


def process_posts(posts: list[Post], verbose: bool = False) -> list[Post]:
    """
    Process a list of posts.
    """
    processed_posts: list[Post] = []

    for post in posts:
        processed_post = process_post(post, verbose=verbose)
        processed_posts.append(processed_post)

    if verbose:
        print(f"Processed {len(processed_posts)} posts.")

    return processed_posts