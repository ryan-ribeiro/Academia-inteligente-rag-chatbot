"""Build an offline sparse TF-IDF index of the downloaded exercise references."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sqlite3
import unicodedata
import zlib
from collections import Counter
from pathlib import Path

from extract_exercise_reference import extract

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "exercise-references"
SOURCES = ("PMC10801605.xml", "free-exercise-db.json", "logpress-exercises.json")


def tokens(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return re.findall(r"[^\W_]+", normalized, re.UNICODE)


def chunks(data: Path = DATA):
    for number, item in enumerate(extract(), 1):
        yield "PMC10801605.xml", str(number), "en", item["section"], item["url"], item["text"]
    records = json.loads((data / SOURCES[1]).read_text(encoding="utf-8"))
    for item in records:
        content = "\n".join([item["name"], *item.get("instructions", [])])
        url = "https://github.com/yuhonas/free-exercise-db/tree/main/exercises/" + item["id"]
        yield SOURCES[1], item["id"], "en", item["name"], url, content
    records = json.loads((data / SOURCES[2]).read_text(encoding="utf-8"))
    for item in records:
        instructions = item.get("instructions") or {}
        steps = item.get("instruction_steps") or {}
        for language in sorted(set(instructions) | set(steps)):
            text = instructions.get(language) or ""
            parts = steps.get(language) or []
            if isinstance(parts, str):
                parts = [parts]
            content = "\n".join([item["name"], text, *parts]).strip()
            if not text and not parts:
                continue
            yield (
                SOURCES[2],
                item["id"],
                language,
                item["name"],
                ("https://github.com/hasaneyldrm/exercises-dataset/blob/main/data/exercises.json"),
                content,
            )


def build(output: Path) -> tuple[int, int]:
    documents = list(chunks())
    counts = [Counter(tokens(doc[-1])) for doc in documents]
    frequency: Counter[str] = Counter()
    for count in counts:
        frequency.update(count.keys())
    total = len(documents)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.unlink(missing_ok=True)
    try:
        with sqlite3.connect(temporary) as db:
            db.executescript("""
                CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE documents (source TEXT NOT NULL, source_id TEXT NOT NULL,
                    language TEXT NOT NULL, section TEXT NOT NULL, url TEXT NOT NULL,
                    text TEXT NOT NULL, vector BLOB NOT NULL,
                    PRIMARY KEY (source, source_id, language));
                CREATE TABLE vocabulary (term TEXT PRIMARY KEY, idf REAL NOT NULL);
            """)
            db.executemany(
                "INSERT INTO vocabulary VALUES (?, ?)",
                (
                    (term, math.log((1 + total) / (1 + count)) + 1)
                    for term, count in frequency.items()
                ),
            )
            for doc, count in zip(documents, counts, strict=True):
                vector = {
                    term: (1 + math.log(n)) * (math.log((1 + total) / (1 + frequency[term])) + 1)
                    for term, n in count.items()
                }
                norm = math.sqrt(sum(value * value for value in vector.values()))
                if norm:
                    vector = {term: round(value / norm, 8) for term, value in vector.items()}
                packed = zlib.compress(json.dumps(vector, ensure_ascii=False).encode("utf-8"))
                db.execute("INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?, ?)", (*doc, packed))
            metadata = {"algorithm": "tf-idf-l2-v1", "documents": str(total)}
            metadata.update(
                {
                    name + ".sha256": hashlib.sha256((DATA / name).read_bytes()).hexdigest()
                    for name in SOURCES
                }
            )
            db.executemany("INSERT INTO metadata VALUES (?, ?)", metadata.items())
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)
    return total, len(frequency)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DATA / "exercise-vectors.sqlite3")
    args = parser.parse_args()
    documents, terms = build(args.output)
    print(f"Indexed {documents} passages and {terms} terms in {args.output}")
