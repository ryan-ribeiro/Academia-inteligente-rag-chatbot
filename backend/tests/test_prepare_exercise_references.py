import hashlib
import sqlite3
from io import BytesIO

import pytest

from scripts import prepare_exercise_references as prepare


def test_restores_missing_source_only_if_download_matches_snapshot(tmp_path, monkeypatch):
    content = b"pinned source"
    monkeypatch.setattr(prepare, "DATA", tmp_path)
    monkeypatch.setattr(
        prepare,
        "SOURCES",
        {"source.xml": ("https://example.test/source", hashlib.sha256(content).hexdigest())},
    )
    monkeypatch.setattr(prepare, "urlopen", lambda *args, **kwargs: BytesIO(content))
    prepare.ensure_sources()
    assert (tmp_path / "source.xml").read_bytes() == content
    monkeypatch.setattr(prepare, "urlopen", lambda *args, **kwargs: BytesIO(b"changed"))
    (tmp_path / "source.xml").unlink()
    with pytest.raises(ValueError, match="pinned snapshot"):
        prepare.ensure_sources()
    assert not (tmp_path / "source.xml").exists()


def test_valid_index_checks_metadata_and_document_count(tmp_path):
    path = tmp_path / "index.sqlite3"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE metadata (key, value)")
        db.execute("CREATE TABLE documents (text)")
        db.executemany("INSERT INTO metadata VALUES (?, ?)", [("documents", "1"), ("model", "v1")])
        db.execute("INSERT INTO documents VALUES ('text')")
    assert prepare.valid_index(path, {"model": "v1"})
    assert not prepare.valid_index(path, {"model": "v2"})
    with sqlite3.connect(path) as db:
        db.execute("DELETE FROM documents")
    assert not prepare.valid_index(path, {"model": "v1"})
