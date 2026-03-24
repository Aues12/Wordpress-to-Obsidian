from __future__ import annotations

import re
from datetime import datetime

from core.models import Post

import re


TR_MAP = str.maketrans({
    "ç": "c", "Ç": "c",
    "ğ": "g", "Ğ": "g",
    "ı": "i", "I": "i",
    "İ": "i",
    "ö": "o", "Ö": "o",
    "ş": "s", "Ş": "s",
    "ü": "u", "Ü": "u",
})


def slugify(value: str) -> str:
    """
    Create a filesystem- and URL-friendly slug.
    Supports Turkish characters.
    """
    # normalize Turkish chars first
    value = value.translate(TR_MAP)

    # basic normalization
    value = value.strip().lower()

    # spaces → dash
    value = re.sub(r"\s+", "-", value)

    # remove invalid chars
    value = re.sub(r"[^a-z0-9\-]", "", value)

    # collapse multiple dashes
    value = re.sub(r"-{2,}", "-", value)

    return value.strip("-")


def normalize_title(post: Post) -> Post:
    """
    Ensure the post has a usable title.
    """
    title = (post.title or "").strip()

    if not title:
        title = "Untitled"

    post.title = title
    return post


def normalize_slug(post: Post) -> Post:
    """
    Ensure the post has a slug.
    """
    slug = (post.slug or "").strip()

    if not slug:
        slug = slugify(post.title)

    if not slug:
        slug = "untitled"

    post.slug = slug
    return post


def normalize_date(post: Post) -> Post:
    """
    Normalize date into ISO-like string when possible.

    If parsing fails, keep original value unchanged.
    """
    if not post.date:
        return post

    raw_date = str(post.date).strip()

    # Common WordPress shape: 2025-03-01T12:34:56
    try:
        parsed = datetime.fromisoformat(raw_date)
        post.date = parsed.isoformat()
        return post
    except ValueError:
        return post


def normalize_metadata(post: Post) -> Post:
    """
    Run all metadata normalization steps for a single post.
    """
    post = normalize_title(post)
    post = normalize_slug(post)
    post = normalize_date(post)

    return post