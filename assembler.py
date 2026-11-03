from __future__ import annotations
import yaml
from markdownify import markdownify

from core.models import Post, DocumentUnit


def assemble(posts: list[Post],
             mode: str = "per_post",
             verbose: bool = False,
             include_frontmatter: bool = False,
             include_excerpt: bool = False,
             ) -> list[DocumentUnit]:
    """
    Assemble processed posts into write-ready document units.
    """
    if mode == "per_post":
        return _assemble_per_post(
            posts,
            verbose=verbose,
            include_frontmatter=include_frontmatter,
            include_excerpt=include_excerpt,
        )

    if mode == "book":
         return _assemble_book(
             posts,
             verbose=verbose,
             include_frontmatter=include_frontmatter,
             include_excerpt=include_excerpt,
         )

    raise ValueError(f"Unsupported assembly mode: {mode}")


def _process_frontmatter(data: dict) -> str:
    yaml_str = yaml.dump(data, sort_keys=False, allow_unicode=True)
    return f"---\n{yaml_str}---\n"


def _process_content(
    post: Post,
    include_excerpt: bool = False,
    prefix: str = "",
) -> str:
    content = markdownify(f"{prefix}{post.content}")
    if not include_excerpt or not post.excerpt:
        return content

    excerpt = markdownify(post.excerpt).strip()
    if not excerpt:
        return content

    return f"{excerpt}\n\n{content}"


def _assemble_per_post(posts: list[Post],
                       verbose: bool = False,
                       include_frontmatter: bool = False,
                       include_excerpt: bool = False,
                       ) -> list[DocumentUnit]:
    """
    Convert each post into its own DocumentUnit.
    """
    units: list[DocumentUnit] = []

    for post in posts:
        if include_frontmatter:
            frontmatter_str = _process_frontmatter(post.frontmatter)
        filename = f"{post.slug or 'untitled'}.md"

        unit = DocumentUnit(
            filename=filename,
            title=post.title,
            content=_process_content(post, include_excerpt=include_excerpt),
            frontmatter=frontmatter_str if include_frontmatter else "",
            meta = {
                    **post.meta,
                    "date": post.date,
                    "slug": post.slug,
                    }
        )
        units.append(unit)

        if verbose:
            print(f"Assembled: {filename}")

    return units

def _assemble_book(posts: list[Post],
                   verbose: bool = False,
                   filename: str = "book.md",
                   include_frontmatter: bool = False,
                   include_excerpt: bool = False,
                   ) -> list[DocumentUnit]:
    """
    Convert all posts into a single DocumentUnit.
    """

    FILENAME = filename
    book_content : list[str] = []

    for post in posts:
        frontmatter_prefix = ""
        if include_frontmatter:
            frontmatter_prefix = f"{_process_frontmatter(post.frontmatter)}\n"

        content = _process_content(
            post,
            include_excerpt=include_excerpt,
            prefix=frontmatter_prefix,
        )
        title = post.title
        book_content.append(f"# {title}\n\n{content}")

    if verbose:
            print(f"Assembled: {filename}")

    book = DocumentUnit(
        filename=FILENAME,
        content="\n\n".join(book_content)
        )

    return list([book])
