from pathlib import Path

import pytest

from importer.wordpress_api import ensure_json_export
from sources.imported_json import load_imported_json


def test_import_reports_missing_empty_and_invalid_json(tmp_path: Path) -> None:
    path = tmp_path / 'imported.json'
    with pytest.raises(FileNotFoundError, match='not found'):
        load_imported_json(path)
    path.write_text('', encoding='utf-8')
    with pytest.raises(ValueError, match='empty'):
        load_imported_json(path)
    path.write_text('{', encoding='utf-8')
    with pytest.raises(ValueError, match='not valid JSON'):
        load_imported_json(path)


def test_export_uses_cache_and_rejects_placeholder_when_fetching(tmp_path: Path) -> None:
    path = tmp_path / 'imported.json'
    path.write_text('{}', encoding='utf-8')
    ensure_json_export('https://your-site.com', path)
    with pytest.raises(ValueError, match='placeholder'):
        ensure_json_export('https://your-site.com', path, refresh=True)
    path.write_text('', encoding='utf-8')
    with pytest.raises(ValueError, match='placeholder'):
        ensure_json_export('https://your-site.com', path)
