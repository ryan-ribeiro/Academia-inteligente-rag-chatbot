"""Provider-independent embedding contract and local Ollama adapter."""

from __future__ import annotations

import json
import math
import os
from typing import Protocol
from urllib.error import URLError
from urllib.request import Request, urlopen


class EmbeddingError(Exception):
    """Embedding service unavailable or returned malformed vectors."""


class Embedder(Protocol):
    model: str

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class OllamaEmbedder:
    def __init__(self, *, base_url: str | None = None, model: str | None = None) -> None:
        self.model = model or os.environ.get(
            "EXERCISE_EMBEDDING_MODEL", "embeddinggemma:300m-qat-q4_0"
        )
        self.base_url = (
            base_url
            or os.environ.get("EXERCISE_EMBEDDING_URL", "http://host.docker.internal:11434")
        ).rstrip("/")
        self.timeout = float(os.environ.get("EXERCISE_EMBEDDING_TIMEOUT", "60"))

    def fingerprint(self) -> str:
        try:
            with urlopen(self.base_url + "/api/tags", timeout=self.timeout) as response:  # noqa: S310
                models = json.load(response)["models"]
            for item in models:
                if item.get("name") == self.model and item.get("digest"):
                    return str(item["digest"])
            raise ValueError
        except (OSError, URLError, TimeoutError, ValueError, TypeError, KeyError):
            raise EmbeddingError from None

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        request = Request(
            self.base_url + "/api/embed",
            data=json.dumps({"model": self.model, "input": texts, "truncate": False}).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:  # noqa: S310
                payload = json.load(response)
            vectors = payload["embeddings"]
            if not isinstance(vectors, list) or len(vectors) != len(texts):
                raise ValueError
            result = []
            dimension = None
            for vector in vectors:
                if not isinstance(vector, list) or not vector:
                    raise ValueError
                values = [float(value) for value in vector]
                if not all(math.isfinite(value) for value in values):
                    raise ValueError
                norm = math.sqrt(sum(value * value for value in values))
                if not norm or (dimension is not None and dimension != len(values)):
                    raise ValueError
                dimension = len(values)
                result.append([value / norm for value in values])
            return result
        except (
            OSError,
            URLError,
            TimeoutError,
            ValueError,
            TypeError,
            KeyError,
            json.JSONDecodeError,
        ):
            raise EmbeddingError from None
