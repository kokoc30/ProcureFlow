# ProcureFlow - Challenge Fit Notes

## Selected Challenge Direction

Semiconductor manufacturing supply-chain procurement.

## Why ProcureFlow Fits

Semiconductor fabs depend on timely procurement of critical materials, equipment parts, and clean-room consumables. Delays in any of these directly threaten production continuity - a missing photoresist shipment or an overdue seal kit can idle an entire fab line.

ProcureFlow maps to this problem because:
- **Multi-step procurement workflow** mirrors how fab operations teams actually buy materials: request, clarify, check policy, approve, and order.
- **Clarification loop** addresses the reality that engineers often submit incomplete requests under time pressure - the system catches missing justification, delivery timing, or operating-impact details before routing for approval.
- **Deterministic policy engine** enforces spend thresholds, category-specific approval chains, and low-risk fast paths for routine supplies - exactly the controls a semiconductor procurement team needs.
- **Approval routing** reflects real org structures: fab manager, department head, procurement, and finance sign-offs at configurable thresholds.
- **Audit trail** provides the traceability that semiconductor supply-chain compliance requires.
- **Scoped watsonx support** helps with language-heavy workflow steps without taking over procurement judgment.

## What Stays Unchanged

The following are unchanged from the original architecture - no unsupported features, integrations, or technical scope were added for this challenge alignment:
- Request intake -> clarification -> policy -> approval -> PO workflow
- HTML/CSS/JS frontend, Python/FastAPI backend
- IBM watsonx Orchestrate coordination with Granite-backed language assistance and graceful fallback
- Deterministic policy engine, approval service, audit service, and PO generation
- In-memory database with mock JSON seed data
- 58-test pytest suite
- API contract structure (`/api/v1/*`)

## Language Conventions

Use these terms consistently across the UI, demo script, README, and pitch materials:

| Term | Use for |
|------|---------|
| semiconductor supply-chain procurement | Top-level product positioning |
| fab operations / fab line | The operational context - where materials are consumed |
| critical materials | Photoresist, CMP slurry, monitor wafers, IPA |
| equipment parts | Maintenance kits, seal kits, replacement components |
| clean-room consumables | Gloves, wipes, garments - low-cost but operationally necessary |
| supplier lead times | Why procurement speed matters |
| preferred supplier / vendor context | Intake-level context captured in notes when the requester already knows the vendor |
| production continuity / line downtime risk | The business consequence of procurement delays |
| request owner | Neutral label for the requester across Fab Operations, Engineering, and Quality |
| fab manager | Default first-level approver persona |
| watsonx Orchestrate | The workflow coordination layer for stage-specific AI support |
| Granite assistance | Narrow language help for messy requests, clarification questions, and grounded explanations |

## What to Avoid

- Generic office-purchasing language (laptops, chairs, swag kits, office supplies)
- Flashy AI or chatbot framing - ProcureFlow is an operational workflow tool
- Implying features that do not exist (ERP integration, real supplier APIs, authentication)
- Overstating the AI role - watsonx helps with orchestration and language support; approvals, routing, totals, and status transitions remain deterministic
- Suggesting that AI replaces procurement, operations, or finance judgment
