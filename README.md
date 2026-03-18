# ProcureFlow

**ProcureFlow** is an AI-assisted procurement intake and approval workflow for semiconductor manufacturing and supply-chain operations, built for an IBM watsonx / watsonx Orchestrate hackathon.

It turns a free-text purchase request from a fab operations team into a structured procurement flow:
- collect request details for critical materials, equipment parts, or clean-room consumables
- ask for missing information
- apply procurement policy checks
- route for approval
- generate a procurement-ready summary / PO draft
- show status and audit trail end to end

The product is designed as a **serious enterprise workflow demo** for semiconductor supply-chain procurement, not a generic chatbot. The focus is on production continuity, material availability, policy control, and approval speed.

---

## Core Demo Story

A process engineer submits a purchase request in plain language — for example, photoresist chemicals needed before a fab line runs out of safety stock, or replacement parts for an etch chamber scheduled for preventive maintenance.

ProcureFlow then:
1. extracts the important fields
2. identifies missing information
3. asks clarifying questions
4. applies procurement and approval rules
5. determines the approval path
6. generates a structured procurement summary
7. records every step in an audit timeline

This makes the app a strong fit for IBM watsonx Orchestrate workflow automation, because it combines:
- multi-step reasoning
- human-in-the-loop clarification
- rule-based decisions
- structured outputs
- workflow visibility

---

## MVP Scope

### In scope
- request intake form
- clarification loop for missing details
- mock item catalog / supplier data (fab materials, equipment parts, clean-room supplies)
- deterministic policy engine
- approval routing
- approval / rejection actions
- audit log / status timeline
- procurement summary or PO-style draft
- IBM watsonx-backed agent step for clarification and structured workflow assistance

### Out of scope for hackathon MVP
- real ERP integrations
- production email / Slack integration
- full authentication / SSO
- advanced analytics dashboards
- complex vendor onboarding
- large enterprise policy engines
- full production document export system

---

## Tech Stack

### Frontend
- HTML
- CSS
- JavaScript

### Backend
- Python
- FastAPI

### Agent / AI Layer
- IBM watsonx Orchestrate coordinates stage-specific workflow support
- Granite or another configured watsonx model handles narrow language tasks
- Python services keep policy, routing, totals, validation, and status transitions deterministic

### Data
- mock JSON data for:
  - catalog items (photoresist, CMP slurry, monitor wafers, seal kits, clean-room supplies)
  - suppliers
  - departments (Fab Operations, Process Engineering, Equipment Maintenance, Quality, Supply Chain, Procurement, Finance, R&D)
  - approval thresholds
  - policy rules
  - seeded demo workflow state

---

## Product Principles

ProcureFlow is being built with these principles:
- **enterprise-first UX**
- **clear workflow over flashy AI**
- **deterministic rules where reliability matters**
- **AI only where it adds real value**
- **polished, demo-ready outputs**
- **strict scope control for hackathon delivery**

---

## Architecture

```text
Frontend (HTML/CSS/JS)
  -> Request intake UI
  -> Clarification UI
  -> Approval dashboard
  -> Audit timeline
  -> Procurement summary view

Backend (FastAPI)
  -> Request routes
  -> Clarification routes
  -> Policy engine
  -> Approval workflow service
  -> Audit event service
  -> Mock data access layer
  -> deterministic procurement services
  -> watsonx integration layer

IBM watsonx Orchestrate
  -> coordinates intake, clarification, policy summary, catalog support,
     approval status handling, and PO-readiness support

Granite / configured watsonx model
  -> interprets messy request language when helpful
  -> drafts clarification questions
  -> produces grounded explanation text from deterministic outputs
```

---

## Repo Structure

```text
frontend/
  pages/           – standalone HTML pages
  css/             – stylesheets (variables, global, per-page)
  js/              – scripts (ui helpers, per-page logic)
  assets/          – images, SVGs

backend/
  main.py          – FastAPI entry point
  models.py        – Pydantic data models
  database.py      – in-memory store and CRUD helpers
  routes/          – API route modules
  services/        – business logic (policy engine, approvals, etc.)
  agents/          – IBM watsonx agent layer (intake, policy, catalog, approval)
  utils/           – settings, enums, helpers

shared/
  data/            – mock JSON data (catalog, users, departments, policies, personas)
  contracts/       – JSON schema contracts

tests/             – pytest suite (58 tests)
docs/
README.md
```

---

## Main User Flow

### 1. Request submission
A fab operations or engineering team member submits a purchase request with fields like:
- requester name
- department
- cost center
- request title
- material / part / service lines (for example, "2 etch chamber o-ring seal kits" or "1 lot 300mm monitor wafers")
- operational context and supplier notes
- justification (production impact, maintenance need, or safety stock risk)
- target delivery date

### 2. Clarification step
If required information is missing, the system asks follow-up questions.

Examples:
- What is the production impact if this material is unavailable?
- Which fab line requires this item?
- What delivery date is required to support the maintenance or production plan?
- Is there preferred vendor context or an existing work order we should capture?

### 3. Policy check
The backend applies deterministic procurement rules such as:
- approval thresholds by amount
- category-based routing for wafers, specialty chemicals, clean-room consumables, spare parts, MRO items, testing materials, and supplier services
- low-risk auto-approval thresholds for routine consumables and MRO items
- manager, procurement, department head, and finance approval requirements by threshold

### 4. Approval routing
The system assigns the approval path, for example:
- fab manager approval
- department head approval
- procurement review
- finance review

### 5. Procurement summary
The app generates a structured summary / PO-style draft showing:
- normalized request details
- decision summary
- missing info resolved
- policy outcome
- recommended next step

### 6. Audit trail
Every step is logged in a timeline:
- request created
- clarification requested
- clarification answered
- policy evaluated
- approval assigned
- approval decision recorded
- summary generated

---

## IBM watsonx Role

ProcureFlow uses IBM watsonx in a tightly scoped way so the demo feels credible to operations, procurement, and finance stakeholders.

### watsonx Orchestrate coordinates
- intake analysis and clarification handling
- policy summary support
- catalog explanation and fulfillment-readiness support around the PO draft
- approval status handling and workflow summaries

### Granite or another configured watsonx model is used for
- interpreting messy request wording
- drafting clarification questions
- producing grounded explanation text from deterministic results

### Keep deterministic in Python
- approval thresholds
- policy logic
- routing rules
- totals and validation
- audit event creation
- status transitions
- approval decisions and PO generation

AI does not approve or reject requests, and it does not replace procurement judgment. This separation keeps the workflow reliable, auditable, and easy to explain in a demo.

---

## API Direction

Recommended API prefix:

```text
/api/v1
```

Example route groups:
- `/api/v1/requests`
- `/api/v1/clarifications`
- `/api/v1/policy`
- `/api/v1/approvals`
- `/api/v1/audit`
- `/api/v1/agents`

---

## UI Direction

The interface should look like a real procurement SaaS tool for semiconductor operations:
- clean white / light-neutral surfaces
- structured layout
- strong typography hierarchy
- restrained accent colors
- polished tables and forms
- clear status badges
- timeline-based audit visibility
- no flashy AI gradients
- no toy chatbot look

### Core screens
- request intake page
- clarification page
- approval dashboard
- request detail page
- audit timeline panel
- procurement summary / PO draft view

---

## Getting Started

### 1. Clone the project
```bash
git clone <your-repo-url>
cd <repo-directory>
```

### 2. Set up the backend
```bash
python -m venv .venv
```

Activate it if you want:

**Windows**
```bash
.venv\Scripts\activate
```

**macOS / Linux**
```bash
source .venv/bin/activate
```

Install dependencies:
```bash
python -m pip install -r requirements.txt
```

If you want Watsonx enabled, copy the example env file and fill in your real values:

**Windows PowerShell**
```powershell
Copy-Item .env.example .env
```

**macOS / Linux**
```bash
cp .env.example .env
```

ProcureFlow also runs without a `.env` file. In that mode, the backend uses deterministic fallback behavior for the AI-assisted helpers.

### 3. Run the backend
```bash
python -m uvicorn backend.main:app --reload
```

Windows PowerShell without activating the virtual environment:
```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload
```

### 4. Open the app
Open [http://localhost:8000](http://localhost:8000) in your browser.

The landing page is served by FastAPI at the root URL.
API docs are available at [http://localhost:8000/docs](http://localhost:8000/docs).
Health check: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health).

---

## Testing

Run the test suite to verify backend correctness before demo:

```bash
# Install dependencies (includes pytest + httpx)
python -m pip install -r requirements.txt

# Run all tests
python -m pytest tests/ -v

# Run a specific test file
python -m pytest tests/test_requests.py -v

# Run a single test
python -m pytest tests/test_integration.py::test_full_happy_path -v
```

The suite covers 58 tests across requests, clarifications, catalog, policy, approvals, PO generation, integration paths, and agent adapter behavior. See `docs/test_plan.md` for the full test plan including manual browser checks.

---

## Environment Variables

Create a `.env` file only if you want live Watsonx credentials. The app starts without it.

Copy `.env.example` to `.env` and fill in values as needed:

```env
WATSONX_API_KEY=your_key_here
WATSONX_PROJECT_ID=your_project_id_here
WATSONX_URL=https://us-south.ml.cloud.ibm.com
WATSONX_MODEL_ID=ibm/granite-3-8b-instruct
```

Never commit secrets to the repository.

---

## Fresh Windows Laptop Setup

From a clean PowerShell session in the repo root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload
```

If you do not need live Watsonx access for the demo, you can skip the `Copy-Item .env.example .env` step entirely.

---

## Demo Start Checklist

- Open PowerShell in the repo root.
- Create or reuse `.venv`.
- Install `requirements.txt`.
- Optionally copy `.env.example` to `.env` and add real Watsonx credentials.
- Start the server with `python -m uvicorn backend.main:app --reload` or `.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload`.
- Open `http://localhost:8000`.
- Confirm `http://localhost:8000/api/v1/health` returns `status: ok`.
- Click through landing page, dashboard, request form, request detail, and approval queue before the demo begins.

---

## Definition of Done for MVP

The MVP is complete when:
- a process engineer can submit a purchase request for fab materials or equipment parts
- the system can detect missing fields
- clarification questions are shown
- answers can be submitted
- policy checks run successfully
- approval routing is generated
- approval status can be updated
- a procurement summary is produced
- an audit timeline shows the full workflow
- the UI is coherent and ready for focused polish

---

## Demo Checklist

Before demo time, make sure you can show this flow cleanly:
- create a request for critical fab materials (e.g., photoresist reorder)
- trigger clarification questions
- answer the missing details
- run policy evaluation
- show approval routing
- approve or reject from dashboard
- open the request detail page
- show the audit timeline
- show the final procurement summary
- explain exactly where IBM watsonx is used

---

## Project Status

This project is a complete hackathon MVP.

What's implemented:
1. full request → clarification → policy → approval → PO workflow
2. clean, enterprise-grade UI with consistent state management
3. IBM watsonx Orchestrate coordination and Granite-backed language assistance with graceful fallback
4. 58 automated tests covering all backend services and routes
5. comprehensive documentation and demo script

Design principles:
- mock integrations where production ERP/SSO would go
- deterministic logic for all business-critical decisions
- polished workflow over oversized feature count
- reliability over pretending to be production-ready

---

## Deployment

### Docker (local)

```bash
# Build the image
docker build -t procureflow .

# Run on default port 8000
docker run -p 8000:8000 procureflow

# Run with Watsonx credentials
docker run -p 8000:8000 \
  -e WATSONX_API_KEY=your_key \
  -e WATSONX_PROJECT_ID=your_project_id \
  procureflow

# Run on a custom port
docker run -p 3000:3000 -e PORT=3000 procureflow
```

Open [http://localhost:8000](http://localhost:8000) (or your chosen port).

### Render

1. Push the repo to GitHub.
2. In [Render Dashboard](https://dashboard.render.com), click **New > Blueprint** and connect the repo.
3. Render detects `render.yaml` and creates the web service automatically.
4. In the service **Environment** tab, set `WATSONX_API_KEY` and `WATSONX_PROJECT_ID` if you want live AI features.
5. Deploy. The app will be available at `https://procureflow.onrender.com` (or your chosen name).

The app runs without Watsonx credentials — agents fall back to deterministic templates.

### Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `PORT` | No | `8000` | Server port (set automatically by Render) |
| `WATSONX_API_KEY` | No | *(none)* | IBM watsonx IAM API key |
| `WATSONX_PROJECT_ID` | No | *(none)* | watsonx project ID |
| `WATSONX_URL` | No | `https://us-south.ml.cloud.ibm.com` | watsonx regional endpoint |
| `WATSONX_MODEL_ID` | No | `ibm/granite-3-8b-instruct` | Foundation model ID |
| `CORS_ORIGINS` | No | `http://localhost:8000` | Comma-separated allowed origins |

### Deployment Checklist

- [ ] `docker build -t procureflow .` succeeds
- [ ] `docker run -p 8000:8000 procureflow` starts and serves the landing page
- [ ] `/api/v1/health` returns `{"status": "ok"}`
- [ ] Watsonx env vars are set in Render dashboard (not hardcoded)
- [ ] Render Blueprint deploys from `render.yaml` without errors
- [ ] Health check passes on Render (`/api/v1/health`)

### Optional: Frontend on Vercel

The current architecture serves the frontend as static files from the same FastAPI container. If you later want to host the frontend separately on Vercel:

1. Deploy the `frontend/` directory as a Vercel static site.
2. In `frontend/js/ui.js`, update the API base URL to point to the Render backend (e.g. `https://procureflow.onrender.com/api/v1`).
3. Set `CORS_ORIGINS=https://your-frontend.vercel.app` on the Render service so the backend accepts cross-origin requests.
4. No backend code changes are needed — the CORS configuration already supports external origins via the env var.

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

## Credits

Built for an IBM watsonx / agentic AI hackathon.
