"""Semantic retrieval from the versioned public exercise corpus."""

from __future__ import annotations

import hashlib
import math
import os
import re
import sqlite3
import struct
import unicodedata
from functools import lru_cache
from pathlib import Path

from app.integrations.embeddings import EmbeddingError, OllamaEmbedder

DEFAULT_INDEX = (
    Path(__file__).resolve().parents[3] / "data/exercise-references/exercise-semantic.sqlite3"
)
ALIASES = {
    "agachamento": "squat",
    "stiff": "romanian deadlift",
    "supino": "bench press",
    "levantamento terra": "deadlift",
    "rosca": "curl",
    "rosca direta": "barbell curl",
    "flexao": "pushup",
    "barra fixa": "pull up",
    "puxada": "pulldown",
    "remada": "row",
    "cadeira extensora": "leg extension",
    "mesa flexora": "leg curl",
    "elevacao pelvica": "hip thrust",
    "burpee": "burpee",
    "afundo": "lunge",
    "avanco": "lunge",
    "panturrilha": "calf raise",
    "desenvolvimento": "shoulder press",
    "triceps": "triceps",
    "biceps": "biceps",
    "leg press": "leg press",
    "prancha": "plank",
    "abdominal": "crunch",
    "elevacao lateral": "lateral raise",
}
PREFERRED_SECTIONS = {
    ("barbell", "curl"): "Barbell Curl",
    ("bench", "press"): "Barbell Bench Press - Medium Grip",
    ("burpee",): "burpee",
    ("calf", "raise"): "Standing Calf Raises",
    ("deadlift",): "Barbell Deadlift",
    ("lateral", "raise"): "Side Lateral Raise",
    ("lunge",): "Bodyweight Walking Lunge",
    ("hip", "thrust"): "Barbell Hip Thrust",
    ("curl", "leg"): "Lying Leg Curls",
    ("extension", "leg"): "Leg Extensions",
    ("leg", "press"): "Leg Press",
    ("pull", "up"): "Weighted Pull Ups",
    ("pulldown",): "Wide-Grip Lat Pulldown",
    ("pushup",): "Pushups",
    ("row",): "Bent Over Barbell Row",
    ("deadlift", "romanian"): "Romanian Deadlift",
    ("press", "shoulder"): "Dumbbell Shoulder Press",
    ("squat",): "Bodyweight Squat",
    ("curl",): "Barbell Curl",
    ("triceps",): "Triceps Pushdown - Rope Attachment",
}
SOURCE_LABELS = {
    "PMC10801605.xml": (
        "Androulakis-Korakakis et al., Optimizing Resistance Training Technique (2024)"
    ),
    "PMC6950543.xml": "Krzysztofik et al., Maximizing Muscle Hypertrophy (2019)",
    "PMC8990091.xml": "Stassen et al., Attention to Progression Principles (2022)",
    "free-exercise-db.json": "Free Exercise DB (versão de 13/11/2026)",
    "logpress-exercises.json": "LogPress Exercise Dataset (versão de 13/11/2026)",
}


def _normalize(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", text.casefold()) if not unicodedata.combining(c)
    )


def _title_matches(required: set[str], title_terms: set[str]) -> bool:
    """Match exercise tokens despite ordinary English plurals in catalogue titles."""
    for term in required:
        variants = {term, term + "s"}
        if term.endswith("y"):
            variants.add(term[:-1] + "ies")
        if term.endswith("s"):
            variants.add(term[:-1])
        if not variants.intersection(title_terms):
            return False
    return True


def exercise_query(message: str) -> str | None:
    text = _normalize(message)
    matches = [
        (len(key), key, value)
        for key, value in ALIASES.items()
        if re.search(r"\b" + re.escape(key) + r"\b", text)
    ]
    is_question = "?" in text or bool(
        re.search(
            r"\b(como|execut|fazer|faco|tecnica|exercicio|carga|peso|repet|serie|"
            r"progress|dica|substit|movimento|muscul|along|aquec)\w*\b",
            text,
        )
    )
    if not is_question:
        return None
    if matches:
        _, name, alias = max(matches)
        qualifiers = []
        for expression, value in (
            (r"\bhalter(?:es)?\b", "halteres"),
            (r"\bcom barra\b", "com barra"),
            (r"\belastico\b", "elastico"),
            (r"\balong\w*\b", "alongamento stretch"),
            (r"\bsumo\b", "sumo"),
            (r"\bfrontal\b", "front"),
            (r"\bbulgar\w*\b", "bulgarian"),
            (r"\binclinad\w*\b", "incline"),
            (r"\bdeclinad\w*\b", "decline"),
            (r"\bunilateral\b", "single"),
            (r"\bpolia\b", "cable"),
            (r"\b(carga|peso)\w*\b", "carga"),
            (r"\brepet\w*\b", "repeticoes"),
            (r"\bprogress\w*\b", "progressao"),
        ):
            if re.search(expression, text):
                qualifiers.append(value)
        return " ".join([name, *qualifiers]) + " | exercise: " + alias
    if re.search(r"\b(agora|nesse caso|neste caso)\b", text):
        return None
    if re.search(r"\b(minha ficha|meu plano|minhas series|meu treino)\b", text) and not re.search(
        r"\b(exercicio|execut|faco|fazer|progress|aument|peso|carga)\w*\b", text
    ):
        return None
    # English names and gym terminology can be matched directly by the index.
    if re.search(
        r"\b(exercicio|execut|fazer|faco|tecnica|carga|peso|repet|serie|progress|"
        r"trein|dica|substit|movimento|muscul|along|aquec)\w*\b",
        text,
    ):
        sanitized = re.sub(r"[\w.+-]+@[\w.-]+\.[a-z]{2,}", " ", message, flags=re.I)
        sanitized = re.sub(r"\b\d[\d.()\-\s]{7,}\d\b", " ", sanitized)
        return sanitized[:400]
    return None


@lru_cache(maxsize=32)
def _source_hash(path: str, modified: int, size: int) -> str:
    del modified, size
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def evidence_matches(pairs: list[tuple[str, str]], *, embedder=None, threshold=0.63) -> bool:
    """Reject clearly unrelated claims; similarity is not proof of entailment."""
    try:
        provider = embedder or OllamaEmbedder()
        vectors = provider.embed([text for pair in pairs for text in pair])
        if len(vectors) != len(pairs) * 2:
            return False
        for index in range(0, len(vectors), 2):
            first, second = vectors[index : index + 2]
            if len(first) != len(second):
                return False
            similarity = sum(a * b for a, b in zip(first, second, strict=True))
            if not math.isfinite(similarity) or similarity < threshold:
                return False
        return bool(pairs)
    except (EmbeddingError, ValueError, TypeError, IndexError):
        return False


def retrieve(query: str, *, limit: int = 3, embedder=None) -> list[dict[str, str]]:
    path = Path(os.environ.get("EXERCISE_VECTOR_INDEX", str(DEFAULT_INDEX))).resolve()
    try:
        provider = embedder or OllamaEmbedder()
        revoked = {
            item.strip()
            for item in os.environ.get("EXERCISE_REVOKED_SOURCES", "").split(",")
            if item.strip()
        }
        threshold = float(os.environ.get("EXERCISE_SIMILARITY_THRESHOLD", "0.55"))
        marker = " | exercise: "
        named = query.rsplit(marker, 1)[-1] if marker in query else ""
        required = set(re.findall(r"[^\W_]+", named.casefold()))
        equipment = None
        normalized_query = _normalize(query.split(marker, 1)[0])
        explicit_exercise = re.search(
            r"\bexercicio\s+(?:chamado\s+)?([a-z]{4,})\b", normalized_query
        )
        unknown_name = explicit_exercise.group(1) if not required and explicit_exercise else ""
        if unknown_name in {"para", "esse", "esta", "mais", "ideal", "certo"}:
            unknown_name = ""
        for expression, term in (
            (r"\bhalter(?:es)?\b", "dumbbell"),
            (r"\bcom barra\b", "barbell"),
            (r"\belastico\b", "band"),
        ):
            if re.search(expression, normalized_query):
                equipment = term
                break
        variation = next(
            (term for term in ("sumo", "front", "bulgarian", "incline", "decline", "cable")
             if re.search(r"\b" + term + r"\b", normalized_query)),
            None,
        )
        preferred_section = PREFERRED_SECTIONS.get(tuple(sorted(required)))
        if variation is None:
            if required == {"squat"}:
                preferred_section = (
                    "Dumbbell Squat" if equipment == "dumbbell" else
                    "Barbell Squat" if equipment == "barbell" else
                    "Bodyweight Squat"
                )
            elif required == {"bench", "press"}:
                preferred_section = (
                    "Dumbbell Bench Press" if equipment == "dumbbell" else
                    "Barbell Bench Press - Medium Grip"
                )
            elif required == {"curl"} and equipment == "dumbbell":
                preferred_section = "Dumbbell Bicep Curl"
            elif required == {"calf", "raise"} and equipment == "dumbbell":
                preferred_section = "Standing Dumbbell Calf Raise"
        search_terms = [normalized_query, "exercise " + " ".join(sorted(required))]
        if variation == "bulgarian":
            search_terms.append("bulgarian split squat rear foot elevated")
        elif preferred_section:
            search_terms.append(preferred_section + " exercise instructions how to perform")
        search_text = " ".join(search_terms)
        with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as db:
            metadata = dict(db.execute("SELECT key,value FROM metadata"))
            if (
                metadata.get("model") != provider.model
                or metadata.get("algorithm") != "semantic-cosine-v1"
            ):
                return []
            expected_count = int(metadata.get("documents", "0"))
            if (
                expected_count < 1
                or db.execute("SELECT COUNT(*) FROM documents").fetchone()[0] != expected_count
            ):
                return []
            if metadata.get("model_digest") and metadata["model_digest"] != provider.fingerprint():
                return []
            for key, digest in metadata.items():
                if key.endswith(".xml.sha256") or key.endswith(".json.sha256"):
                    source_file = path.parent / key.removesuffix(".sha256")
                    if source_file.exists():
                        stat = source_file.stat()
                        if _source_hash(str(source_file), stat.st_mtime_ns, stat.st_size) != digest:
                            return []
            vector = provider.embed(["task: search result | query: " + search_text])[0]
            scores = []
            for source, source_id, section, url, text, blob in db.execute(
                "SELECT source,source_id,section,url,text,vector FROM documents"
            ):
                if source in revoked or len(blob) != len(vector) * 4:
                    continue
                if re.search(
                    r"\b(ignore|ignorem|desconsidere)\b.{0,80}\b"
                    r"(instructions|instrucoes|system prompt|developer)\b",
                    " ".join(_normalize(text).split()),
                ):
                    continue
                title_terms = set(re.findall(r"[^\W_]+", section.casefold()))
                if unknown_name and unknown_name not in _normalize(section).split():
                    continue
                if required and not source.startswith("PMC") and not _title_matches(
                    required, title_terms
                ):
                    continue
                if equipment and not source.startswith("PMC") and not _title_matches(
                    {equipment}, title_terms
                ):
                    continue
                if variation and not source.startswith("PMC"):
                    if variation == "bulgarian":
                        normalized_text = _normalize(text)
                        elevated_rear_foot = (
                            "split" in title_terms
                            and "squat" in title_terms
                            and (
                                "rear foot elevated" in normalized_text
                                or "top of your foot on the bench" in normalized_text
                                or "other leg back" in normalized_text
                            )
                        )
                        if not elevated_rear_foot:
                            continue
                    elif not _title_matches({variation}, title_terms):
                        continue
                candidate = struct.unpack(f"<{len(vector)}f", blob)
                score = sum(a * b for a, b in zip(vector, candidate, strict=True))
                is_canonical = (
                    preferred_section and section.casefold() == preferred_section.casefold()
                )
                minimum_score = min(threshold, 0.30) if is_canonical else threshold
                if math.isfinite(score) and score >= minimum_score:
                    scores.append((score, source, source_id, section, url, text))
        scores.sort(
            key=lambda row: (
                row[3].casefold() == preferred_section.casefold()
                if preferred_section
                else False,
                row[0],
            ),
            reverse=True,
        )
        results = []
        seen = set()
        for _, source, source_id, section, url, text in scores:
            if (source, source_id) in seen:
                continue
            seen.add((source, source_id))
            results.append(
                {
                    "source": source,
                    "title": SOURCE_LABELS.get(source, source),
                    "section": section,
                    "url": url,
                    "text": text[:2500],
                }
            )
            if len(results) >= limit:
                break
        return results
    except (
        OSError,
        sqlite3.Error,
        ValueError,
        TypeError,
        IndexError,
        struct.error,
        EmbeddingError,
    ):
        return []
