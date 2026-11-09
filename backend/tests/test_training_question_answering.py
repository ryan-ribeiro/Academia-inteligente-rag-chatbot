import json
import logging
from uuid import uuid4

import pytest
from sqlalchemy import select
from test_training_chat import FakeProvider, complete_onboarding, create_client, create_current_plan
from test_training_chat import session as session
from test_training_rag import CHUNK_ID, FakeKnowledge

from app.integrations.ai import AiTrainingChatResponse
from app.modules.knowledge.applicability import apply_procedural_applicability
from app.modules.knowledge.service import KnowledgeContext
from app.modules.training.chat_service import TrainingChatDraftUpdateError, TrainingChatService
from app.modules.training.models import TrainingPlanItem, TrainingPlanVersion

BENCH_CHUNK_ID = "muyor-bench-press-2023-technique"
BACK_SQUAT_CHUNK_ID = "papadakis-back-squat-older-adults-2024-procedure"
BODYWEIGHT_SQUAT_CHUNK_ID = "santarem-bodyweight-squat-2025-deep-procedure"
BENCH_CONTEXT = KnowledgeContext(
    (
        {
            "chunk_id": BENCH_CHUNK_ID,
            "source_id": "muyor-bench-press-2023",
            "content": "Desça a barra até próximo ao peito e estenda os cotovelos.",
        },
    ),
    "supported",
    "Limitações do estudo.",
)


@pytest.mark.parametrize(
    "message",
    [
        "Como fazer o agachamento?",
        "como fazer o agachamento",
        "Me explique o exercício agachamento",
        "Quero saber por que descanso 90 segundos",
        "Poderia me dizer como executar o movimento",
        "Gostaria de entender a respiração durante o exercício",
        "É seguro fazer agachamento",
    ],
)
def test_question_detection(message):
    assert TrainingChatService._is_question(message)


def test_statement_is_not_question():
    assert not TrainingChatService._is_question("Hoje fiz agachamento")


@pytest.mark.parametrize("exercise", ["supino", "levantamento terra"])
def test_question_retrieves_and_includes_own_onboarding(session, exercise, monkeypatch):
    monkeypatch.setattr("app.modules.training.chat_service.enforcement_enabled", lambda: True)
    client = create_client(session, "ada", "ada@example.test")
    create_current_plan(session, client)
    complete_onboarding(session, "ada")
    knowledge = FakeKnowledge(BENCH_CONTEXT)
    provider = FakeProvider(AiTrainingChatResponse(assistant_message="unused"))
    service = TrainingChatService(provider, knowledge_service=knowledge)
    request_id = uuid4()
    message = "Como fazer supino corretamente?"
    result = service.submit_for_subject(
        session, "ada", message=message, client_request_id=request_id
    )
    assert knowledge.calls == [(client.id, message)]
    assert provider.calls == 0
    assert "onboarding" in result.messages[-1].content
    assert "instrutor" in result.messages[-1].content
    assert result.messages[-1].citations[0]["chunk_id"] == BENCH_CHUNK_ID
    replay = service.submit_for_subject(
        session, "ada", message=message, client_request_id=request_id
    )
    assert replay.messages[-1].content == result.messages[-1].content
    assert len(knowledge.calls) == 1


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("unavailable", "Não consegui consultar as fontes"),
        ("outdated", "As fontes relacionadas precisam de revisão"),
        ("insufficient_evidence", "Não encontrei fundamentação suficiente"),
    ],
)
def test_question_without_evidence_never_calls_writer(session, status, expected):
    create_client(session, "ada", "ada@example.test")
    knowledge = FakeKnowledge(KnowledgeContext.empty(status))
    provider = FakeProvider(AiTrainingChatResponse(assistant_message="Resposta inventada"))
    result = TrainingChatService(provider, knowledge_service=knowledge).submit_for_subject(
        session, "ada", message="Como fazer agachamento?", client_request_id=uuid4()
    )
    assert len(knowledge.calls) == 1
    assert provider.calls == 0
    assert result.messages[-1].knowledge_status == status
    assert expected in result.messages[-1].content
    assert not result.messages[-1].citations


def test_question_context_does_not_include_another_clients_exercises_or_onboarding(session):
    owner = create_client(session, "ada", "ada@example.test")
    other = create_client(session, "grace", "grace@example.test")
    create_current_plan(session, other)
    complete_onboarding(session, "grace")
    provider = FakeProvider(AiTrainingChatResponse(assistant_message="unused"))
    knowledge = FakeKnowledge(BENCH_CONTEXT)
    result = TrainingChatService(provider, knowledge_service=knowledge).submit_for_subject(
        session, "ada", message="Como fazer supino?", client_request_id=uuid4()
    )
    assert knowledge.calls[0][0] == owner.id
    assert provider.calls == 0
    assert "Joelho sens?vel" not in result.messages[-1].content
    assert "Joelho sensível" not in result.messages[-1].content


def test_reviewed_procedure_works_for_an_assigned_exercise_without_changing_plan(session):
    client = create_client(session, "ada", "ada@example.test")
    create_current_plan(session, client)
    item = session.scalar(select(TrainingPlanItem))
    item.exercise_name = "Supino horizontal com barra"
    session.commit()
    before = item.exercise_name
    provider = FakeProvider(AiTrainingChatResponse(assistant_message="unused"))
    result = TrainingChatService(
        provider, knowledge_service=FakeKnowledge(BENCH_CONTEXT)
    ).submit_for_subject(
        session,
        "ada",
        message="Como fazer supino horizontal com barra?",
        client_request_id=uuid4(),
    )
    assert result.messages[-1].knowledge_status == "supported"
    assert result.messages[-1].citations[0]["chunk_id"] == BENCH_CHUNK_ID
    assert provider.calls == 0
    assert item.exercise_name == before


@pytest.mark.parametrize("status", ["current", "proposal", "superseded"])
def test_assigned_exercise_in_each_version_is_read_only(session, status):
    client = create_client(session, "ada", "ada@example.test")
    create_current_plan(session, client)
    version = session.scalar(select(TrainingPlanVersion))
    version.status = status
    session.commit()
    before = (version.status, version.revision, version.name, version.approved_by)
    provider = FakeProvider(AiTrainingChatResponse(assistant_message="Sem evidência."))
    knowledge = FakeKnowledge()
    result = TrainingChatService(provider, knowledge_service=knowledge).submit_for_subject(
        session, "ada", message="Como fazer agachamento?", client_request_id=uuid4()
    )
    assert provider.calls == 0
    assert result.messages[-1].knowledge_status == "insufficient_evidence"
    assert len(knowledge.calls) == 1
    assert (version.status, version.revision, version.name, version.approved_by) == before


@pytest.mark.parametrize("status", ["supported", "unavailable"])
def test_missing_exercise_name_queries_then_asks_for_clarification(session, status):
    create_client(session, "ada", "ada@example.test")
    knowledge = (
        FakeKnowledge() if status == "supported" else FakeKnowledge(KnowledgeContext.empty(status))
    )
    provider = FakeProvider(AiTrainingChatResponse(assistant_message="Resposta inventada"))
    result = TrainingChatService(provider, knowledge_service=knowledge).submit_for_subject(
        session, "ada", message="Como fazer o exercício?", client_request_id=uuid4()
    )
    assert len(knowledge.calls) == 1
    assert provider.calls == 0
    assert "Qual exercício" in result.messages[-1].content
    assert not result.messages[-1].citations


def test_question_rejects_citations_not_retrieved(session):
    create_client(session, "ada", "ada@example.test")
    provider = FakeProvider(
        AiTrainingChatResponse(
            assistant_message="Fa?a assim.", citations=["invented"], knowledge_status="supported"
        )
    )
    service = TrainingChatService(provider, knowledge_service=FakeKnowledge())
    with pytest.raises(TrainingChatDraftUpdateError):
        service.submit_for_subject(
            session, "ada", message="O que diz a fonte sobre descanso?", client_request_id=uuid4()
        )
    assert [message.role for message in service.state_for_subject(session, "ada").messages] == [
        "user"
    ]


def test_retrieval_precedes_the_writer(session):
    create_client(session, "ada", "ada@example.test")
    events = []

    class RecordingKnowledge(FakeKnowledge):
        def retrieve(self, session, client_id, query):
            events.append("retrieve")
            return super().retrieve(session, client_id, query)

    class RecordingProvider(FakeProvider):
        def training_chat(self, context):
            events.append("writer")
            return super().training_chat(context)

    provider = RecordingProvider(
        AiTrainingChatResponse(
            assistant_message="Resposta baseada na fonte.",
            citations=[CHUNK_ID],
            knowledge_status="supported",
        )
    )
    TrainingChatService(provider, knowledge_service=RecordingKnowledge()).submit_for_subject(
        session, "ada", message="O que diz a fonte sobre descanso?", client_request_id=uuid4()
    )
    assert events == ["retrieve", "writer"]


def test_question_reassesses_missing_citations_with_same_retrieval(session):
    create_client(session, "ada", "ada@example.test")

    class Writer(FakeProvider):
        def training_chat(self, context):
            self.calls += 1
            self.contexts.append(context)
            if self.calls == 1:
                return AiTrainingChatResponse(
                    assistant_message="Resposta", knowledge_status="supported"
                )
            return AiTrainingChatResponse(
                assistant_message="Resposta com fonte.",
                citations=[CHUNK_ID],
                knowledge_status="supported",
            )

    knowledge = FakeKnowledge()
    writer = Writer(AiTrainingChatResponse(assistant_message="unused"))
    result = TrainingChatService(writer, knowledge_service=knowledge).submit_for_subject(
        session, "ada", message="O que diz a fonte sobre descanso?", client_request_id=uuid4()
    )
    assert len(knowledge.calls) == 1 and writer.calls == 2
    assert "citation_reassessment" in writer.contexts[1]
    assert result.messages[-1].knowledge_status == "supported"
    assert result.messages[-1].citations[0]["chunk_id"] == CHUNK_ID


@pytest.mark.parametrize(
    ("question", "expected_status", "expected_ids"),
    [
        (
            "Uma pergunta, como fazer supino corretamente?",
            "supported",
            ["muyor-bench-press-2023-technique"],
        ),
        (
            "Qual a forma correta do supino?",
            "supported",
            ["muyor-bench-press-2023-technique"],
        ),
        ("Qual a forma correta do supino inclinado?", "insufficient_evidence", []),
        ("Como fazer supino inclinado?", "insufficient_evidence", []),
        ("Como fazer supino com halteres?", "insufficient_evidence", []),
        ("Como fazer agachamento?", "insufficient_evidence", []),
    ],
)
def test_procedural_support_requires_reviewed_exercise_and_variant(
    question, expected_status, expected_ids
):
    matching = {
        "chunk_id": "muyor-bench-press-2023-technique",
        "source_id": "muyor-bench-press-2023",
        "content": "Procedure for barbell horizontal bench press.",
    }
    unrelated = {"chunk_id": CHUNK_ID, "source_id": "anatomy", "content": "Anatomy."}
    raw = KnowledgeContext((matching, unrelated), "supported", "")

    result = apply_procedural_applicability(raw, question)

    assert result.knowledge_status == expected_status
    assert [chunk["chunk_id"] for chunk in result.chunks] == expected_ids


@pytest.mark.parametrize(
    ("question", "expected_status"),
    [
        ("Como fazer agachamento com barra?", "supported"),
        ("Como fazer back squat com barra?", "supported"),
        ("Como fazer agachamento?", "insufficient_evidence"),
        ("Como fazer agachamento goblet?", "insufficient_evidence"),
        ("Como fazer agachamento no Smith?", "insufficient_evidence"),
        ("Como fazer agachamento com peso corporal?", "insufficient_evidence"),
        ("Como fazer agachamento para posterior de coxa?", "insufficient_evidence"),
    ],
)
def test_back_squat_procedure_does_not_leak_to_other_variants(question, expected_status):
    from app.modules.knowledge.applicability import apply_procedural_applicability

    context = KnowledgeContext(
        (
            {
                "chunk_id": BACK_SQUAT_CHUNK_ID,
                "source_id": "papadakis-back-squat-older-adults-2024",
                "content": "Study procedure for barbell back squat in older adults.",
            },
        ),
        "supported",
        "",
    )

    result = apply_procedural_applicability(context, question)

    assert result.knowledge_status == expected_status
    assert [chunk["chunk_id"] for chunk in result.chunks] == (
        [BACK_SQUAT_CHUNK_ID] if expected_status == "supported" else []
    )


@pytest.mark.parametrize("assigned", [False, True])
def test_back_squat_question_uses_only_cited_published_procedure(session, assigned):
    client = create_client(session, "ada", "ada@example.test")
    if assigned:
        create_current_plan(session, client)
    knowledge = FakeKnowledge(
        KnowledgeContext(
            (
                {
                    "chunk_id": BACK_SQUAT_CHUNK_ID,
                    "source_id": "papadakis-back-squat-older-adults-2024",
                    "content": (
                        "Starting: barbell across upper back. Descent: flex hips, knees, "
                        "and ankles "
                        "until thighs parallel. Ascent: extend and keep hips and shoulders rising "
                        "together."
                    ),
                },
            ),
            "supported",
            "",
        )
    )
    writer = FakeProvider(AiTrainingChatResponse(assistant_message="unused"))

    result = TrainingChatService(writer, knowledge_service=knowledge).submit_for_subject(
        session,
        "ada",
        message="Como fazer agachamento com barra?",
        client_request_id=uuid4(),
    )

    message = result.messages[-1]
    assert writer.calls == 0
    assert len(knowledge.calls) == 1
    assert message.knowledge_status == "supported"
    assert message.citations[0]["chunk_id"] == BACK_SQUAT_CHUNK_ID
    assert "adultos mais velhos" in message.content
    assert "não cobre agachamento com peso corporal, goblet ou Smith" in message.content


def test_unqualified_squat_question_asks_for_variant_after_retrieval(session):
    create_client(session, "ada", "ada@example.test")
    knowledge = FakeKnowledge(
        KnowledgeContext(
            (
                {
                    "chunk_id": BACK_SQUAT_CHUNK_ID,
                    "source_id": "papadakis-back-squat-older-adults-2024",
                    "content": "Procedure passage for the barbell back squat.",
                },
            ),
            "supported",
            "",
        )
    )
    writer = FakeProvider(AiTrainingChatResponse(assistant_message="unused"))

    result = TrainingChatService(writer, knowledge_service=knowledge).submit_for_subject(
        session,
        "ada",
        message="Como fazer agachamento?",
        client_request_id=uuid4(),
    )

    message = result.messages[-1]
    assert len(knowledge.calls) == 1
    assert "Você se refere ao agachamento posterior com barra?" in message.content
    assert "adultos mais velhos" in message.content
    assert message.citations[0]["chunk_id"] == BACK_SQUAT_CHUNK_ID
    assert writer.calls == 0


@pytest.mark.parametrize(
    ("question", "status"),
    [
        ("Como fazer agachamento profundo com peso corporal?", "supported"),
        ("Como fazer agachamento profundo sem peso?", "supported"),
        ("Como fazer agachamento com peso corporal?", "insufficient_evidence"),
        ("Como fazer agachamento profundo com peso corporal e barra?", "insufficient_evidence"),
        ("Como fazer agachamento profundo unilateral sem peso?", "insufficient_evidence"),
        ("Como fazer agachamento com salto sem peso?", "insufficient_evidence"),
    ],
)
def test_bodyweight_squat_evidence_is_limited_to_deep_variant(question, status):
    context = KnowledgeContext(
        ({"chunk_id": BODYWEIGHT_SQUAT_CHUNK_ID, "content": "Deep bodyweight squat."},),
        "supported",
        "",
    )
    result = apply_procedural_applicability(context, question)
    assert result.knowledge_status == status


def test_bodyweight_squat_clarifies_depth_before_answering(session):
    create_client(session, "ada", "ada@example.test")
    knowledge = FakeKnowledge(
        KnowledgeContext(
            (
                {
                    "chunk_id": BODYWEIGHT_SQUAT_CHUNK_ID,
                    "source_id": "santarem-bodyweight-squat-2025",
                    "content": "Deep bodyweight squat protocol.",
                },
            ),
            "supported",
            "",
        )
    )
    writer = FakeProvider(AiTrainingChatResponse(assistant_message="unused"))
    result = TrainingChatService(writer, knowledge_service=knowledge).submit_for_subject(
        session,
        "ada",
        message="Como fazer agachamento com peso corporal?",
        client_request_id=uuid4(),
    )
    answer = result.messages[-1]
    assert "Você quer o agachamento profundo com peso corporal?" in answer.content
    assert answer.citations[0]["chunk_id"] == BODYWEIGHT_SQUAT_CHUNK_ID
    assert writer.calls == 0 and len(knowledge.calls) == 1


def test_bodyweight_squat_answer_identifies_protocol_and_limits(session):
    create_client(session, "ada", "ada@example.test")
    knowledge = FakeKnowledge(
        KnowledgeContext(
            (
                {
                    "chunk_id": BODYWEIGHT_SQUAT_CHUNK_ID,
                    "source_id": "santarem-bodyweight-squat-2025",
                    "content": "Deep bodyweight squat protocol.",
                },
            ),
            "supported",
            "",
        )
    )
    writer = FakeProvider(AiTrainingChatResponse(assistant_message="unused"))
    result = TrainingChatService(writer, knowledge_service=knowledge).submit_for_subject(
        session,
        "ada",
        message="Como fazer agachamento profundo com peso corporal?",
        client_request_id=uuid4(),
    )
    answer = result.messages[-1]
    assert answer.citations[0]["chunk_id"] == BODYWEIGHT_SQUAT_CHUNK_ID
    assert "15 adultos recreacionalmente ativos" in answer.content
    assert "não detalha todas as fases" in answer.content


def test_affirmative_after_variant_clarification_retrieves_and_replays(session, monkeypatch):
    monkeypatch.setattr("app.modules.training.chat_service.enforcement_enabled", lambda: True)
    create_client(session, "ada", "ada@example.test")
    knowledge = FakeKnowledge(
        KnowledgeContext(
            (
                {
                    "chunk_id": BODYWEIGHT_SQUAT_CHUNK_ID,
                    "source_id": "santarem-bodyweight-squat-2025",
                    "content": "Deep bodyweight squat protocol.",
                },
            ),
            "supported",
            "",
        )
    )
    writer = FakeProvider(AiTrainingChatResponse(assistant_message="unused"))
    service = TrainingChatService(writer, knowledge_service=knowledge)
    first = service.submit_for_subject(
        session,
        "ada",
        message="Como fazer agachamento com peso corporal?",
        client_request_id=uuid4(),
    )
    assert "Você quer o agachamento profundo" in first.messages[-1].content
    request_id = uuid4()
    result = service.submit_for_subject(session, "ada", message="Sim", client_request_id=request_id)
    replay = service.submit_for_subject(session, "ada", message="Sim", client_request_id=request_id)

    assert result.messages[-2].content == "Sim"
    assert result.messages[-1].citations[0]["chunk_id"] == BODYWEIGHT_SQUAT_CHUNK_ID
    assert knowledge.calls[-1][1] == "Como fazer agachamento profundo com peso corporal?"
    assert len(knowledge.calls) == 2 and writer.calls == 0
    assert replay.messages[-1].content == result.messages[-1].content


def test_clarification_reply_does_not_discard_extra_context_or_guess_between_options():
    from app.modules.knowledge.applicability import resolve_variant_reply

    single = "Você quer o agachamento profundo com peso corporal?"
    choice = "Você quer o agachamento posterior com barra ou o agachamento profundo?"
    assert resolve_variant_reply("Sim, sinto dor", single) is None
    assert resolve_variant_reply("Sim, por favor!", single) == (
        "Como fazer agachamento profundo com peso corporal?"
    )
    assert resolve_variant_reply("Sim", choice) is None
    assert resolve_variant_reply("peso corporal", choice) == (
        "Como fazer agachamento profundo com peso corporal?"
    )


@pytest.mark.parametrize(
    ("question", "chunk_id", "expected"),
    [
        (
            "Como fazer abdominal curto?",
            "oliva-lozano-muyor-core-2020-curlup",
            "joelhos flexionados",
        ),
        (
            "Como fazer elevação de quadril no solo?",
            "oliva-lozano-muyor-core-2020-bridge",
            "quadril é elevado",
        ),
        (
            "Como fazer flexão de braços?",
            "oliva-lozano-muyor-core-2020-pushup",
            "não especifica o posicionamento das mãos",
        ),
    ],
)
def test_core_procedure_answers_are_cited_and_limited(session, question, chunk_id, expected):
    create_client(session, "ada", "ada@example.test")
    complete_onboarding(session, "ada")
    knowledge = FakeKnowledge(
        KnowledgeContext(
            ({"chunk_id": chunk_id, "source_id": "core-review", "content": "Study protocol."},),
            "supported",
            "",
        )
    )
    writer = FakeProvider(AiTrainingChatResponse(assistant_message="unused"))

    result = TrainingChatService(writer, knowledge_service=knowledge).submit_for_subject(
        session, "ada", message=question, client_request_id=uuid4()
    )

    answer = result.messages[-1]
    assert len(knowledge.calls) == 1 and writer.calls == 0
    assert answer.citations[0]["chunk_id"] == chunk_id
    assert "adultos saudáveis" in answer.content and expected in answer.content
    assert "onboarding contém informações de saúde" in answer.content


@pytest.mark.parametrize(
    ("question", "chunk_id"),
    [
        ("Como fazer abdominal curto com rotação?", "oliva-lozano-muyor-core-2020-curlup"),
        ("Como fazer ponte unilateral?", "oliva-lozano-muyor-core-2020-bridge"),
        ("Como fazer ponte com uma perna?", "oliva-lozano-muyor-core-2020-bridge"),
        ("Como fazer ponte com elástico?", "oliva-lozano-muyor-core-2020-bridge"),
        ("Como fazer flexão de braços na parede?", "oliva-lozano-muyor-core-2020-pushup"),
        (
            "Como fazer flexão de braços com joelhos apoiados?",
            "oliva-lozano-muyor-core-2020-pushup",
        ),
    ],
)
def test_core_passages_do_not_support_other_variants(question, chunk_id):
    context = KnowledgeContext(
        ({"chunk_id": chunk_id, "source_id": "core-review", "content": "Study protocol."},),
        "supported",
        "",
    )
    result = apply_procedural_applicability(context, question)
    assert result.knowledge_status == "insufficient_evidence"
    assert not result.chunks


def test_multiple_exercises_do_not_silently_receive_only_one_procedure():
    context = KnowledgeContext(
        (
            {"chunk_id": "oliva-lozano-muyor-core-2020-pushup", "content": "Push-up."},
            {"chunk_id": "oliva-lozano-muyor-core-2020-curlup", "content": "Curl-up."},
        ),
        "supported",
        "",
    )
    result = apply_procedural_applicability(
        context, "Como fazer flexão de braços e abdominal curto?"
    )
    assert result.knowledge_status == "insufficient_evidence"
    assert not result.chunks


@pytest.mark.parametrize(
    ("question", "status"),
    [
        ("Como fazer rosca direta com halteres?", "supported"),
        ("Como fazer rosca de bíceps com halteres?", "supported"),
        ("Como fazer rosca direta com barra?", "insufficient_evidence"),
        ("Como fazer rosca alternada com halteres?", "insufficient_evidence"),
        ("Como fazer rosca martelo com halteres?", "insufficient_evidence"),
        ("Como fazer rosca com halteres?", "insufficient_evidence"),
    ],
)
def test_dumbbell_curl_support_is_specific_to_study_variant(question, status):
    context = KnowledgeContext(
        (
            {
                "chunk_id": "parpa-dumbbell-curl-2025-procedure",
                "source_id": "parpa-dumbbell-curl-2025",
                "content": "Standing bilateral dumbbell curl procedure.",
            },
        ),
        "supported",
        "",
    )
    result = apply_procedural_applicability(context, question)
    assert result.knowledge_status == status
    assert len(result.chunks) == (1 if status == "supported" else 0)


def test_dumbbell_curl_answer_identifies_study_population_and_source(session):
    create_client(session, "ada", "ada@example.test")
    knowledge = FakeKnowledge(
        KnowledgeContext(
            (
                {
                    "chunk_id": "parpa-dumbbell-curl-2025-procedure",
                    "source_id": "parpa-dumbbell-curl-2025",
                    "content": "Standing bilateral dumbbell curl procedure.",
                },
            ),
            "supported",
            "",
        )
    )
    writer = FakeProvider(AiTrainingChatResponse(assistant_message="unused"))
    result = TrainingChatService(writer, knowledge_service=knowledge).submit_for_subject(
        session,
        "ada",
        message="Como fazer rosca direta com halteres?",
        client_request_id=uuid4(),
    )
    answer = result.messages[-1]
    assert writer.calls == 0 and len(knowledge.calls) == 1
    assert answer.citations[0]["chunk_id"] == "parpa-dumbbell-curl-2025-procedure"
    assert "homens fisicamente ativos e treinados" in answer.content
    assert "não avalia sua situação individual" in answer.content


def test_chat_http_cites_core_source_and_keeps_other_client_isolated(session, monkeypatch):
    from test_mvp_end_to_end_verification import AsgiClient, MutableIdentityProvider

    from app.database import get_database_session
    from app.main import create_app
    from app.modules.identity import router as identity_router
    from app.modules.identity.service import AuthenticatedIdentity
    from app.modules.knowledge.acquisition import CATALOG_PATH
    from app.modules.training import router as training_router

    ada = create_client(session, "ada", "ada@example.test")
    create_client(session, "grace", "grace@example.test")
    complete_onboarding(session, "ada")
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    source = next(
        item
        for item in catalog["sources"]
        if item["id"] == "oliva-lozano-muyor-core-exercise-procedures-2020"
    )
    selected = next(chunk for chunk in source["chunks"] if chunk["id"].endswith("pushup"))
    passage = {
        **{key: source[key] for key in ("title", "url", "authors", "license", "license_url")},
        "chunk_id": selected["id"],
        "source_id": source["id"],
        "section": selected["section"],
        "attribution": source["attribution"],
        "content_note": source["content_note"],
        "content": selected["content"],
    }
    knowledge = FakeKnowledge(KnowledgeContext((passage,), "supported", ""))
    writer = FakeProvider(AiTrainingChatResponse(assistant_message="unused"))
    app = create_app()

    def override_database_session():
        yield session

    app.dependency_overrides[get_database_session] = override_database_session
    identity = MutableIdentityProvider(
        AuthenticatedIdentity("ada", "ada@example.test", ("client",))
    )
    monkeypatch.setattr(identity_router, "identity_provider", identity)
    monkeypatch.setattr(
        training_router, "chat_service", TrainingChatService(writer, knowledge_service=knowledge)
    )
    api = AsgiClient(app)
    request = {"message": "Como fazer flexão de braços?", "client_request_id": str(uuid4())}
    try:
        response = api.request("POST", "/training/chat/messages", request)
        replay = api.request("POST", "/training/chat/messages", request)
        identity.identity = AuthenticatedIdentity("grace", "grace@example.test", ("client",))
        other = api.request("GET", "/training/chat")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == replay.status_code == other.status_code == 200
    answer = response.body["messages"][-1]
    assert answer["citations"][0]["chunk_id"] == selected["id"]
    assert answer["citations"][0]["url"] == source["url"]
    assert "Descrições da tabela 2" in answer["citations"][0]["content_note"]
    assert "adultos saudáveis" in answer["content"]
    assert knowledge.calls == [(ada.id, request["message"])]
    assert other.body["messages"] == []


def test_question_with_only_unrelated_retrieval_does_not_reach_writer(session):
    create_client(session, "ada", "ada@example.test")

    class IrrelevantKnowledge(FakeKnowledge):
        def retrieve(self, session, client_id, query):
            self.calls.append((client_id, query))
            return KnowledgeContext(
                ({"chunk_id": CHUNK_ID, "source_id": "anatomy", "content": "Anatomy."},),
                "supported",
                "",
            )

    writer = FakeProvider(AiTrainingChatResponse(assistant_message="Resposta sem fonte"))
    result = TrainingChatService(
        writer, knowledge_service=IrrelevantKnowledge()
    ).submit_for_subject(
        session,
        "ada",
        message="Como fazer agachamento?",
        client_request_id=uuid4(),
    )
    assert writer.calls == 0
    assert result.messages[-1].knowledge_status == "insufficient_evidence"
    assert not result.messages[-1].citations


def test_question_does_not_invent_citation_after_reassessment(session):
    create_client(session, "ada", "ada@example.test")
    writer = FakeProvider(
        AiTrainingChatResponse(assistant_message="Resposta sem fonte", knowledge_status="supported")
    )
    result = TrainingChatService(writer, knowledge_service=FakeKnowledge()).submit_for_subject(
        session, "ada", message="O que diz a fonte sobre descanso?", client_request_id=uuid4()
    )
    assert writer.calls == 2
    assert result.messages[-1].knowledge_status == "insufficient_evidence"
    assert not result.messages[-1].citations


def test_question_suppresses_writer_prompt_echo(session):
    create_client(session, "ada", "ada@example.test")
    writer = FakeProvider(
        AiTrainingChatResponse(
            assistant_message=(
                "Responda diretamente ao cliente usando somente os trechos em knowledge.chunks."
            )
        )
    )
    result = TrainingChatService(writer, knowledge_service=FakeKnowledge()).submit_for_subject(
        session, "ada", message="O que diz a fonte sobre descanso?", client_request_id=uuid4()
    )
    assert "Responda diretamente" not in result.messages[-1].content
    assert result.messages[-1].knowledge_status == "insufficient_evidence"
    assert not result.messages[-1].citations


def test_question_diagnostics_are_bounded_and_do_not_log_sensitive_context(session, caplog):
    caplog.set_level(logging.INFO, logger="uvicorn.error.ai")
    create_client(session, "ada", "ada@example.test")
    provider = FakeProvider(AiTrainingChatResponse(assistant_message="unused"))
    TrainingChatService(
        provider, knowledge_service=FakeKnowledge(BENCH_CONTEXT)
    ).submit_for_subject(
        session, "ada", message="Como fazer supino? informa??o privada", client_request_id=uuid4()
    )
    turns = [
        json.loads(record.message)
        for record in caplog.records
        if '"event":"ai_turn"' in record.message
    ]
    assert turns[-1]["question"] is True
    assert turns[-1]["passage_count"] == 1
    assert turns[-1]["path"] == "reviewed_procedure"
    assert turns[-1]["citation_state"] == "provided"
    assert turns[-1]["knowledge_status"] == "supported"
    assert "informa??o privada" not in caplog.text
    assert "ada@example.test" not in caplog.text
