from __future__ import annotations

from pathlib import Path

from core.models import DocumentUnit


DEFAULT_OUTPUT_DIR = "output"


def write(
    units: list[DocumentUnit],
    format: str = "md",
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    verbose: bool = False,
) -> None:
    """
    Write document units to disk.

    For now, only markdown output is supported.
    """
    if format == "md":
        _write_markdown(units, output_dir=output_dir, verbose=verbose)
        return

    raise ValueError(f"Unsupported output format: {format}")


def _write_markdown(
    units: list[DocumentUnit],
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    verbose: bool = False,
    mode: str = "per_post"
) -> None:
    """
    Write each DocumentUnit as a separate markdown file.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    if mode == "per_post":
        # In this case, each unit is a post object
        for unit in units:
            file_path = output_path / unit.filename
            content = unit.content

            if unit.title:
                content = f"# {unit.title}\n\n{content}"
            
            file_path.write_text(content, encoding="utf-8")

            if verbose:
                print(f"Wrote: {file_path}")

    elif mode == "book":
        if len(units) != 1:
            raise ValueError("Book mode expects exactly one DocumentUnit.")
        # In this case, the  unit is the posts combined
        unit = units[0]
        file_path = output_path / unit.filename
        content = unit.content

        if unit.title:
            content = f"# {unit.title}\n\n{content}"
        
        file_path.write_text(content, encoding="utf-8")

        if verbose:
            print(f"Wrote: {file_path}")