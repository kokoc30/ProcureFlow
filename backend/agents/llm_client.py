"""ProcureFlow -- LLM client abstraction with watsonx adapter.

Provides a clean boundary between ProcureFlow's deterministic workflow
services and IBM watsonx language assistance. Granite or another
configured watsonx model is used only for language-heavy tasks such as
interpreting messy request text, drafting clarification questions, and
producing grounded explanation text.

The ``ibm_watsonx_ai`` package is **never** imported at module level so the
entire backend can start without the SDK installed.

Environment variables (all optional -- StubClient is used when absent):
    WATSONX_API_KEY       IAM API key for watsonx.ai
    WATSONX_PROJECT_ID    watsonx.ai project ID
    WATSONX_URL           Regional endpoint (default: us-south)
    WATSONX_MODEL_ID      Foundation model (default: ibm/granite-3-8b-instruct)
"""

from __future__ import annotations

import abc
import json
import logging
import os
import re

from pydantic import BaseModel

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Request / Response value objects
# ---------------------------------------------------------------------------

class LLMRequest(BaseModel):
    """Structured input to the LLM."""

    system_prompt: str
    user_message: str
    max_tokens: int = 1024
    temperature: float = 0.2


class LLMResponse(BaseModel):
    """Structured output from the LLM."""

    content: str
    model_id: str
    usage_tokens: int | None = None
    ai_available: bool = True


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class LLMClient(abc.ABC):
    """Abstract base for LLM backends."""

    @abc.abstractmethod
    def generate(self, request: LLMRequest) -> LLMResponse:
        ...

    @abc.abstractmethod
    def is_available(self) -> bool:
        ...

    @abc.abstractmethod
    def client_type(self) -> str:
        ...

    @abc.abstractmethod
    def model_id(self) -> str:
        ...


# ---------------------------------------------------------------------------
# Stub implementation (zero external deps)
# ---------------------------------------------------------------------------

class StubClient(LLMClient):
    """Returns empty content with ``ai_available=False``.

    This is the default when watsonx credentials are not configured.
    Every agent is expected to handle the empty-content case by falling
    back to deterministic template-based output.
    """

    def generate(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(
            content="",
            model_id="stub",
            ai_available=False,
        )

    def is_available(self) -> bool:
        return False

    def client_type(self) -> str:
        return "stub"

    def model_id(self) -> str:
        return "stub"


# ---------------------------------------------------------------------------
# IBM watsonx implementation
# ---------------------------------------------------------------------------

class WatsonxClient(LLMClient):
    """Real IBM watsonx.ai client.

    The ``ibm_watsonx_ai`` SDK is imported **lazily** inside
    :meth:`generate` so the rest of the backend never depends on it.
    """

    def __init__(self) -> None:
        self._api_key: str = os.environ.get("WATSONX_API_KEY", "")
        self._project_id: str = os.environ.get("WATSONX_PROJECT_ID", "")
        self._url: str = os.environ.get(
            "WATSONX_URL", "https://us-south.ml.cloud.ibm.com"
        )
        self._model: str = os.environ.get(
            "WATSONX_MODEL_ID", "ibm/granite-3-8b-instruct"
        )

    def is_available(self) -> bool:
        return bool(self._api_key and self._project_id)

    def client_type(self) -> str:
        return "watsonx"

    def model_id(self) -> str:
        return self._model

    def generate(self, request: LLMRequest) -> LLMResponse:
        try:
            from ibm_watsonx_ai import Credentials
            from ibm_watsonx_ai.foundation_models import ModelInference

            credentials = Credentials(url=self._url, api_key=self._api_key)

            model = ModelInference(
                model_id=self._model,
                credentials=credentials,
                project_id=self._project_id,
                params={
                    "max_new_tokens": request.max_tokens,
                    "temperature": request.temperature,
                    "stop_sequences": ["\n\n\n"],
                },
            )

            prompt = (
                f"<|system|>\n{request.system_prompt}\n"
                f"<|user|>\n{request.user_message}\n"
                f"<|assistant|>\n"
            )

            raw = model.generate(prompt=prompt)
            # raw: {"results": [{"generated_text": "...", "generated_token_count": N, ...}]}
            first = (raw.get("results") or [{}])[0]
            generated_text = first.get("generated_text", "")
            token_count = first.get("generated_token_count")

            return LLMResponse(
                content=generated_text.strip() if generated_text else "",
                model_id=self._model,
                usage_tokens=token_count,
                ai_available=True,
            )
        except Exception as exc:
            logger.warning(
                "watsonx call failed, falling back to stub: %s",
                type(exc).__name__,
            )
            logger.debug("watsonx error detail: %s", exc)
            return LLMResponse(
                content="",
                model_id=self._model,
                ai_available=False,
            )


# ---------------------------------------------------------------------------
# JSON parsing helper
# ---------------------------------------------------------------------------

def parse_json_response(text: str) -> dict | list | None:
    """Best-effort extraction of JSON from an LLM response.

    Handles common cases: raw JSON, markdown-fenced JSON, and responses
    with extra text before/after the JSON block.
    """
    if not text:
        return None

    # Try raw parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try stripping markdown fences
    fenced = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if fenced:
        try:
            return json.loads(fenced.group(1))
        except json.JSONDecodeError:
            pass

    # Try finding first { or [ to end of corresponding bracket
    for start_char, end_char in [("{", "}"), ("[", "]")]:
        idx = text.find(start_char)
        if idx >= 0:
            # Find matching end bracket from the end of string
            end_idx = text.rfind(end_char)
            if end_idx > idx:
                try:
                    return json.loads(text[idx : end_idx + 1])
                except json.JSONDecodeError:
                    pass

    return None


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

_cached_client: LLMClient | None = None


def get_client() -> LLMClient:
    """Return the singleton LLM client.

    Returns :class:`WatsonxClient` when credentials are configured,
    otherwise :class:`StubClient`.
    """
    global _cached_client
    if _cached_client is not None:
        return _cached_client

    candidate = WatsonxClient()
    if candidate.is_available():
        logger.info("watsonx credentials found -- using WatsonxClient (%s)", candidate.model_id())
        _cached_client = candidate
    else:
        logger.info("No watsonx credentials -- using StubClient (deterministic-only mode)")
        _cached_client = StubClient()

    return _cached_client


def _reset_client() -> None:
    """Reset the cached client singleton. For testing only."""
    global _cached_client
    _cached_client = None
