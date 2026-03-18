"""ProcureFlow -- Agent orchestration registry.

Maps :class:`~backend.utils.enums.RequestStatus` values to the
stage-appropriate watsonx-assisted tools. This gives ProcureFlow a clear
coordination boundary for intake, clarification, policy explanation,
catalog support, and approval-status handling without hard-coding the
mapping elsewhere.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from backend.utils.enums import RequestStatus

logger = logging.getLogger(__name__)

# Type alias for agent tool functions
AgentTool = Callable[..., Any]


class AgentRegistry:
    """Maps workflow stages to agent tool functions.

    Each registered tool is a callable that accepts ``request_id`` as its
    first positional argument (some accept additional kwargs). The
    registry is the coordination point a watsonx Orchestrate flow can use
    to determine which narrow AI support tool applies at each stage.
    """

    def __init__(self) -> None:
        self._registry: dict[RequestStatus, list[AgentTool]] = {}

    def register(self, stage: RequestStatus, tool: AgentTool) -> None:
        """Register an agent tool for a workflow stage."""
        self._registry.setdefault(stage, []).append(tool)

    def get_tools(self, stage: RequestStatus) -> list[AgentTool]:
        """Return the agent tools registered for *stage*."""
        return list(self._registry.get(stage, []))

    def list_stages(self) -> list[RequestStatus]:
        """Return all stages that have registered tools."""
        return list(self._registry.keys())

    def list_all(self) -> dict[str, list[str]]:
        """Return a serializable summary for debugging / docs."""
        return {
            stage.value: [t.__name__ for t in tools]
            for stage, tools in self._registry.items()
        }

    def run_stage(self, request_id: str) -> dict[str, Any]:
        """Execute all tools registered for the request's current status.

        Looks up the request, determines its status, and calls each
        registered agent tool in order. Results are collected into a
        dict keyed by the tool's function name.

        If a tool raises an exception it is caught and logged; the
        remaining tools still run.

        Parameters
        ----------
        request_id:
            The request to run agents against.

        Returns
        -------
        dict
            ``{"stage": str, "results": {tool_name: result, ...}}``

        Expected output schema::

            {
              "stage": "<current RequestStatus value>",
              "results": {
                "<agent_function_name>": <tool output (Pydantic model)>,
                ...
              }
            }
        """
        from backend.database import db

        req = db.get_request(request_id)
        if req is None:
            return {"stage": "unknown", "results": {}}

        stage = req.status
        tools = self.get_tools(stage)

        if not tools:
            logger.debug("run_stage: no agents registered for %s", stage.value)
            return {"stage": stage.value, "results": {}}

        results: dict[str, Any] = {}
        for tool in tools:
            # Disambiguate tools with the same __name__ (e.g. two "explain")
            module = getattr(tool, "__module__", "")
            module_short = module.rsplit(".", 1)[-1] if module else ""
            name = f"{module_short}.{tool.__name__}" if module_short else tool.__name__
            try:
                # catalog_agent.explain needs match_result, not request_id
                if name == "explain" and "catalog" in tool.__module__:
                    result = _run_catalog_explain(tool, request_id)
                else:
                    result = tool(request_id)
                results[name] = result
            except Exception:
                logger.warning(
                    "run_stage: agent %s failed for request %s",
                    name,
                    request_id,
                    exc_info=True,
                )
                results[name] = {"error": f"Agent {name} failed"}

        logger.info(
            "run_stage: ran %d agent(s) for request %s at stage %s",
            len(results),
            request_id,
            stage.value,
        )
        return {"stage": stage.value, "results": results}


def _run_catalog_explain(tool: AgentTool, request_id: str) -> Any:
    """Special-case runner for catalog_agent.explain which needs match_result."""
    from backend.database import db
    from backend.services.catalog import match_items

    req = db.get_request(request_id)
    if req is None:
        return tool({}, request_id=request_id)
    match_result = match_items(req.requested_items)
    return tool(match_result, request_id=request_id)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

registry = AgentRegistry()


def _register_defaults() -> None:
    """Wire up the default stage-to-agent mappings.

    Imports are local to avoid circular-import issues and to keep the
    registry importable without pulling in the full agent tree.
    """
    from backend.agents.approval_agent import draft_notification
    from backend.agents.catalog_agent import explain as catalog_explain
    from backend.agents.intake_agent import analyze as intake_analyze
    from backend.agents.policy_agent import explain as policy_explain

    registry.register(RequestStatus.draft, intake_analyze)
    registry.register(RequestStatus.clarification, intake_analyze)
    registry.register(RequestStatus.policy_review, policy_explain)
    registry.register(RequestStatus.policy_review, catalog_explain)
    registry.register(RequestStatus.pending_approval, draft_notification)
    registry.register(RequestStatus.approved, catalog_explain)

    logger.debug("Agent registry initialized: %s", registry.list_all())


_register_defaults()
