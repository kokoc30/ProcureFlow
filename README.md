# ProcureFlow

A multi-stage procurement workflow application combining deterministic business logic with optional IBM watsonx AI assistance for intake analysis and natural-language explanations.

---

## Overview

ProcureFlow manages purchase requests through a structured approval pipeline:

- Employees submit purchase requests with line items and justification
- The system detects missing information and generates clarification questions
- Policy rules (category-based thresholds and approver requirements) are evaluated deterministically
- Approval tasks are routed to the correct approvers based on policy results
- Purchase orders are generated from catalog-matched items
- Every action is recorded in an immutable audit timeline

**Deterministic-first design:** All policy evaluation, approval routing, status transitions, and validation are pure Python — no AI involved in decisions. IBM watsonx (optional) assists only with language tasks: drafting clarification questions, explaining policy results, and summarizing catalog matches. If watsonx credentials are absent, the application runs fully with deterministic fallbacks.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend framework | FastAPI 0.115+ |
| ASGI server | Uvicorn |
| Data validation | Pydantic |
| Testing | pytest + httpx |
| AI / LLM (optional) | IBM watsonx.ai — Granite model |
| Environment config | python-dotenv |
| Frontend | Vanilla HTML5 + CSS + JavaScript (ES6+) |
| Database | In-memory (no persistence; resets on restart) |

---

## Project Structure

```
IBM/
├── backend/
│   ├── main.py                  # FastAPI app entry point, static file serving, CORS
│   ├── models.py                # Pydantic models (Request, Item, ApprovalTask, PO, …)
│   ├── database.py              # In-memory store with CRUD helpers and seed-data loader
│   ├── audit.py                 # Audit event recorder
│   ├── agents/
│   │   ├── llm_client.py        # WatsonxClient / StubClient (graceful fallback)
│   │   ├── intake_agent.py      # Analyzes requests for missing fields
│   │   ├── policy_agent.py      # Explains policy evaluation results
│   │   ├── catalog_agent.py     # Explains catalog matching confidence
│   │   ├── approval_agent.py    # Drafts approval notification context
│   │   └── orchestrate_registry.py  # Stage → agent mapping
│   ├── routes/
│   │   ├── requests.py          # /requests CRUD
│   │   ├── clarifications.py    # /clarifications CRUD + answer
│   │   ├── catalog.py           # /catalog/match
│   │   ├── policy.py            # /policy/{id}/evaluate
│   │   ├── approvals.py         # /approvals start + decide
│   │   ├── po.py                # /po generate + get
│   │   ├── audit.py             # /audit timeline
│   │   ├── agents.py            # /agents AI endpoints
│   │   └── reference.py         # /users, /departments, /health
│   ├── services/
│   │   ├── intake_service.py    # Missing-field detection, clarification creation
│   │   ├── catalog.py           # 3-layer deterministic catalog matching
│   │   ├── policy_engine.py     # Category-based policy rule evaluation
│   │   ├── approval_service.py  # ApprovalTask creation and decision cascading
│   │   ├── po_generator.py      # PO draft generation from matched items
│   │   ├── clarification_service.py  # Clarification lifecycle management
│   │   └── summary_service.py   # Human-readable request summaries
│   └── utils/
│       ├── enums.py             # RequestStatus, ApproverRole, Urgency, AuditAction, …
│       └── settings.py          # API prefix, app title, CORS origins, path constants
├── frontend/
│   ├── pages/                   # Standalone HTML pages
│   ├── css/                     # Per-page and global stylesheets
│   ├── js/                      # Vanilla JS modules (api.js, ui.js, caseUtils.js, …)
│   └── assets/                  # Static images
├── shared/
│   ├── data/                    # Seed data JSON (users, catalog, policies, departments, personas, demo_state)
│   └── contracts/               # API schema contracts
├── tests/                       # pytest test suite (8 modules)
├── docs/                        # Architecture notes, demo flow, agent positioning
├── requirements.txt
├── .env.example
└── LICENSE
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- pip

### Install

```bash
cd IBM
pip install -r requirements.txt
```

### Run the development server

```bash
uvicorn backend.main:app --reload
```

The server starts at **http://localhost:8000**.

Open a browser and navigate to **http://localhost:8000** to access the landing page.

### Production

```bash
uvicorn backend.main:app
```

---

## Configuration

Copy `.env.example` to `.env` and fill in your watsonx credentials if you want AI-assisted features:

```env
WATSONX_API_KEY=your_api_key
WATSONX_PROJECT_ID=your_project_id
WATSONX_URL=https://us-south.ml.cloud.ibm.com
WATSONX_MODEL_ID=ibm/granite-3-8b-instruct
```

**All four variables are optional.** If any are missing, the application automatically uses the `StubClient` (deterministic fallback). No configuration is required to run the application.

---

## Running Tests

```bash
python -m pytest tests/ -v
```

The test suite covers:
- Request CRUD and status transitions
- Clarification creation and answering
- Catalog matching (alias map, token overlap, quantity parsing)
- Policy evaluation and auto-approve thresholds
- Approval task creation, decision recording, and cascading
- PO generation
- Full integration / happy-path flows
- LLM client selection and fallback behavior

All tests run fully offline against an in-memory store (no external services required).

---

## Workflow: How It Works

Purchase requests move through the following status lifecycle:

```
draft → clarification → policy_review → pending_approval → approved
                                                         ↘ rejected
```

| Step | What happens |
|---|---|
| **1. Create Request** | Employee submits items, justification, cost center, delivery date. Missing fields trigger `clarification` status. |
| **2. Answer Clarifications** | Assigned user answers clarification questions. When all are answered the request transitions to `policy_review`. |
| **3. Match Catalog** | Raw line-item descriptions are matched to catalog entries via alias map → token overlap → quantity parsing. Total is computed in cents. |
| **4. Evaluate Policy** | Category-based rules determine required approvers and auto-approve limit. Low-value purchases may skip approval entirely. |
| **5. Start Approval** | An `ApprovalTask` is created for each required approver role (manager, dept_head, procurement, finance), assigned via persona map. |
| **6. Approve / Reject** | Each approver records a decision. Any rejection immediately rejects the request. All approvals advance it to `approved`. |
| **7. Generate PO** | A Purchase Order draft is generated from matched catalog items. Unresolved items are flagged for manual review but do not block generation. |

Every action is recorded as an immutable `AuditEvent` in the timeline.

---

## API Reference

All endpoints are under the prefix `/api/v1`. Interactive docs available at **http://localhost:8000/docs**.

### Reference Data

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/health` | Health check with store statistics |
| `GET` | `/api/v1/users` | List mock users |
| `GET` | `/api/v1/departments` | List departments and cost centers |

### Requests

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/requests` | Create a new purchase request |
| `GET` | `/api/v1/requests` | List requests (filter by requester, status; paginated) |
| `GET` | `/api/v1/requests/{request_id}` | Get a single request with all linked entities |
| `GET` | `/api/v1/requests/{request_id}/clarifications` | List clarifications for a request |

### Clarifications

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/clarifications` | Create a clarification question |
| `GET` | `/api/v1/clarifications/{clarification_id}` | Get a single clarification |
| `POST` | `/api/v1/clarifications/{clarification_id}/answer` | Submit an answer |

### Catalog

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/catalog/match` | Match raw items to catalog (persist or preview mode) |

### Policy

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/policy/{request_id}/evaluate` | Evaluate policy rules for a request |

### Approvals

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/approvals/start` | Create approval tasks from a policy result |
| `POST` | `/api/v1/approvals/{task_id}/decide` | Record an approver's decision |
| `GET` | `/api/v1/approvals/{task_id}` | Get a single approval task |
| `GET` | `/api/v1/approvals` | List tasks (filter by approver) |

### Purchase Orders

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/po/generate` | Generate a PO draft from a matched request |
| `GET` | `/api/v1/po/{po_id}` | Get a single purchase order |

### Audit

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/audit/{request_id}` | Timeline events for a single request |
| `GET` | `/api/v1/audit` | All events (filter by request, action) |

### AI Agents

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/agents/status` | Check watsonx availability and registered tools |
| `POST` | `/api/v1/agents/intake-analysis/{request_id}` | Analyze request for missing fields |
| `POST` | `/api/v1/agents/intake-preview` | Preview intake analysis on unsaved form data |
| `POST` | `/api/v1/agents/policy-explanation/{request_id}` | Explain policy result in plain language |
| `POST` | `/api/v1/agents/catalog-explanation` | Explain catalog matching confidence |
| `POST` | `/api/v1/agents/approval-notification/{request_id}` | Draft approval context for approvers |
| `POST` | `/api/v1/agents/run-intake/{request_id}` | Auto-create clarifications via agent |
| `POST` | `/api/v1/agents/run-stage/{request_id}` | Execute all agents registered for the current stage |

---

## Frontend Pages

The frontend is a multi-page application (no SPA framework). Pages are served as static files by FastAPI.

| Page | URL | Description |
|---|---|---|
| Landing | `/` | Hero section, feature overview, navigation |
| Dashboard | `/pages/dashboard.html` | Request list with status filters and pagination |
| New Request | `/pages/request_form.html` | Form to create a purchase request with line items |
| Request Detail | `/pages/request_detail.html` | Full request view: linked entities, clarifications, approvals, PO, audit timeline |
| Approval Queue | `/pages/approval_tasks.html` | Approver queue to review and decide tasks |

**JavaScript conventions:**
- `caseUtils.js` — bidirectional snake_case ↔ camelCase key conversion
- `api.js` — domain API client; automatically converts keys at the boundary
- `ui.js` — base fetch wrapper and shared UI helpers

---

## AI Agent Integration

Agents provide language assistance at each stage of the workflow. They never make business decisions.

| Agent | When it runs | What it does |
|---|---|---|
| **Intake Agent** | After request creation | Identifies missing fields, drafts clarification questions |
| **Policy Agent** | After policy evaluation | Explains rules applied and approver requirements in plain language |
| **Catalog Agent** | After catalog matching | Explains match confidence and guides resolution of unmatched items |
| **Approval Agent** | Before approval routing | Drafts context summary for approvers |

**Graceful fallback:** If `WATSONX_API_KEY` or `WATSONX_PROJECT_ID` are not set, the `StubClient` is used automatically. All agent endpoints still return valid responses using deterministic templates — no errors, no configuration required.

Check agent status at any time: `GET /api/v1/agents/status`

---

## Seed Data

The following data is loaded at startup from `shared/data/`:

### Users (9 mock users)

| Role | User |
|---|---|
| Requester / manager | Alice, Bob |
| Department head | Carol |
| Procurement officer | Frank |
| Finance approver | Grace |
| Other staff | Dave, Eve, Heidi, Ivan |

### Catalog (~20 items across 7 categories)

| Category | Example items |
|---|---|
| Wafers | Prime silicon wafers, monitor wafers |
| Specialty chemicals | Photoresist, CMP slurry, isopropyl alcohol |
| Cleanroom consumables | Wipers, gloves |
| Equipment spare parts | Pump rebuild kits, seal kits, mass flow controllers |
| Testing materials | Probe cards, test coupons |
| MRO | HEPA filters, drive belts |
| Supplier services | Calibration services, audit support |

### Policy Rules (16 rules)

Category-based thresholds determine auto-approve limits and required approvers. Example rules:

- Wafers < $3,000 → manager + procurement required
- Wafers ≥ $3,000 → manager + dept_head + procurement + finance required
- Cleanroom consumables < $150 → auto-approved

### Personas

Role-to-user mappings for automatic approval task assignment:
- `manager` → Bob
- `dept_head` → Carol
- `procurement` → Frank
- `finance` → Grace

### Demo State

`shared/data/demo_state.json` contains a pre-seeded request ("ETCH-03 resist top-up + seal kits before Tuesday PM") with linked clarifications, policy results, and audit events for live demonstrations.

---

## Architecture Notes

**In-memory database:** There is no SQL or NoSQL database. All data lives in Python dictionaries and lists, initialized from seed JSON at startup. Data is lost when the server restarts. This is intentional for a demo/prototype context.

**Layered separation:**
1. **Routes** (`backend/routes/`) — HTTP handling, request parsing, response shaping only
2. **Services** (`backend/services/`) — Deterministic business logic, status transitions, validation
3. **Agents** (`backend/agents/`) — AI-assisted language interpretation; never called on the critical path
4. **Database** (`backend/database.py`) — In-memory CRUD store
5. **Models** (`backend/models.py`) — Pydantic validation and serialization

**Monetary values:** All prices and totals are stored as integers in cents to avoid floating-point precision issues.

**IDs:** All entity IDs are UUID4 hex strings.

**CORS:** Configured for `http://localhost:8000` and `http://127.0.0.1:8000` only. Update `DEV_ALLOWED_ORIGINS` in `backend/utils/settings.py` for other environments.


