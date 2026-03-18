# ProcureFlow – Test Plan

## Test Suite Overview

| File | Tests | Covers |
|------|-------|--------|
| `test_requests.py` | 8 | Request creation, validation, listing, 404 |
| `test_clarifications.py` | 7 | Create/answer lifecycle, back-fill, status transitions |
| `test_catalog.py` | 6 | Alias matching, quantities, unknown items, persist mode |
| `test_policy.py` | 6 | Auto-approve, threshold tiers, idempotency |
| `test_approvals.py` | 7 | Start approval, approve/reject cascade, guards |
| `test_po.py` | 5 | PO generation, totals, format, idempotency |
| `test_integration.py` | 2 | Full happy path, auto-approve path |
| `test_agents.py` | 17 | watsonx adapter selection, fallback behavior, JSON parsing |
| **Total** | **58** | |

## Running Tests

```bash
# Install dependencies (from project root)
pip install -r requirements.txt

# Run all tests with verbose output
python -m pytest tests/ -v

# Run a single file
python -m pytest tests/test_requests.py -v

# Run a single test
python -m pytest tests/test_integration.py::test_full_happy_path -v
```

## Error Code Coverage

| Code | Meaning | Tested In |
|------|---------|-----------|
| 404 | Not found | test_requests (requester, request), test_clarifications (request, clarification), test_approvals (request, task), test_po (request), test_policy (request) |
| 409 | Conflict / wrong state | test_clarifications (wrong status), test_policy (wrong status, idempotency), test_approvals (wrong status), test_po (idempotency) |
| 422 | Validation error | test_requests (cost_center, empty items), test_catalog (no input), test_approvals (invalid decision), test_po (no items) |
| 403 | Forbidden | test_clarifications (wrong user), test_approvals (wrong approver) |

## DB Reset Strategy

Tests use an autouse pytest fixture (`reset_db`) that clears the 6 mutable collections before each test:
- `requests`, `clarifications`, `approval_tasks`, `policy_results`, `purchase_orders`, `audit_events`

Seed data (users, catalog, policies, departments, personas) is preserved across all tests.

## Manual Browser Checks (Pre-Demo)

### Pages Load
- [ ] `http://localhost:8000/` — landing page renders
- [ ] Dashboard page — loads without console errors
- [ ] Request form — all fields render, department dropdown populated
- [ ] Request detail — shows linked entities (clarifications, approvals, PO)
- [ ] Approval tasks page — lists pending tasks

### Workflow Walk-Through
- [ ] Submit a request with missing justification → clarification status shown
- [ ] Answer all clarifications → status transitions to policy review
- [ ] Policy evaluation runs → correct approval tier displayed
- [ ] Approve all tasks → request moves to approved
- [ ] Generate PO → PO number and total displayed correctly
- [ ] Audit trail shows all events in chronological order

### API Spot Checks (curl or browser dev tools)
- [ ] `GET /api/v1/health` → 200 with store stats
- [ ] `GET /api/v1/users` → list of 9 users
- [ ] `GET /api/v1/departments` → list of 8 departments
- [ ] `POST /api/v1/requests` with valid payload → 201
- [ ] `POST /api/v1/catalog/match` with `{"requested_items": ["krf photoresist"]}` → matched item

## Known Limitations

- **No auth**: Tests do not cover authentication (MVP uses mock personas)
- **No concurrency**: Tests run sequentially against in-memory store
- **No frontend tests**: Only backend API coverage; UI verified manually
- **Agent endpoints**: Agent/LLM endpoints (`/api/v1/agents/*`) are not tested as they depend on external LLM availability
