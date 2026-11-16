"""Build a resumable, local semantic index from the extracted reference corpus."""

from __future__ import annotations

import argparse
import hashlib
import sqlite3
import struct
import sys
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.integrations.embeddings import OllamaEmbedder  # noqa: E402

DATA = ROOT / "data/exercise-references"
SUPPLEMENTAL = ("PMC6950543.xml", "PMC8990091.xml")


def add_supplemental(target: sqlite3.Connection, embedder: OllamaEmbedder) -> None:
    for filename in SUPPLEMENTAL:
        path = DATA / filename
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        key = filename + ".sha256"
        existing = target.execute("SELECT value FROM metadata WHERE key=?", (key,)).fetchone()
        if existing:
            if existing[0] != digest:
                raise ValueError("Supplemental source changed; rebuild the index")
            continue
        root = ElementTree.parse(path).getroot()
        entries = []
        for section in root.findall(".//body//sec"):
            heading = section.find("title")
            title = " ".join(heading.itertext()).strip() if heading is not None else ""
            for paragraph in section.findall("p"):
                text = " ".join("".join(paragraph.itertext()).split())
                if text:
                    entries.append((title, text))
        if not entries:
            raise ValueError("Supplemental source has no paragraphs")
        article = filename.removesuffix(".xml")
        with target:
            for offset in range(0, len(entries), 16):
                batch = entries[offset : offset + 16]
                vectors = embedder.embed(
                    ["title: " + title + " | text: " + text for title, text in batch]
                )
                for number, ((title, text), vector) in enumerate(
                    zip(batch, vectors, strict=True), offset + 1
                ):
                    target.execute(
                        "INSERT INTO documents (source,source_id,language,section,url,text,vector) "
                        "VALUES (?,?,?,?,?,?,?)",
                        (
                            filename,
                            str(number),
                            "en",
                            title,
                            f"https://pmc.ncbi.nlm.nih.gov/articles/{article}/",
                            text,
                            struct.pack(f"<{len(vector)}f", *vector),
                        ),
                    )
            target.execute("INSERT INTO metadata VALUES (?,?)", (key, digest))


def build(source: Path, output: Path, embedder: OllamaEmbedder, batch_size: int = 16) -> None:
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    model_digest = embedder.fingerprint() if hasattr(embedder, "fingerprint") else ""
    temporary = output.with_suffix(output.suffix + ".partial")
    with sqlite3.connect(source) as original, sqlite3.connect(temporary) as target:
        target.executescript("""
            CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS documents (
                rowid INTEGER PRIMARY KEY, source TEXT NOT NULL, source_id TEXT NOT NULL,
                language TEXT NOT NULL, section TEXT NOT NULL, url TEXT NOT NULL,
                text TEXT NOT NULL, vector BLOB NOT NULL
            );
        """)
        metadata = dict(target.execute("SELECT key, value FROM metadata"))
        if metadata and (
            metadata.get("model") != embedder.model
            or metadata.get("corpus_sha256") != digest
            or (metadata.get("model_digest") and metadata["model_digest"] != model_digest)
        ):
            raise ValueError("Partial index belongs to a different model or corpus")
        target.executemany(
            "INSERT OR IGNORE INTO metadata VALUES (?, ?)",
            [
                ("model", embedder.model),
                ("corpus_sha256", digest),
                ("algorithm", "semantic-cosine-v1"),
                ("model_digest", model_digest),
            ],
        )
        target.executemany(
            "INSERT OR IGNORE INTO metadata VALUES (?, ?)",
            original.execute("SELECT key,value FROM metadata WHERE key LIKE '%.sha256'").fetchall(),
        )
        last_id = target.execute("SELECT COALESCE(MAX(rowid), 0) FROM documents").fetchone()[0]
        total = original.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        cursor = original.execute(
            "SELECT rowid,source,source_id,language,section,url,text FROM documents "
            "WHERE rowid > ? ORDER BY rowid",
            (last_id,),
        )
        while batch := cursor.fetchmany(batch_size):
            vectors = embedder.embed(["title: " + row[4] + " | text: " + row[6] for row in batch])
            with target:
                for row, vector in zip(batch, vectors, strict=True):
                    target.execute(
                        "INSERT INTO documents VALUES (?,?,?,?,?,?,?,?)",
                        (*row, struct.pack(f"<{len(vector)}f", *vector)),
                    )
            last_id = batch[-1][0]
            print(
                f"Indexed {target.execute('SELECT COUNT(*) FROM documents').fetchone()[0]}/{total}",
                flush=True,
            )
        count = target.execute(
            "SELECT COUNT(*) FROM documents WHERE source NOT IN (?, ?)", SUPPLEMENTAL
        ).fetchone()[0]
        if count != total:
            raise ValueError("Incomplete semantic index")
        add_supplemental(target, embedder)
        count = target.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        target.execute("INSERT OR REPLACE INTO metadata VALUES ('documents', ?)", (str(count),))
        target.commit()
    temporary.replace(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DATA / "exercise-vectors.sqlite3")
    parser.add_argument("--output", type=Path, default=DATA / "exercise-semantic.sqlite3")
    parser.add_argument("--batch-size", type=int, default=16)
    args = parser.parse_args()
    if args.batch_size < 1:
        parser.error("batch size must be positive")
    build(args.source, args.output, OllamaEmbedder(), args.batch_size)
