"""Pinned, text-only acquisition of exercise procedures from a CC BY review."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import UTC, date, datetime
from pathlib import Path

from app.modules.knowledge.acquisition import (
    CACHE_PATH,
    AcquisitionError,
    digest,
    validate_packaged_source,
    write_json,
)
from app.modules.knowledge.acquisition_bioc import (
    CORE_ENDPOINT as ENDPOINT,
)
from app.modules.knowledge.acquisition_bioc import (
    CORE_SOURCE_ID as SOURCE_ID,
)
from app.modules.knowledge.acquisition_bioc import download, publish

RECIPE_PATH = Path(__file__).with_name("acquisition-core-exercises.json")
MAX_BYTES = 5_000_000
EXTRACTOR = "ncbi-pmc-bioc-table-rows/1"


def table_rows(table_text: str) -> dict[str, str]:
    rows: dict[str, str] = {}
    for row in table_text.split("\t \t"):
        cells = row.split("\t", 1)
        if len(cells) != 2:
            continue
        name, description = (cell.strip() for cell in cells)
        if name and description:
            if name in rows:
                raise AcquisitionError("duplicate_procedure_table_row")
            rows[name] = description
    return rows


def extract(body: bytes, recipe: dict) -> tuple[list[dict], str]:
    if not body or len(body) > MAX_BYTES:
        raise AcquisitionError("invalid_artifact_size")
    try:
        collection = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise AcquisitionError("invalid_bioc_artifact") from error
    if not isinstance(collection, list) or len(collection) != 1:
        raise AcquisitionError("invalid_bioc_collection")
    docs = collection[0].get("documents")
    if not isinstance(docs, list) or len(docs) != 1:
        raise AcquisitionError("article_identity_mismatch")
    doc = docs[0]
    passages = doc.get("passages", [])
    front = next(
        (p for p in passages if p.get("infons", {}).get("type") == "front"), None
    )
    if not front:
        raise AcquisitionError("missing_article_metadata")
    info = front.get("infons", {})
    license_text = info.get("license", "")
    if (
        doc.get("id") != recipe["pmc"]
        or info.get("article-id_doi") != recipe["doi"]
        or front.get("text") != recipe["title"]
        or doc.get("infons", {}).get("license") != "CC BY"
        or "creativecommons.org/licenses/by/4.0" not in license_text
        or re.search(r"by-nc|by-nd|noncommercial|noderivatives", license_text, re.IGNORECASE)
        or recipe["source"]["license"] != "CC-BY-4.0"
    ):
        raise AcquisitionError("unverified_article_identity_or_license")
    for index, surname in enumerate(recipe["author_surnames"]):
        if f"surname:{surname}" not in info.get(f"name_{index}", ""):
            raise AcquisitionError("article_authors_mismatch")
    tables = [
        p["text"]
        for p in passages
        if p.get("infons", {}).get("type") == "table"
        and p.get("text", "").startswith("Curl-Up or Crunch\t")
    ]
    if len(tables) != 1:
        raise AcquisitionError("missing_or_ambiguous_procedure_table")
    rows = table_rows(tables[0])
    chunks = []
    for selection in recipe["selections"]:
        raw = rows.get(selection["exercise"])
        if not raw or hashlib.sha256(raw.encode()).hexdigest() != selection["row_sha256"]:
            raise AcquisitionError("unreviewed_extraction_change")
        content = raw.split(" This exercise may vary", 1)[0].strip()
        if not content or "\ufffd" in content:
            raise AcquisitionError("invalid_extracted_text")
        if hashlib.sha256(content.encode()).hexdigest() != selection["text_sha256"]:
            raise AcquisitionError("unreviewed_extraction_change")
        chunks.append(
            {
                "id": selection["id"],
                "section": selection["locator"],
                "content": content,
            }
        )
    return chunks, license_text


def acquire(*, cache: Path, refresh=False, fetch=None) -> tuple[dict, dict]:
    recipe = json.loads(RECIPE_PATH.read_text(encoding="utf-8"))
    if recipe.get("source", {}).get("id") != SOURCE_ID:
        raise AcquisitionError("unapproved_article")
    manifest_path = cache / f"{SOURCE_ID}-manifest.json"
    if manifest_path.exists() and not refresh:
        prior = json.loads(manifest_path.read_text(encoding="utf-8"))
        artifact_hash = prior.get("artifact_sha256", "")
        if not re.fullmatch(r"[a-f0-9]{64}", artifact_hash):
            raise AcquisitionError("invalid_cached_artifact_path")
        body = (cache / (artifact_hash + ".json")).read_bytes()
        if digest(body) != artifact_hash:
            raise AcquisitionError("cached_artifact_integrity_failure")
        captured = prior["captured_at"]
    else:
        body = fetch() if fetch is not None else download(endpoint=ENDPOINT)
        captured = datetime.now(UTC).isoformat()
    chunks, rights = extract(body, recipe)
    meta = recipe["source"]
    if (
        meta["review_status"] != "approved"
        or not meta["commercial_use_allowed"]
        or not meta["reviewed_by"].strip()
        or not date.fromisoformat(meta["reviewed_at"])
        <= date.today()
        < date.fromisoformat(meta["review_due_at"])
    ):
        raise AcquisitionError("source_review_not_current")
    artifact_hash = digest(body)
    manifest = {
        "version": 1,
        "source_id": SOURCE_ID,
        "doi": recipe["doi"],
        "repository_identifier": recipe["pmc"],
        "requested_url": ENDPOINT,
        "captured_at": captured,
        "artifact_file": artifact_hash + ".json",
        "artifact_sha256": artifact_hash,
        "artifact_bytes": len(body),
        "media_type": "application/json",
        "extractor": EXTRACTOR,
        "license": meta["license"],
        "license_url": meta["license_url"],
        "license_evidence": rights,
        "license_evidence_sha256": digest(rights.encode()),
        "recipe_sha256": digest(json.dumps(recipe, sort_keys=True).encode()),
        "scientific_approval": (
            "peer-reviewed-review-table; exercise-specific-translation-review-pending"
        ),
        "chunks": [
            {
                "id": chunk["id"],
                "locator": chunk["section"],
                "text_sha256": digest(chunk["content"].encode()),
            }
            for chunk in chunks
        ],
    }
    cache.mkdir(parents=True, exist_ok=True)
    artifact_path = cache / manifest["artifact_file"]
    temporary = artifact_path.with_suffix(".json.tmp")
    temporary.write_bytes(body)
    temporary.replace(artifact_path)
    write_json(manifest_path, manifest)
    source = {**meta, "chunks": chunks, "captured_at": captured[:10], "provenance": manifest}
    validate_packaged_source(source)
    return source, manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()
    source, manifest = acquire(cache=CACHE_PATH / "core-exercises", refresh=args.refresh)
    if args.publish:
        publish(source)
    print(
        json.dumps(
            {
                "source_id": source["id"],
                "chunks": len(source["chunks"]),
                "artifact_sha256": manifest["artifact_sha256"],
                "published": args.publish,
            }
        )
    )


if __name__ == "__main__":
    main()
