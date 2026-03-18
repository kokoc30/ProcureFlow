# ProcureFlow - Architecture Decisions

Locked-in decisions for the hackathon build. Follow these to keep the codebase consistent.

---

## Serving Model

Multi-page application. FastAPI serves:

- **HTML pages** from `frontend/pages/` (each page is a standalone `.html` file)
- **Static assets** (CSS, JS, images) from `frontend/` mounted at `/static`

There is no SPA, no client-side router, no React, no Vite. Each page loads its own CSS/JS via `/static/...` paths.

The root route (`GET /`) returns `frontend/pages/index.html` directly.

---

## API Prefix

All backend endpoints live under:

```
/api/v1
```

No exceptions. The prefix is defined once in `backend/utils/settings.py` as `API_PREFIX`.

---

## Route Registration

Each route module in `backend/routes/` exports:

```python
from fastapi import APIRouter
router = APIRouter(prefix="/things", tags=["things"])
```

All routers are registered in `backend/routes/__init__.py` via `include_routers(app)`, which adds the `/api/v1` prefix. The resulting path is `/api/v1/things`.

To add a new route module:
1. Create `backend/routes/<name>.py` with a `router`
2. Import it in `backend/routes/__init__.py`
3. Add `app.include_router(<name>_router, prefix=API_PREFIX)`

No changes to `backend/main.py` are needed.

---

## Naming Conventions

| Layer | Convention | Example |
|-------|-----------|---------|
| Python models, fields, functions | `snake_case` | `estimated_cost`, `approval_status` |
| Python files and modules | `snake_case` | `policy_engine.py`, `approval_workflow.py` |
| Frontend JS variables and functions | `camelCase` | `estimatedCost`, `fetchRequests()` |
| API JSON keys | `snake_case` | `{"request_id": "..."}` |

Case conversion between `snake_case` (API) and `camelCase` (JS) happens at the frontend boundary only, if needed. The backend never uses camelCase.

---

## Business Logic Placement

| What | Where | Why |
|------|-------|-----|
| Policy rules, approval thresholds, routing, totals, validation, and status transitions | `backend/services/` (deterministic Python) | Reliability and auditability - these controls must stay predictable |
| Workflow coordination across intake, clarification, policy summary support, catalog support, and approval status handling | `backend/agents/orchestrate_registry.py` and `/api/v1/agents/*` | Keeps stage-specific AI support aligned to the right workflow stage |
| Interpreting messy request language, drafting clarification questions, and producing grounded explanation text | IBM watsonx / Granite via `backend/agents/llm_client.py` | AI adds value on language-heavy tasks without owning business decisions |

IBM watsonx Orchestrate wraps and augments the deterministic services. It never replaces them. If watsonx is unavailable, the core workflow still functions with deterministic fallbacks. AI never makes approval decisions and never overrides procurement judgment.

---

## Key Paths

```
backend/
  main.py              - app entry point, CORS, static mount
  database.py          - in-memory store, seed loading, CRUD helpers
  models.py            - Pydantic data models
  utils/settings.py    - all constants (paths, prefix, origins)
  routes/__init__.py   - include_routers() registration
  routes/<name>.py     - individual API routers
  services/<name>.py   - business logic

frontend/
  pages/<name>.html    - standalone HTML pages
  css/<name>.css       - stylesheets
  js/<name>.js         - scripts
  assets/              - images, SVGs

shared/
  data/                - mock JSON data (catalog, users, departments, policies, personas)
  contracts/           - API schema contracts
```

---

## Testing

ProcureFlow includes a pytest suite covering all backend services and API routes.

### Running Tests

```bash
python -m pytest tests/ -v
```

### Test Modules

| File | Coverage |
|------|----------|
| `tests/test_requests.py` | Request CRUD, validation, status transitions |
| `tests/test_clarifications.py` | Clarification creation, answering, back-fill |
| `tests/test_catalog.py` | Catalog matching, item resolution |
| `tests/test_policy.py` | Policy evaluation, threshold rules, auto-approve |
| `tests/test_approvals.py` | Approval task creation, decision recording, cascade |
| `tests/test_po.py` | PO generation, totals, blocking conditions |
| `tests/test_integration.py` | Full happy-path and auto-approve end-to-end flows |
| `tests/test_agents.py` | LLM client adapter selection, fallback behavior, JSON parsing |
| `tests/conftest.py` | Shared fixtures (test client, database reset) |

### Design Principles

- Tests use FastAPI `TestClient` with `httpx` for synchronous HTTP calls
- The in-memory database is reset between tests via the `reset_db` autouse fixture
- No external services or mocks required - all tests run offline
- Integration tests exercise the complete workflow from request creation through PO generation

See also: `docs/test_plan.md` for the full test plan including manual browser checks.
