# watsonx Agent Integration Notes

## Positioning Summary

ProcureFlow uses IBM watsonx in a scoped, governance-friendly way:

- **watsonx Orchestrate** coordinates stage-specific workflow support across intake, clarification, policy summary support, catalog support, approval status handling, and fulfillment-readiness support around the PO draft.
- **Granite or another configured watsonx model** is used for narrow language tasks such as interpreting messy request wording, drafting clarification questions, and producing grounded explanation text.
- **Deterministic Python services** remain responsible for policy thresholds, routing rules, totals, validation, status transitions, approval outcomes, PO generation, and audit events.

AI never makes uncontrolled approval decisions and never replaces procurement judgment.

---

## Architecture Overview

The agent layer wraps ProcureFlow's deterministic services to produce workflow-safe language assistance. It **never** replaces or overrides the deterministic business logic.

```
Routes (existing) -> Services (deterministic) -> Database
                              ^
Routes (/agents/) -> Orchestrate registry -> Agent tools -> LLM client -> watsonx / StubClient
                                               |
                                               -> grounded explanations from deterministic outputs
```

All agent code lives in `backend/agents/`. The IBM SDK is imported lazily inside `WatsonxClient.generate()` only - the rest of the backend runs without `ibm-watsonx-ai` installed.

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `WATSONX_API_KEY` | No | - | IAM API key for watsonx.ai |
| `WATSONX_PROJECT_ID` | No | - | watsonx.ai project ID |
| `WATSONX_URL` | No | `https://us-south.ml.cloud.ibm.com` | Regional endpoint |
| `WATSONX_MODEL_ID` | No | `ibm/granite-3-8b-instruct` | Foundation model ID |

When `WATSONX_API_KEY` and `WATSONX_PROJECT_ID` are both set, the `WatsonxClient` is used. Otherwise the `StubClient` provides deterministic fallback behavior.

---

## Client Abstraction

`backend/agents/llm_client.py` provides:

- **`LLMClient`** - abstract base with `.generate()` and `.is_available()`
- **`WatsonxClient`** - real IBM SDK integration with lazy imports
- **`StubClient`** - returns `ai_available=False` with empty content
- **`get_client()`** - factory that auto-detects credentials

The client is cached as a singleton after the first call.

---

## What watsonx Orchestrate Coordinates

`backend/agents/orchestrate_registry.py` maps `RequestStatus` values to the stage-appropriate tools:

| Status | Coordinated support |
|--------|---------------------|
| `draft` | Intake analysis and clarification drafting |
| `clarification` | Clarification follow-up support |
| `policy_review` | Policy explanation and catalog explanation |
| `pending_approval` | Approval-status notification support |
| `approved` | Catalog / fulfillment-readiness explanation support |

Use `registry.get_tools(status)` to look up which tools apply. Use `registry.run_stage(request_id)` to execute all applicable tools for the current workflow stage in one call.

---

## Agents

### Intake Agent (`intake_agent.py`)
- **Function:** `analyze(request_id) -> IntakeAnalysis`
- **Deterministic part:** Identifies missing fields (`justification`, `cost_center`, `delivery_date`)
- **Language-model part:** Drafts clarification questions and a short intake summary
- **Fallback:** Template questions per missing field

### Policy Agent (`policy_agent.py`)
- **Function:** `explain(request_id) -> PolicyExplanation`
- **Deterministic part:** Reads `PolicyResult` from the policy engine
- **Language-model part:** Translates policy flags into grounded business language
- **Fallback:** Concatenates deterministic flag messages

### Catalog Agent (`catalog_agent.py`)
- **Function:** `explain(match_result, request_id) -> CatalogExplanation`
- **Deterministic part:** Reads match results from the catalog service
- **Language-model part:** Explains matches and unresolved items in grounded language
- **Fallback:** Deterministic matched / unresolved summaries

### Approval Agent (`approval_agent.py`)
- **Function:** `draft_notification(request_id, approver_role) -> ApprovalNotification`
- **Deterministic part:** Reads request, policy result, and user data
- **Language-model part:** Drafts concise approval-status context for the approver
- **Fallback:** Deterministic notification template

---

## What AI May Do

- Interpret messy request wording to improve clarification quality
- Ask follow-up questions for missing fields
- Produce human-readable summaries of deterministic outputs
- Explain matching, policy, and approval status in plain language
- Package next-step guidance for the requester or approver

## What AI Must Not Do

- Decide thresholds, roles, approval outcomes, totals, or pricing
- Override or reinterpret deterministic service outputs
- Fabricate policy rules, catalog items, or supplier facts
- Infer missing facts when the workflow should ask explicitly
- Mutate database state on its own
- Recommend approval or rejection decisions

---

## API Endpoints

All agent endpoints live under `/api/v1/agents/`.

| Method | Path | Mutates? | Description |
|--------|------|----------|-------------|
| GET | `/agents/status` | No | watsonx availability and registered stage map |
| POST | `/agents/intake-analysis/{request_id}` | No | Analyze missing fields and suggest clarification questions |
| POST | `/agents/run-intake/{request_id}` | Yes | Analyze plus auto-create clarification records |
| POST | `/agents/policy-explanation/{request_id}` | No | Explain policy evaluation in business language |
| POST | `/agents/catalog-explanation` | No | Explain catalog match results |
| POST | `/agents/approval-notification/{request_id}` | No | Draft approval-status context |
| POST | `/agents/run-stage/{request_id}` | No | Run all stage-appropriate tools for the current workflow status |

---

## AI vs Deterministic Boundary

| Task | Owner | AI-assisted? |
|------|-------|-------------|
| Catalog matching (token overlap + aliases) | `backend/services/catalog.py` | No |
| Missing-field detection | `backend/agents/intake_agent.py` | No - deterministic |
| Clarification question text | `backend/agents/intake_agent.py` | Yes - drafts language |
| Field back-fill on answer | `backend/services/clarification_service.py` | No |
| Policy threshold evaluation | `backend/services/policy_engine.py` | No |
| Required approver determination | `backend/services/policy_engine.py` | No |
| Policy result explanation text | `backend/agents/policy_agent.py` | Yes - summarizes |
| Catalog match explanation text | `backend/agents/catalog_agent.py` | Yes - explains |
| Approval cascade logic | `backend/services/approval_service.py` | No |
| Approval notification text | `backend/agents/approval_agent.py` | Yes - drafts |
| PO generation | `backend/services/po_generator.py` | No |
| Audit event recording | `backend/audit.py` | No |

---

## Intake Service Boundary

`backend/services/intake_service.py` bridges the intake agent with the clarification service:

1. Calls `intake_agent.analyze()` to detect missing fields and draft questions
2. Transitions the request from `draft` to `clarification` if missing fields are found
3. Creates one `Clarification` record per suggested question
4. Returns `{"analysis": IntakeAnalysis, "clarifications_created": [str, ...]}`

**All state mutations are deterministic.** The agent only contributes question text and a summary. The service decides whether clarifications are needed and when statuses change.

---

## Testing Without Credentials

1. Start the server normally - `StubClient` activates automatically
2. All `/api/v1/agents/` endpoints return valid responses with `ai_available: false`
3. `GET /api/v1/agents/status` reports `client_type: "stub"`
4. No import errors and no SDK dependency required

---

## Demo Guidance

When describing ProcureFlow live:

- Say that watsonx Orchestrate coordinates the workflow handoffs between the AI-assisted stages
- Say that Granite helps with request-language interpretation, clarification drafting, and grounded summaries
- Say that Python services still own policy thresholds, routing, totals, validation, status changes, and approvals
- Do not say that AI approves requests or replaces procurement judgment

---

## Adding a New Agent

1. Create `backend/agents/<name>_agent.py`
2. Define the output model in `backend/agents/agent_models.py`
3. Implement the tool function with an LLM call plus deterministic fallback
4. Register it in `backend/agents/orchestrate_registry.py`
5. Add the route in `backend/routes/agents.py`
6. Document the guardrails and the deterministic boundary in this file
