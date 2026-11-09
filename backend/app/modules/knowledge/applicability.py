"""Conservative exercise/variant applicability for procedural evidence."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import replace

# A retrieval hit is not proof that a passage teaches the requested movement.
# Add entries only after a source has been reviewed for the exact procedure.
_PROCEDURAL_CHUNKS = {
    "muyor-bench-press-2023-technique": {
        "exercise": "supino",
        "variants": {"barra", "reto", "horizontal"},
    },
    "papadakis-back-squat-older-adults-2024-procedure": {
        "exercise": "agachamento",
        "variants": {"barra", "posterior", "back squat"},
    },
    "santarem-bodyweight-squat-2025-deep-procedure": {
        "exercise": "agachamento_corporal_profundo",
        "variants": {"peso corporal", "sem peso", "profundo"},
    },
    "oliva-lozano-muyor-core-2020-curlup": {
        "exercise": "abdominal_curto",
        "variants": {"abdominal curto", "curl-up", "curl up", "crunch"},
    },
    "oliva-lozano-muyor-core-2020-bridge": {
        "exercise": "hip_bridge",
        "variants": {"ponte", "bridge", "elevacao de quadril no solo"},
    },
    "oliva-lozano-muyor-core-2020-pushup": {
        "exercise": "flexao de bracos",
        "variants": {"flexao de bracos", "flexao de braco", "push-up", "push up"},
    },
    "parpa-dumbbell-curl-2025-procedure": {
        "exercise": "rosca_halteres",
        "variants": {"rosca direta com halteres", "rosca de biceps com halteres"},
    },
}
_TECHNIQUE_INTENT = re.compile(
    r"\b(como|jeito|forma|maneira)\b.{0,50}\b(fazer|faz\w*|executar|realizar|faco|executo)\b"
    r"|\b(como|jeito|forma|maneira)\b.{0,50}\b(exercicio|movimento)\b"
    r"|\b(qual|quais)\b.{0,50}\b(posicao|postura|passos)\b"
    r"|\b(ensine|ensina|explique)\b.{0,50}\b(fazer|executar|realizar)\b"
    r"|\btecnica\b|\bexecucao\b|\bcorret\w*\b",
    re.IGNORECASE,
)


def _normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.casefold())
    return "".join(char for char in value if not unicodedata.combining(char))


def is_procedural_question(query: str) -> bool:
    return bool(_TECHNIQUE_INTENT.search(_normalize(query)))


def exercise_variant_clarification(
    query: str, retrieved_chunks: list[dict[str, object]]
) -> tuple[str, list[str]] | None:
    """Ask a focused variant question when the exercise name is ambiguous."""
    normalized = _normalize(query)
    if not is_procedural_question(query) or not re.search(r"\b(agachamento|squat)\b", normalized):
        return None
    barbell_id = "papadakis-back-squat-older-adults-2024-procedure"
    bodyweight_id = "santarem-bodyweight-squat-2025-deep-procedure"
    available = {chunk.get("chunk_id") for chunk in retrieved_chunks}
    is_bodyweight = any(term in normalized for term in ("peso corporal", "sem peso", "bodyweight"))
    conflicting_equipment = any(
        term in normalized
        for term in (
            "barra", "halter", "smith", "goblet", "salto", "unilateral", "uma perna",
            "um pe", "instavel", "bosu", "parede", "isometr", "sumo", "pistol",
        )
    )
    if (
        is_bodyweight
        and "profund" not in normalized
        and not conflicting_equipment
        and bodyweight_id in available
    ):
        return (
            "Você quer o agachamento profundo com peso corporal? A fonte disponível descreve "
            "essa variação em um estudo com adultos recreacionalmente ativos.",
            [bodyweight_id],
        )
    named_variant = any(
        term in normalized
        for term in (
            "barra",
            "barbell",
            "back squat",
            "goblet",
            "halter",
            "peso corporal",
            "sem peso",
            "bodyweight",
            "smith",
            "frontal",
            "front squat",
            "hack",
            "sumo",
            "unilateral",
            "uma perna",
            "um pe",
            "instavel",
            "bosu",
            "parede",
            "isometr",
            "pistol",
            "salto",
        )
    )
    if named_variant:
        return None
    if barbell_id in available and bodyweight_id in available:
        return (
            "Você quer o agachamento posterior com barra ou o agachamento profundo com peso "
            "corporal? As fontes descrevem essas variações em estudos com públicos diferentes.",
            [barbell_id, bodyweight_id],
        )
    if barbell_id in available:
        return (
            "Você se refere ao agachamento posterior com barra? A fonte disponível descreve essa "
            "variação em um contexto voltado a adultos mais velhos. Informe a variação desejada.",
            [barbell_id],
        )
    if bodyweight_id in available:
        return (
            "Você se refere ao agachamento profundo com peso corporal? A fonte disponível "
            "descreve essa variação em um estudo com adultos recreacionalmente ativos.",
            [bodyweight_id],
        )
    return None


def resolve_variant_reply(message: str, previous_assistant: str) -> str | None:
    """Resolve only short replies to the assistant's own specific clarification."""
    reply = " ".join(re.sub(r"[,.!?]+", " ", _normalize(message)).split())
    previous = _normalize(previous_assistant)
    affirmative = reply in {"sim", "sim por favor", "isso", "isso mesmo"}
    bodyweight_question = "Como fazer agachamento profundo com peso corporal?"
    barbell_question = "Como fazer agachamento posterior com barra?"
    if previous.startswith("voce quer o agachamento profundo com peso corporal?"):
        return bodyweight_question if affirmative else None
    if previous.startswith("voce se refere ao agachamento profundo com peso corporal?"):
        return bodyweight_question if affirmative else None
    if previous.startswith("voce se refere ao agachamento posterior com barra?"):
        return barbell_question if affirmative else None
    if previous.startswith("voce quer o agachamento posterior com barra ou"):
        if reply in {"barra", "com barra", "posterior com barra"}:
            return barbell_question
        if reply in {
            "peso corporal", "com peso corporal", "profundo", "profundo com peso corporal"
        }:
            return bodyweight_question
    return None


def filter_procedural_evidence(
    query: str, chunks: list[dict[str, object]]
) -> list[dict[str, object]]:
    """For technique questions, retain only passages reviewed for that exercise.

    Non-procedural questions keep the ordinary hybrid retrieval result. A named
    unsupported variant cannot inherit support from a different variant.
    """
    normalized = _normalize(query)
    if not _TECHNIQUE_INTENT.search(normalized):
        return chunks

    requested_exercises = [
        exercise
        for exercise, matched in (
            ("supino", bool(re.search(r"\bsupino\b", normalized))),
            ("agachamento", bool(re.search(r"\b(agachamento|squat)\b", normalized))),
            (
                "abdominal_curto",
                any(term in normalized for term in ("abdominal", "curl-up", "curl up", "crunch")),
            ),
            (
                "hip_bridge",
                any(term in normalized for term in ("ponte", "bridge", "elevacao de quadril")),
            ),
            (
                "flexao de bracos",
                any(term in normalized for term in ("flexao de braco", "push-up", "push up")),
            ),
            ("rosca_halteres", "rosca" in normalized),
        )
        if matched
    ]
    if len(requested_exercises) != 1:
        return []
    requested = requested_exercises[0]
    if (
        requested == "agachamento"
        and "profund" in normalized
        and any(term in normalized for term in ("peso corporal", "sem peso", "bodyweight"))
    ):
        requested = "agachamento_corporal_profundo"

    if requested == "supino":
        incompatible = any(
            re.search(rf"\b{variant}\b", normalized)
            for variant in ("halteres", "halter", "maquina", "inclinado", "declinado", "smith")
        )
        if incompatible:
            return []
    elif requested == "agachamento":
        unsupported_variant = any(
            term in normalized
            for term in (
                "goblet",
                "halter",
                "peso corporal",
                "sem peso",
                "smith",
                "frontal",
                "front squat",
                "hack",
                "sumo",
                "unilateral",
                "uma perna",
                "bulgar",
                "caixa",
                "salto",
                "overhead",
            )
        )
        specific_barbell_variant = any(
            term in normalized for term in ("barra", "barbell", "back squat")
        )
        if unsupported_variant or not specific_barbell_variant:
            return []
    elif requested == "agachamento_corporal_profundo":
        if any(
            term in normalized
            for term in (
                "barra", "halter", "smith", "goblet", "salto", "unilateral", "uma perna",
                "um pe", "instavel", "bosu", "parede", "isometr", "sumo", "pistol",
            )
        ):
            return []
    elif requested == "abdominal_curto":
        supported_name = any(
            term in normalized for term in ("abdominal curto", "curl-up", "curl up", "crunch")
        )
        if not supported_name or any(
            term in normalized
            for term in (
                "sit up", "sit-up", "rotacao", "obliqu", "maquina", "bola", "reverso",
                "peso", "carga", "halter",
            )
        ):
            return []
    elif requested == "hip_bridge":
        supported_name = any(
            term in normalized
            for term in (
                "ponte",
                "bridge",
                "elevacao de quadril no solo",
                "elevacao de quadril no chao",
            )
        )
        if not supported_name or any(
            term in normalized
            for term in (
                "hip thrust", "unilateral", "barra", "halter", "bola", "uma perna", "banco",
                "elastico", "faixa", "caneleira", "peso", "carga",
            )
        ):
            return []
    elif requested == "flexao de bracos":
        supported_name = any(
            term in normalized for term in ("flexao de braco", "push-up", "push up")
        )
        unsupported_variant = any(
            term in normalized
            for term in (
                "inclinad", "declinad", "joelho", "suspens", "argola", "parede", "diamante",
                "pike", "unilateral", "elevad", "uma mao", "banco", "halter", "barra",
            )
        )
        if not supported_name or unsupported_variant:
            return []
    elif requested == "rosca_halteres":
        supported_name = "halter" in normalized and any(
            term in normalized for term in ("direta", "biceps")
        )
        unsupported_variant = any(
            term in normalized
            for term in (
                "alternad", "unilateral", "uma mao", "um braco", "martelo", "sentad",
                "banco", "cabo", "polia", "barra", "scott", "inclinad", "elastico",
                "faixa", "concentrad", "invers",
            )
        )
        if not supported_name or unsupported_variant:
            return []
    return [
        chunk
        for chunk in chunks
        if chunk.get("chunk_id") in _PROCEDURAL_CHUNKS
        and _PROCEDURAL_CHUNKS[str(chunk["chunk_id"])]["exercise"] == requested
    ]


def apply_procedural_applicability(context, query: str):
    """Make procedural support depend on a reviewed exercise/variant match."""
    if context.knowledge_status != "supported":
        return context
    chunks = filter_procedural_evidence(query, list(context.chunks))
    normalized = _normalize(query)
    if not _TECHNIQUE_INTENT.search(normalized):
        return context
    if chunks:
        return replace(context, chunks=tuple(chunks))
    from app.modules.knowledge.service import KnowledgeContext

    return KnowledgeContext.empty("insufficient_evidence")
