from __future__ import annotations

from sources.imported_json import load_imported_json
from processors.pipeline import process_posts
from assembler import assemble
from writer import write


def main() -> None:
    print("Starting build...")

    posts = load_imported_json(verbose=True)
    posts = process_posts(posts, verbose=True)
    units = assemble(posts, mode="per_post", verbose=True)
    write(units, format="md", output_dir="output", verbose=True)

    print("Build completed.")


if __name__ == "__main__":
    main()