"""Pinned PMC BioC acquisition for selected exercise procedures."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from datetime import UTC, date, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from app.modules.knowledge.acquisition import (
    CACHE_PATH,
    CATALOG_PATH,
    AcquisitionError,
    digest,
    validate_packaged_source,
    write_json,
)

RECIPE_PATH = Path(__file__).with_name("acquisition-bioc.json")
CURL_RECIPE_PATH = Path(__file__).with_name("acquisition-bioc-curl.json")
BODYWEIGHT_RECIPE_PATH = Path(__file__).with_name("acquisition-bioc-bodyweight-squat.json")
ENDPOINT = (
    "https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/"
    "BioC_json/PMC11587132/unicode"
)
SOURCE_ID = "papadakis-back-squat-older-adults-2024"
CURL_SOURCE_ID = "parpa-dumbbell-curl-2025"
BODYWEIGHT_SOURCE_ID = "santarem-bodyweight-squat-2025"
CORE_SOURCE_ID = "oliva-lozano-muyor-core-exercise-procedures-2020"
CURL_ENDPOINT = (
    "https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/"
    "BioC_json/PMC12550948/unicode"
)
BODYWEIGHT_ENDPOINT = (
    "https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/"
    "BioC_json/PMC11991476/unicode"
)
CORE_ENDPOINT = (
    "https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/"
    "BioC_json/PMC7345922/unicode"
)
MAX_BYTES = 5_000_000
EXTRACTOR = "ncbi-pmc-bioc-pinned-passage/1"


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise AcquisitionError("unapproved_redirect")


def download(*, endpoint=ENDPOINT, opener=None, sleep=time.sleep) -> bytes:
    """Fetch one exact public article endpoint, with one bounded retry."""
    if endpoint not in (ENDPOINT, CURL_ENDPOINT, BODYWEIGHT_ENDPOINT, CORE_ENDPOINT):
        raise AcquisitionError("unapproved_article")
    opener = opener or build_opener(NoRedirects())
    for attempt in range(2):
        try:
            with opener.open(
                Request(endpoint, headers={"User-Agent": "AcademiaEvidence/1.0"}), timeout=30
            ) as response:
                if response.url != endpoint:
                    raise AcquisitionError("unapproved_redirect")
                if response.headers.get_content_type() != "application/json":
                    raise AcquisitionError("unexpected_content_type")
                body = response.read(MAX_BYTES + 1)
                if not body or len(body) > MAX_BYTES:
                    raise AcquisitionError("invalid_artifact_size")
                return body
        except HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504) or attempt:
                raise AcquisitionError("download_http_failure") from error
            retry_after = error.headers.get("Retry-After", "2")
            if not retry_after.isdigit() or int(retry_after) > 30:
                raise AcquisitionError("download_retry_deferred") from error
            sleep(max(2, int(retry_after)))
        except (URLError, TimeoutError, OSError) as error:
            if attempt:
                raise AcquisitionError("download_unavailable") from error
            sleep(2)
    raise AcquisitionError("download_unavailable")


def extract(body: bytes, recipe: dict) -> tuple[list[dict], str]:
    """Validate article identity/licence and extract only the pinned prose passage."""
    if not body or len(body) > MAX_BYTES:
        raise AcquisitionError("invalid_artifact_size")
    try:
        collection = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise AcquisitionError("invalid_bioc_artifact") from error
    if not isinstance(collection, list) or len(collection) != 1:
        raise AcquisitionError("invalid_bioc_collection")
    documents = collection[0].get("documents")
    if not isinstance(documents, list) or len(documents) != 1:
        raise AcquisitionError("article_identity_mismatch")
    document = documents[0]
    passages = document.get("passages", [])
    front = next(
        (
            passage
            for passage in passages
            if passage.get("infons", {}).get("type") == "front"
        ),
        None,
    )
    if not isinstance(front, dict):
        raise AcquisitionError("missing_article_metadata")
    info = front.get("infons", {})
    rights = info.get("license", "")
    expected = recipe["source"]
    valid_pmc = document.get("id") == recipe["pmc"] or (
        document.get("id") == "unknown" and info.get("article-id_pmcid") == recipe["pmc"]
    )
    if (
        not valid_pmc
        or info.get("article-id_doi") != recipe["doi"]
        or front.get("text") != expected["title"]
        or document.get("infons", {}).get("license") != "CC BY"
        or "creativecommons.org/licenses/by/4.0" not in rights
        or re.search(r"by-nc|by-nd|noncommercial|noderivatives", rights, re.IGNORECASE)
        or expected["license"] != "CC-BY-4.0"
    ):
        raise AcquisitionError("unverified_article_identity_or_license")
    names = [
        info.get(f"name_{index}", "")
        for index in range(len(expected["authors"]))
    ]
    if any(
        f"surname:{author.split(', ')[0]}" not in name
        or f"given-names:{author.split(', ', 1)[1]}" not in name
        for author, name in zip(expected["authors"], names, strict=True)
    ):
        raise AcquisitionError("article_authors_mismatch")
    selection = recipe["selection"]
    matches = []
    for passage in passages:
        if (
            passage.get("infons", {}).get("section_type") != selection["section_type"]
            or passage.get("infons", {}).get("type") != "paragraph"
        ):
            continue
        content = passage.get("text", "")
        if "start_marker" in selection:
            start, end = selection["start_marker"], selection["end_marker"]
            if (
                digest(content.encode()) != selection["paragraph_sha256"]
                or content.count(start) != 1
                or content.count(end) != 1
                or content.index(start) >= content.index(end)
            ):
                continue
            content = content[content.index(start) : content.index(end)].strip()
        if hashlib.sha256(content.encode()).hexdigest() == selection["text_sha256"]:
            matches.append(content)
    if len(matches) != 1:
        raise AcquisitionError("unreviewed_extraction_change")
    chunk = {
        "id": selection["id"],
        "section": selection["locator"],
        "content": matches[0],
    }
    return [chunk], rights


def acquire(*, cache: Path, source_id=SOURCE_ID, refresh=False, fetch=None) -> tuple[dict, dict]:
    approved = {
        SOURCE_ID: (RECIPE_PATH, ENDPOINT, "PMC11587132"),
        CURL_SOURCE_ID: (CURL_RECIPE_PATH, CURL_ENDPOINT, "PMC12550948"),
        BODYWEIGHT_SOURCE_ID: (BODYWEIGHT_RECIPE_PATH, BODYWEIGHT_ENDPOINT, "PMC11991476"),
    }
    if source_id not in approved:
        raise AcquisitionError("unapproved_article")
    recipe_path, endpoint, pmc = approved[source_id]
    recipe = json.loads(recipe_path.read_text(encoding="utf-8"))
    if recipe.get("source", {}).get("id") != source_id or recipe.get("pmc") != pmc:
        raise AcquisitionError("unapproved_article")
    manifest_path = cache / f"{source_id}-manifest.json"
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
        body = fetch() if fetch is not None else download(endpoint=endpoint)
        captured = datetime.now(UTC).isoformat()
    chunks, rights = extract(body, recipe)
    source_meta = recipe["source"]
    if (
        source_meta["review_status"] != "approved"
        or not source_meta["commercial_use_allowed"]
        or not source_meta["reviewed_by"].strip()
        or not date.fromisoformat(source_meta["reviewed_at"])
        <= date.today()
        < date.fromisoformat(source_meta["review_due_at"])
    ):
        raise AcquisitionError("source_review_not_current")
    artifact_hash = digest(body)
    manifest = {
        "version": 1,
        "source_id": source_id,
        "doi": recipe["doi"],
        "repository_identifier": recipe["pmc"],
        "requested_url": endpoint,
        "captured_at": captured,
        "artifact_file": artifact_hash + ".json",
        "artifact_sha256": artifact_hash,
        "artifact_bytes": len(body),
        "media_type": "application/json",
        "extractor": EXTRACTOR,
        "license": source_meta["license"],
        "license_url": source_meta["license_url"],
        "license_evidence": rights,
        "license_evidence_sha256": digest(rights.encode()),
        "recipe_sha256": digest(json.dumps(recipe, sort_keys=True).encode()),
        "scientific_approval": "source-authored-procedure; independent-translation-review-pending",
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
    source = {
        **source_meta,
        "chunks": chunks,
        "captured_at": captured[:10],
        "provenance": manifest,
    }
    validate_packaged_source(source)
    return source, manifest


def publish(source: dict, catalog_path: Path = CATALOG_PATH) -> None:
    source_id = source.get("id")
    if source_id not in (SOURCE_ID, CURL_SOURCE_ID, BODYWEIGHT_SOURCE_ID, CORE_SOURCE_ID):
        raise AcquisitionError("unapproved_article")
    validate_packaged_source(source)
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    entries = catalog["sources"]
    positions = [i for i, entry in enumerate(entries) if entry["id"] == source_id]
    if len(positions) > 1:
        raise AcquisitionError("duplicate_catalog_source")
    if positions:
        entries[positions[0]] = source
    else:
        entries.append(source)
    write_json(catalog_path, catalog)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source", choices=(SOURCE_ID, CURL_SOURCE_ID, BODYWEIGHT_SOURCE_ID), default=SOURCE_ID
    )
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()
    source, manifest = acquire(
        cache=CACHE_PATH / "bioc", source_id=args.source, refresh=args.refresh
    )
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
