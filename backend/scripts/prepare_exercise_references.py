"""Validate the pinned corpus and prepare the semantic index before serving traffic."""

import hashlib
import sqlite3
import sys
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.integrations.embeddings import OllamaEmbedder  # noqa: E402

sys.path.insert(0, str(ROOT / "scripts"))
from scripts import build_semantic_exercise_index as semantic  # noqa: E402
from scripts import vectorize_exercise_references as sparse  # noqa: E402

DATA = ROOT / "data/exercise-references"
SOURCES = {
    "PMC10801605.xml": (
        "https://www.ebi.ac.uk/europepmc/webservices/rest/PMC10801605/fullTextXML",
        "fc15ccb56e8cf0fe965e440fa18c167ffbe0953a4603e468cfe97fe69c5711fd",
    ),
    "PMC6950543.xml": (
        "https://www.ebi.ac.uk/europepmc/webservices/rest/PMC6950543/fullTextXML",
        "4cb564f9dc5fd035b55614861e54ec7b3934c93eb1f470465500d8221df3c28a",
    ),
    "PMC8990091.xml": (
        "https://www.ebi.ac.uk/europepmc/webservices/rest/PMC8990091/fullTextXML",
        "2022e409ff4b131ad95a98d32f1d6ea23040bc9c1c602043a48d41439e3ed5ca",
    ),
    "free-exercise-db.json": (
        "https://raw.githubusercontent.com/yuhonas/free-exercise-db/main/dist/exercises.json",
        "5bb747e3fc658f095a60dcbf6d53c96627acdcc6ffb6fffde86f7e26995d40bf",
    ),
    "logpress-exercises.json": (
        "https://raw.githubusercontent.com/hasaneyldrm/exercises-dataset/main/data/exercises.json",
        "656634224b8977b99a6d765470ee123260d4979715eaa4e7c0b7c8bb0d79f93d",
    ),
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ensure_sources():
    DATA.mkdir(parents=True, exist_ok=True)
    for name, (url, expected) in SOURCES.items():
        path = DATA / name
        if path.exists() and digest(path) == expected:
            continue
        print(f"Downloading {name}", flush=True)
        with urlopen(url, timeout=120) as response:  # noqa: S310
            content = response.read()
        if hashlib.sha256(content).hexdigest() != expected:
            raise ValueError(f"Downloaded {name} differs from the pinned snapshot")
        temporary = path.with_suffix(path.suffix + ".download")
        temporary.write_bytes(content)
        temporary.replace(path)


def valid_index(path, expected, *, check_count=True):
    try:
        with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as db:
            metadata = dict(db.execute("SELECT key,value FROM metadata"))
            if any(metadata.get(key) != value for key, value in expected.items()):
                return False
            return (
                not check_count
                or int(metadata.get("documents", "0"))
                == db.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
                > 0
            )
    except (sqlite3.Error, OSError, ValueError):
        return False


def prepare():
    ensure_sources()
    source = DATA / "exercise-vectors.sqlite3"
    source_hashes = {name + ".sha256": SOURCES[name][1] for name in sparse.SOURCES}
    if not valid_index(source, {**source_hashes, "algorithm": "tf-idf-l2-v1"}):
        print("Building exercise corpus index", flush=True)
        sparse.build(source)
    provider = OllamaEmbedder()
    expected = {
        **{name + ".sha256": value[1] for name, value in SOURCES.items()},
        "corpus_sha256": digest(source),
        "algorithm": "semantic-cosine-v1",
        "model": provider.model,
        "model_digest": provider.fingerprint(),
    }
    output = DATA / "exercise-semantic.sqlite3"
    if valid_index(output, expected):
        print("Exercise semantic index is ready", flush=True)
        return
    partial = output.with_suffix(output.suffix + ".partial")
    if partial.exists() and not valid_index(
        partial,
        {key: expected[key] for key in ("model", "model_digest", "corpus_sha256")},
        check_count=False,
    ):
        partial.unlink()
    print("Building exercise semantic index", flush=True)
    semantic.build(source, output, provider)


if __name__ == "__main__":
    prepare()
