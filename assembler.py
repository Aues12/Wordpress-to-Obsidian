from __future__ import annotations

from core.models import Post, DocumentUnit


def assemble(posts: list[Post], mode: str = "per_post", verbose: bool = False) -> list[DocumentUnit]:
    """
    Assemble processed posts into write-ready document units.
    """
    if mode == "per_post":
        return _assemble_per_post(posts, verbose=verbose)
    
    if mode == "book":
         return _assemble_book(posts, verbose=verbose)

    raise ValueError(f"Unsupported assembly mode: {mode}")


def _assemble_per_post(posts: list[Post], verbose: bool = False) -> list[DocumentUnit]:
    """
    Convert each post into its own DocumentUnit.
    """
    units: list[DocumentUnit] = []

    for post in posts:
        filename = f"{post.slug or 'untitled'}.md"

        unit = DocumentUnit(
            filename=filename,
            title=post.title,
            content=post.content,
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

def _assemble_book(posts: list[Post], verbose: bool = False, filename: str = "book.md") -> list[DocumentUnit]:
    """
    Convert all posts into a single DocumentUnit.
    """

    FILENAME = filename
    book_content = []

    for post in posts:
        book_content.append(f"# {post.title}\n\n{post.content}")

    if verbose:
            print(f"Assembled: {filename}")
    
    book = DocumentUnit(
        filename=FILENAME,
        content="\n\n".join(book_content)
        )

    return list([book])

