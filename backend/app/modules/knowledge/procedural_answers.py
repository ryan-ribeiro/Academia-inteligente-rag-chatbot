"""Deterministic, reviewed answer templates for narrowly covered procedures."""

from __future__ import annotations

BENCH_PRESS_PROCEDURE_ID = "muyor-bench-press-2023-technique"
BACK_SQUAT_PROCEDURE_ID = "papadakis-back-squat-older-adults-2024-procedure"
BODYWEIGHT_SQUAT_PROCEDURE_ID = "santarem-bodyweight-squat-2025-deep-procedure"
CURLUP_PROCEDURE_ID = "oliva-lozano-muyor-core-2020-curlup"
BRIDGE_PROCEDURE_ID = "oliva-lozano-muyor-core-2020-bridge"
PUSHUP_PROCEDURE_ID = "oliva-lozano-muyor-core-2020-pushup"
CURL_PROCEDURE_ID = "parpa-dumbbell-curl-2025-procedure"


def reviewed_procedural_answer(
    question: str,
    chunks: tuple[dict[str, object], ...],
    onboarding: dict[str, object] | None = None,
):
    """Describe only the exact procedure supported by a retrieved passage."""
    from app.integrations.ai import AiTrainingChatResponse
    from app.modules.knowledge.applicability import (
        filter_procedural_evidence,
        is_procedural_question,
    )

    if not is_procedural_question(question):
        return None
    eligible = filter_procedural_evidence(question, list(chunks))
    if len(eligible) != 1:
        return None
    chunk_id = eligible[0].get("chunk_id")
    health_fields = ("limitations_or_complaints", "health_conditions", "medications")
    has_health_context = bool(
        onboarding
        and any(onboarding.get(field) not in (None, "", [], {}) for field in health_fields)
    )
    individual_context = (
        " Seu onboarding contém informações de saúde que esta fonte não avaliou; peça ao "
        "instrutor que as considere ao avaliar qualquer adaptação."
        if has_health_context
        else ""
    )
    if chunk_id == BENCH_PRESS_PROCEDURE_ID:
        answer = (
            "A fonte disponível descreve o supino horizontal com barra: deite-se no banco e "
            "segure a barra com os polegares envolvendo-a. Desça a barra até perto do peito, "
            "mantendo os ombros a aproximadamente 45° do tronco, e depois estenda os cotovelos. "
            "Esse foi o protocolo de um estudo com 20 adultos fisicamente ativos; não define "
            "uma técnica universal nem avalia sua situação individual. Para adaptar a execução, "
            "consulte seu instrutor."
        )
    elif chunk_id == BACK_SQUAT_PROCEDURE_ID:
        answer = (
            "O artigo citado descreve o agachamento posterior com barra em um contexto clínico "
            "voltado a adultos mais velhos: a barra fica apoiada na parte superior das costas, "
            "com as mãos aproximadamente na largura dos ombros ou um pouco além. O tronco "
            "permanece firme durante a descida controlada, com flexão de quadris, joelhos e "
            "tornozelos até as coxas ficarem paralelas ao chão ou um pouco abaixo. Na subida, "
            "essas articulações se estendem, com tronco firme e quadris e ombros subindo juntos. "
            "Essa é uma descrição do artigo, não uma avaliação individual nem uma "
            "recomendação universal; ela não cobre agachamento com peso corporal, goblet ou "
            "Smith. Consulte seu instrutor para avaliar adaptações."
        )
    elif chunk_id == BODYWEIGHT_SQUAT_PROCEDURE_ID:
        answer = (
            "O estudo citado descreve o agachamento profundo com peso corporal em superfície "
            "estável, com pés afastados na largura dos ombros, peito erguido e joelhos apontando "
            "para fora. O tronco acompanha a direção das canelas durante o movimento. Na "
            "descida, os participantes usaram uma fita como referência e um ângulo de quadril "
            "de aproximadamente 110°. A pesquisa envolveu 15 adultos recreacionalmente ativos; "
            "essa profundidade não é uma recomendação individual e a fonte não detalha todas as "
            "fases da execução. Consulte seu instrutor para avaliar sua técnica e adaptações."
        )
    elif chunk_id in (CURLUP_PROCEDURE_ID, BRIDGE_PROCEDURE_ID, PUSHUP_PROCEDURE_ID):
        descriptions = {
            CURLUP_PROCEDURE_ID: (
                "No abdominal curto descrito, a pessoa fica deitada de costas, com os pés no "
                "chão afastados na largura do quadril e os joelhos flexionados. A parte superior "
                "do tronco é elevada com as mãos atrás do pescoço e retorna à posição inicial."
            ),
            BRIDGE_PROCEDURE_ID: (
                "Na ponte de quadril descrita, a pessoa fica deitada de costas, com joelhos "
                "flexionados e pés no chão. O quadril é elevado, formando uma linha entre os "
                "ombros e os joelhos."
            ),
            PUSHUP_PROCEDURE_ID: (
                "Na flexão de braços descrita, a pessoa começa de frente para o chão, com "
                "cotovelos estendidos e as pontas dos pés afastadas na largura dos ombros. "
                "O corpo desce com a flexão dos cotovelos e sobe com a extensão deles. A fonte "
                "não especifica o posicionamento das mãos."
            ),
        }
        answer = (
            "A revisão citada reúne procedimentos de estudos com adultos saudáveis. "
            + descriptions[chunk_id]
            + " Ela descreve protocolos de pesquisa e não avalia sua situação individual. "
            "Para orientação e adaptações, consulte seu instrutor."
        )
    elif chunk_id == CURL_PROCEDURE_ID:
        answer = (
            "O estudo citado descreve a rosca em pé com um halter em cada mão, palmas voltadas "
            "para a frente e pés afastados na largura dos ombros. Os braços começam estendidos "
            "ao lado do corpo, com cotovelos próximos ao tronco; os halteres sobem em direção "
            "aos ombros ao flexionar os cotovelos e descem de forma controlada. O protocolo "
            "foi usado com homens fisicamente ativos e treinados, de 20 a 40 anos. A descrição "
            "não avalia sua situação individual nem cobre outras variações; consulte seu "
            "instrutor para orientação e adaptações."
        )
    else:
        return None
    return AiTrainingChatResponse(
        assistant_message=answer + individual_context,
        citations=[str(chunk_id)],
        knowledge_status="supported",
    )
