"""Exercise source acquisition uses bounded, pinned, licensed material."""

import copy
import json

import pytest

from app.modules.knowledge import acquisition_core_exercises as acquisition
from app.modules.knowledge.acquisition import (
    CATALOG_PATH,
    AcquisitionError,
    digest,
    validate_packaged_source,
)


@pytest.fixture
def article():
    recipe = json.loads(acquisition.RECIPE_PATH.read_text(encoding="utf-8"))
    recipe = copy.deepcopy(recipe)
    rows = []
    for index, selection in enumerate(recipe["selections"]):
        text = f"Fixture procedure {index}."
        raw = text + " This exercise may vary in the studies."
        selection["row_sha256"] = digest(raw.encode())
        selection["text_sha256"] = digest(text.encode())
        rows.append(selection["exercise"] + "\t" + raw)
    table = "\t \t".join(rows)
    front = {
        "text": recipe["title"],
        "infons": {
            "type": "front",
            "article-id_doi": recipe["doi"],
            "license": "https://creativecommons.org/licenses/by/4.0/",
            "name_0": "surname:Oliva-Lozano;given-names:José",
            "name_1": "surname:Muyor;given-names:José",
        },
    }
    document = {
        "id": recipe["pmc"],
        "infons": {"license": "CC BY"},
        "passages": [front, {"infons": {"type": "table"}, "text": table}],
    }
    return json.dumps([{"documents": [document]}]).encode(), recipe


def test_extract_pins_selected_rows_and_excludes_other_variations(article):
    body, recipe = article
    chunks, rights = acquisition.extract(body, recipe)

    assert [chunk["content"] for chunk in chunks] == [
        "Fixture procedure 0.",
        "Fixture procedure 1.",
        "Fixture procedure 2.",
    ]
    assert "creativecommons.org/licenses/by/4.0" in rights


@pytest.mark.parametrize("replacement", ["CC BY-NC", "CC BY-SA"])
def test_rejects_unverified_item_license(article, replacement):
    body, recipe = article
    value = json.loads(body)
    value[0]["documents"][0]["infons"]["license"] = replacement

    with pytest.raises(AcquisitionError, match="identity_or_license"):
        acquisition.extract(json.dumps(value).encode(), recipe)


def test_rejects_changed_or_duplicate_table_row(article):
    body, recipe = article
    with pytest.raises(AcquisitionError, match="unreviewed_extraction_change"):
        acquisition.extract(body.replace(b"Fixture procedure 1", b"Changed procedure 1"), recipe)
    with pytest.raises(AcquisitionError, match="duplicate_procedure_table_row"):
        acquisition.table_rows("Bridge\tFirst\t \tBridge\tSecond")


def test_acquisition_is_idempotent_and_cache_hash_is_checked(article, tmp_path, monkeypatch):
    body, recipe = article
    recipe_path = tmp_path / "recipe.json"
    recipe_path.write_text(json.dumps(recipe), encoding="utf-8")
    monkeypatch.setattr(acquisition, "RECIPE_PATH", recipe_path)
    source, manifest = acquisition.acquire(cache=tmp_path, fetch=lambda: body)
    again, _ = acquisition.acquire(
        cache=tmp_path, fetch=lambda: pytest.fail("cached acquisition used the network")
    )
    assert source["chunks"] == again["chunks"]
    (tmp_path / manifest["artifact_file"]).write_bytes(b"changed")
    with pytest.raises(AcquisitionError, match="cached_artifact_integrity_failure"):
        acquisition.acquire(cache=tmp_path)


def test_catalogue_preserves_source_provenance():
    recipe = json.loads(acquisition.RECIPE_PATH.read_text(encoding="utf-8"))
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    source = next(source for source in catalog["sources"] if source["id"] == acquisition.SOURCE_ID)
    validate_packaged_source(source)
    assert [chunk["id"] for chunk in source["chunks"]] == [
        item["id"] for item in recipe["selections"]
    ]
    source.pop("provenance")
    with pytest.raises(AcquisitionError, match="missing_artifact_provenance"):
        validate_packaged_source(source)
