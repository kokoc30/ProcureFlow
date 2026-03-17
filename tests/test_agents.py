"""Tests for LLM client adapter selection and fallback behaviour."""

import os
from unittest.mock import patch, MagicMock

import pytest

from backend.agents.llm_client import (
    LLMRequest,
    StubClient,
    WatsonxClient,
    get_client,
    parse_json_response,
    _reset_client,
)


# ---------------------------------------------------------------------------
# Fixture: reset the singleton between tests
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clean_singleton():
    """Ensure each test starts with a fresh client singleton."""
    _reset_client()
    yield
    _reset_client()


# ---------------------------------------------------------------------------
# StubClient
# ---------------------------------------------------------------------------

class TestStubClient:
    def test_returns_ai_unavailable(self):
        client = StubClient()
        resp = client.generate(LLMRequest(system_prompt="x", user_message="y"))
        assert resp.ai_available is False
        assert resp.content == ""
        assert resp.model_id == "stub"

    def test_is_available_false(self):
        assert StubClient().is_available() is False

    def test_client_type(self):
        assert StubClient().client_type() == "stub"


# ---------------------------------------------------------------------------
# WatsonxClient
# ---------------------------------------------------------------------------

class TestWatsonxClient:
    def test_available_when_credentials_set(self, monkeypatch):
        monkeypatch.setenv("WATSONX_API_KEY", "test-key")
        monkeypatch.setenv("WATSONX_PROJECT_ID", "test-project")
        client = WatsonxClient()
        assert client.is_available() is True
        assert client.client_type() == "watsonx"

    def test_unavailable_when_key_missing(self, monkeypatch):
        monkeypatch.delenv("WATSONX_API_KEY", raising=False)
        monkeypatch.delenv("WATSONX_PROJECT_ID", raising=False)
        client = WatsonxClient()
        assert client.is_available() is False

    def test_generate_falls_back_on_import_error(self, monkeypatch):
        """When the SDK is not installed, generate() returns ai_available=False."""
        monkeypatch.setenv("WATSONX_API_KEY", "test-key")
        monkeypatch.setenv("WATSONX_PROJECT_ID", "test-project")
        client = WatsonxClient()

        # Force ImportError when trying to import the SDK
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if "ibm_watsonx_ai" in name:
                raise ImportError("No module named 'ibm_watsonx_ai'")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            resp = client.generate(LLMRequest(system_prompt="x", user_message="y"))

        assert resp.ai_available is False
        assert resp.content == ""

    def test_generate_falls_back_on_api_error(self, monkeypatch):
        """When the SDK call raises, generate() returns ai_available=False."""
        monkeypatch.setenv("WATSONX_API_KEY", "test-key")
        monkeypatch.setenv("WATSONX_PROJECT_ID", "test-project")
        client = WatsonxClient()

        mock_creds = MagicMock()
        mock_model_cls = MagicMock()
        mock_model_cls.return_value.generate.side_effect = RuntimeError("API error")

        with patch.dict("sys.modules", {
            "ibm_watsonx_ai": MagicMock(Credentials=mock_creds),
            "ibm_watsonx_ai.foundation_models": MagicMock(ModelInference=mock_model_cls),
        }):
            resp = client.generate(LLMRequest(system_prompt="x", user_message="y"))

        assert resp.ai_available is False
        assert resp.content == ""

    def test_default_model_id(self, monkeypatch):
        monkeypatch.setenv("WATSONX_API_KEY", "k")
        monkeypatch.setenv("WATSONX_PROJECT_ID", "p")
        monkeypatch.delenv("WATSONX_MODEL_ID", raising=False)
        client = WatsonxClient()
        assert client.model_id() == "ibm/granite-3-8b-instruct"


# ---------------------------------------------------------------------------
# get_client() factory
# ---------------------------------------------------------------------------

class TestGetClient:
    def test_returns_stub_when_no_credentials(self, monkeypatch):
        monkeypatch.delenv("WATSONX_API_KEY", raising=False)
        monkeypatch.delenv("WATSONX_PROJECT_ID", raising=False)
        client = get_client()
        assert client.client_type() == "stub"
        assert client.is_available() is False

    def test_returns_watsonx_when_credentials_set(self, monkeypatch):
        monkeypatch.setenv("WATSONX_API_KEY", "test-key")
        monkeypatch.setenv("WATSONX_PROJECT_ID", "test-project")
        client = get_client()
        assert client.client_type() == "watsonx"
        assert client.is_available() is True

    def test_singleton_caching(self, monkeypatch):
        monkeypatch.delenv("WATSONX_API_KEY", raising=False)
        monkeypatch.delenv("WATSONX_PROJECT_ID", raising=False)
        c1 = get_client()
        c2 = get_client()
        assert c1 is c2


# ---------------------------------------------------------------------------
# parse_json_response
# ---------------------------------------------------------------------------

class TestParseJsonResponse:
    def test_empty_string(self):
        assert parse_json_response("") is None

    def test_raw_json_object(self):
        assert parse_json_response('{"a": 1}') == {"a": 1}

    def test_raw_json_array(self):
        assert parse_json_response('[1, 2]') == [1, 2]

    def test_markdown_fenced(self):
        text = '```json\n{"key": "value"}\n```'
        assert parse_json_response(text) == {"key": "value"}

    def test_json_with_surrounding_text(self):
        text = 'Here is the result:\n{"x": 42}\nDone.'
        assert parse_json_response(text) == {"x": 42}

    def test_invalid_json(self):
        assert parse_json_response("not json at all") is None
