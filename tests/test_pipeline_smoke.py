from __future__ import annotations

import json
from pathlib import Path

from assembler import assemble
from cli.main import parse_args
from core.models import Post
from importer.wordpress_api import normalize_post
from processors.pipeline import process_posts
from sources.imported_json import load_imported_json
from writer import write


def test_excerpt_cli_flag_defaults_to_false() -> None:
    assert parse_args([]).excerpt is False
    assert parse_args(["--excerpt"]).excerpt is True


def test_wordpress_excerpt_is_normalized() -> None:
    post = normalize_post(
        {
            "title": {"rendered": "Baslik"},
            "content": {"rendered": "<p>Icerik</p>"},
            "excerpt": {"rendered": "<p>Ozet &amp; giris</p>"},
        }
    )

    assert post["excerpt"] == "<p>Ozet & giris</p>"


def test_pipeline_smoke_per_post(tmp_path: Path) -> None:
    input_path = tmp_path / "imported.json"
    output_dir = tmp_path / "output"

    payload = {
        "posts": [
            {
                "id": 1,
                "title": "Merhaba Dunya",
                "content": "<p>Ilk icerik</p>",
                "excerpt": "<p>Kisa ozet</p>",
                "date": "2026-05-01T10:20:30",
                "modified": "2026-05-01T10:20:30",
                "slug": "",
                "status": "publish",
                "link": "https://example.com/post-1",
                "categories": [10],
                "category_names": ["Genel"],
            }
        ]
    }
    input_path.write_text(json.dumps(payload), encoding="utf-8")

    posts = load_imported_json(input_file=input_path)
    processed = process_posts(posts)
    units = assemble(processed, mode="per_post", include_frontmatter=True)

    write(units, format="md", output_dir=output_dir, mode="per_post")

    written_file = output_dir / "merhaba-dunya.md"

    assert written_file.exists()
    content = written_file.read_text(encoding="utf-8")
    assert "# Merhaba Dunya" in content
    assert "Ilk icerik" in content
    assert "Kisa ozet" not in content
    assert "slug: null" not in content


def test_pipeline_includes_excerpt_when_requested(tmp_path: Path) -> None:
    input_path = tmp_path / "imported.json"
    output_dir = tmp_path / "output"

    payload = {
        "posts": [
            {
                "title": "Ozetli Yazi",
                "content": "<p>Ana icerik</p>",
                "excerpt": "<p>Kisa <strong>ozet</strong></p>",
                "slug": "ozetli-yazi",
            }
        ]
    }
    input_path.write_text(json.dumps(payload), encoding="utf-8")

    posts = process_posts(load_imported_json(input_file=input_path))
    units = assemble(posts, mode="per_post", include_excerpt=True)
    write(units, format="md", output_dir=output_dir, mode="per_post")

    content = (output_dir / "ozetli-yazi.md").read_text(encoding="utf-8")
    assert "Kisa **ozet**" in content
    assert content.index("Kisa **ozet**") < content.index("Ana icerik")


def test_book_assembly_includes_excerpt_when_requested() -> None:
    posts = [
        Post(
            title="Kitap Yazisi",
            content="<p>Kitap icerigi</p>",
            excerpt="<p>Kitap ozeti</p>",
        )
    ]

    content = assemble(posts, mode="book", include_excerpt=True)[0].content

    assert content.index("Kitap ozeti") < content.index("Kitap icerigi")


def test_pipeline_smoke_book(tmp_path: Path) -> None:
    input_path = tmp_path / "imported.json"
    output_dir = tmp_path / "output"

    payload = {
        "posts": [
            {
                "id": 1,
                "title": "Birinci Yazi",
                "content": "<p>Birinci icerik</p>",
                "date": "2026-05-01T10:20:30",
                "modified": "2026-05-01T10:20:30",
                "slug": "birinci-yazi",
                "status": "publish",
                "link": "https://example.com/post-1",
                "categories": [],
                "category_names": [],
            },
            {
                "id": 2,
                "title": "Ikinci Yazi",
                "content": "<p>Ikinci icerik</p>",
                "date": "2026-05-02T10:20:30",
                "modified": "2026-05-02T10:20:30",
                "slug": "ikinci-yazi",
                "status": "publish",
                "link": "https://example.com/post-2",
                "categories": [],
                "category_names": [],
            },
        ]
    }
    input_path.write_text(json.dumps(payload), encoding="utf-8")

    posts = load_imported_json(input_file=input_path)
    processed = process_posts(posts)
    units = assemble(processed, mode="book", include_frontmatter=False)

    write(units, format="md", output_dir=output_dir, mode="book")

    written_file = output_dir / "book.md"

    assert written_file.exists()
    content = written_file.read_text(encoding="utf-8")
    assert "# Birinci Yazi" in content
    assert "# Ikinci Yazi" in content
    assert "Birinci icerik" in content
    assert "Ikinci icerik" in content
