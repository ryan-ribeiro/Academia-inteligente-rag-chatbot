import sqlite3

import pytest

from scripts import build_semantic_exercise_index as indexer


class FakeEmbedder:
    model = "test-model"

    def __init__(self, fail_after=None):
        self.calls = 0
        self.fail_after = fail_after

    def embed(self, texts):
        self.calls += 1
        if self.calls == self.fail_after:
            raise RuntimeError("simulated interruption")
        return [[1.0, 0.0] for _ in texts]


def test_index_recovers_from_interruption_and_includes_all_sources(tmp_path, monkeypatch):
    monkeypatch.setattr(indexer, "DATA", tmp_path)
    for name in indexer.SUPPLEMENTAL:
        (tmp_path / name).write_text(
            "<article><body><sec><title>Exercise</title><p>Evidence.</p></sec></body></article>"
        )
    source = tmp_path / "source.sqlite3"
    with sqlite3.connect(source) as db:
        db.execute("CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT)")
        db.execute("CREATE TABLE documents (source, source_id, language, section, url, text)")
        db.executemany(
            "INSERT INTO documents VALUES (?,?,?,?,?,?)",
            [
                ("test", "1", "en", "Squat", "https://example.test/1", "Squat"),
                ("test", "2", "en", "Lunge", "https://example.test/2", "Lunge"),
            ],
        )
    output = tmp_path / "semantic.sqlite3"
    with pytest.raises(RuntimeError, match="interruption"):
        indexer.build(source, output, FakeEmbedder(fail_after=2), batch_size=1)
    assert not output.exists()
    assert output.with_suffix(".sqlite3.partial").exists()
    indexer.build(source, output, FakeEmbedder(), batch_size=1)
    with sqlite3.connect(output) as db:
        assert db.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 4
        assert dict(db.execute("SELECT key,value FROM metadata"))["documents"] == "4"
