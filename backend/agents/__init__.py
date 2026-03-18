"""ProcureFlow -- watsonx agent tools package.

Provides the scoped watsonx-assisted workflow layer for ProcureFlow.
watsonx Orchestrate-style coordination decides which tool applies at
each workflow stage, while Granite or another configured model handles
language-heavy tasks such as clarification drafting and grounded
explanation text.

All tools are optional: when watsonx credentials are absent,
deterministic fallbacks produce structured responses from the existing
service outputs. No IBM SDK imports happen at this package level. The
adapter in ``llm_client.py`` lazy-imports only when credentials are
present.
"""

from backend.agents.orchestrate_registry import registry  # noqa: F401
