"""Offline validation for the pinned PMC exercise-technique acquisition."""

import copy
import hashlib
import json

import pytest

from app.modules.knowledge import acquisition_bioc
from app.modules.knowledge.acquisition import (
    CATALOG_PATH,
    AcquisitionError,
    digest,
    validate_packaged_source,
)


def fixture_article(recipe, text="Reviewed fixture procedure."):
    recipe = copy.deepcopy(recipe)
    recipe["selection"]["text_sha256"] = hashlib.sha256(text.encode()).hexdigest()
    names = recipe["source"]["authors"]
    front = {
        "text": recipe["source"]["title"],
        "infons": {
            "type": "front",
            "article-id_doi": recipe["doi"],
            "license": "This article is licensed https://creativecommons.org/licenses/by/4.0/",
            **{
                f"name_{i}": f"surname:{name.split(', ')[0]};given-names:{name.split(', ')[1]}"
                for i, name in enumerate(names)
            },
        },
    }
    document = {
        "id": recipe["pmc"],
        "infons": {"license": "CC BY"},
        "passages": [
            front,
            {
                "text": text,
                "infons": {
                    "section_type": recipe["selection"]["section_type"],
                    "type": "paragraph",
                },
            },
        ],
    }
    return json.dumps([{"documents": [document]}]).encode(), recipe


@pytest.fixture
def recipe():
    return json.loads(acquisition_bioc.RECIPE_PATH.read_text(encoding="utf-8"))


def test_extract_verifies_article_license_authors_and_pinned_passage(recipe):
    body, recipe = fixture_article(recipe)

    chunks, rights = acquisition_bioc.extract(body, recipe)

    assert chunks == [
        {
            "id": recipe["selection"]["id"],
            "section": recipe["selection"]["locator"],
            "content": "Reviewed fixture procedure.",
        }
    ]
    assert "creativecommons.org/licenses/by/4.0" in rights


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("id", "PMC0000000", "article_identity_or_license"),
        ("license", "CC BY-NC", "article_identity_or_license"),
    ],
)
def test_extract_rejects_identity_or_license_mismatch(recipe, field, value, reason):
    body, recipe = fixture_article(recipe)
    document = json.loads(body)[0]["documents"][0]
    if field == "id":
        document["id"] = value
    else:
        document["infons"]["license"] = value

    with pytest.raises(AcquisitionError, match=reason):
        acquisition_bioc.extract(json.dumps([{"documents": [document]}]).encode(), recipe)


def test_extract_rejects_changed_procedure(recipe):
    body, recipe = fixture_article(recipe)
    document = json.loads(body)[0]["documents"][0]
    document["passages"][1]["text"] = "Changed procedure."

    with pytest.raises(AcquisitionError, match="unreviewed_extraction_change"):
        acquisition_bioc.extract(json.dumps([{"documents": [document]}]).encode(), recipe)


def test_unknown_bioc_document_id_requires_matching_pmc_metadata(recipe):
    body, recipe = fixture_article(recipe)
    document = json.loads(body)[0]["documents"][0]
    document["id"] = "unknown"
    document["passages"][0]["infons"]["article-id_pmcid"] = recipe["pmc"]
    acquisition_bioc.extract(json.dumps([{"documents": [document]}]).encode(), recipe)

    document["passages"][0]["infons"]["article-id_pmcid"] = "PMC0000000"
    with pytest.raises(AcquisitionError, match="article_identity_or_license"):
        acquisition_bioc.extract(json.dumps([{"documents": [document]}]).encode(), recipe)


def test_packaged_catalogue_contains_pinned_procedure_and_provenance(recipe):
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    matches = [
        source for source in catalog["sources"] if source["id"] == recipe["source"]["id"]
    ]

    assert len(matches) == 1
    source = matches[0]
    validate_packaged_source(source)
    assert source["license"] == "CC-BY-4.0"
    assert source["provenance"]["repository_identifier"] == recipe["pmc"]
    assert [chunk["id"] for chunk in source["chunks"]] == [recipe["selection"]["id"]]
    assert "independent review" in source["reviewed_by"].lower()


def test_acquisition_is_cached_and_reproducible(recipe, tmp_path, monkeypatch):
    body, recipe = fixture_article(recipe)
    recipe_path = tmp_path / "recipe.json"
    recipe_path.write_text(json.dumps(recipe), encoding="utf-8")
    monkeypatch.setattr(acquisition_bioc, "RECIPE_PATH", recipe_path)
    source, manifest = acquisition_bioc.acquire(cache=tmp_path, fetch=lambda: body)
    again, second_manifest = acquisition_bioc.acquire(
        cache=tmp_path, fetch=lambda: pytest.fail("cached acquisition fetched again")
    )

    assert source["chunks"] == again["chunks"]
    assert manifest["artifact_sha256"] == digest(body)
    assert second_manifest["artifact_sha256"] == manifest["artifact_sha256"]


def test_curl_extracts_only_pinned_protocol_from_mixed_methods(tmp_path, monkeypatch):
    recipe = json.loads(acquisition_bioc.CURL_RECIPE_PATH.read_text(encoding="utf-8"))
    start = recipe["selection"]["start_marker"]
    end = recipe["selection"]["end_marker"]
    paragraph = f"Warm-up with a dose. {start} in a controlled way. {end} Other exercise."
    body, recipe = fixture_article(recipe, text=paragraph)
    excerpt = f"{start} in a controlled way."
    recipe["selection"]["paragraph_sha256"] = digest(paragraph.encode())
    recipe["selection"]["text_sha256"] = digest(excerpt.encode())
    recipe_path = tmp_path / "curl-recipe.json"
    recipe_path.write_text(json.dumps(recipe), encoding="utf-8")
    monkeypatch.setattr(acquisition_bioc, "CURL_RECIPE_PATH", recipe_path)

    source, _ = acquisition_bioc.acquire(
        cache=tmp_path, source_id=acquisition_bioc.CURL_SOURCE_ID, fetch=lambda: body
    )

    assert source["chunks"][0]["content"] == excerpt
    assert "dose" not in source["chunks"][0]["content"]
    with pytest.raises(AcquisitionError, match="unreviewed_extraction_change"):
        acquisition_bioc.extract(body.replace(b"Warm-up", b"Changed"), recipe)


def test_bioc_fetcher_rejects_unknown_endpoint():
    with pytest.raises(AcquisitionError, match="unapproved_article"):
        acquisition_bioc.download(endpoint="https://example.test/unapproved")


@pytest.mark.parametrize("recipe_path", [
    acquisition_bioc.CURL_RECIPE_PATH,
    acquisition_bioc.BODYWEIGHT_RECIPE_PATH,
])
def test_other_bioc_sources_have_valid_pinned_provenance(recipe_path):
    recipe = json.loads(recipe_path.read_text(encoding="utf-8"))
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    source = next(item for item in catalog["sources"] if item["id"] == recipe["source"]["id"])
    validate_packaged_source(source)
    assert source["provenance"]["repository_identifier"] == recipe["pmc"]
    assert digest(source["chunks"][0]["content"].encode()) == recipe["selection"]["text_sha256"]
