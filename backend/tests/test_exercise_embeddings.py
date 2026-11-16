import io
import json
from urllib.error import URLError

import pytest

from app.integrations.ai import AiTrainingChatResponse, OllamaOnboardingProvider
from app.integrations.embeddings import EmbeddingError, OllamaEmbedder


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def test_embedding_adapter_normalizes_and_batches(monkeypatch):
    def fake_open(request, timeout):
        payload = json.loads(request.data)
        assert payload["input"] == ["um", "dois"]
        assert payload["truncate"] is False
        return Response(json.dumps({"embeddings": [[3, 4], [0, 2]]}).encode())

    monkeypatch.setattr("app.integrations.embeddings.urlopen", fake_open)
    vectors = OllamaEmbedder(base_url="http://example.test").embed(["um", "dois"])
    assert vectors == [[0.6, 0.8], [0.0, 1.0]]


@pytest.mark.parametrize("payload", [{"embeddings": [[0, 0]]}, {"embeddings": []}, {}])
def test_embedding_adapter_rejects_invalid_vectors(monkeypatch, payload):
    monkeypatch.setattr(
        "app.integrations.embeddings.urlopen",
        lambda request, timeout: Response(json.dumps(payload).encode()),
    )
    with pytest.raises(EmbeddingError):
        OllamaEmbedder(base_url="http://example.test").embed(["um"])


def test_embedding_adapter_returns_controlled_failure(monkeypatch):
    def unavailable(request, timeout):
        raise URLError("unavailable")

    monkeypatch.setattr("app.integrations.embeddings.urlopen", unavailable)
    with pytest.raises(EmbeddingError):
        OllamaEmbedder(base_url="http://example.test").embed(["um"])


def test_embedding_model_fingerprint(monkeypatch):
    payload = {"models": [{"name": "model:test", "digest": "sha256-test"}]}
    monkeypatch.setattr(
        "app.integrations.embeddings.urlopen",
        lambda request, timeout: Response(json.dumps(payload).encode()),
    )
    assert OllamaEmbedder(base_url="http://example.test", model="model:test").fingerprint() == (
        "sha256-test"
    )


def test_chat_schema_forbids_draft_when_not_authorized(monkeypatch):
    provider = OllamaOnboardingProvider()
    schemas = []

    def fake_call(context, instructions, schema, type_):
        schemas.append(schema)
        return AiTrainingChatResponse(assistant_message="Certo.")

    monkeypatch.setattr(provider, "_call", fake_call)
    provider.training_chat({"rules": {"may_update_ai_draft": False}})
    assert schemas[0]["properties"]["draft_update"] == {"type": "null"}
