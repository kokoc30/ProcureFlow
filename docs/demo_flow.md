# ProcureFlow - Canonical Live Demo Flow

This is the canonical live demo scenario for ProcureFlow. It uses a seeded in-progress request so the walkthrough starts from a believable operational problem instead of a blank slate.

---

## Canonical Scenario

**Scenario name:** ETCH-03 resist top-up and seal kits before the Tuesday maintenance window

**Why this works live:**
- It starts with a messy, rushed operations request
- It immediately shows clarification behavior
- It deterministically routes to manager plus procurement review
- It finishes with a structured PO draft and a clean audit trail
- The stakes are easy to explain: avoid a line restart delay on Fab Line 3

---

## Seeded Record

**Seed file:** `shared/data/demo_state.json`

**Seeded request ID:** `9f1c2d3e4a5b6c7d8e9f0a1b2c3d4e5f`

**Seeded request title:** `ETCH-03 resist top-up + seal kits before Tuesday PM`

**Starting status:** `clarification`

**Requester:** Alice Johnson, Fab Operations

**Messy raw request lines:**
- `need 1 krf photoresist for line 3 hold by Tue night`
- `2 seal kits for etch chamber pm on etch-03`

**Seeded clarification questions:**
- `What is the production or maintenance impact if the photoresist and seal kits are not on site before the ETCH-03 window?`
- `What delivery date is required to support the ETCH-03 maintenance plan and avoid a line restart delay?`

---

## Ideal Click Path

1. Open **Dashboard** and select the seeded request titled **ETCH-03 resist top-up + seal kits before Tuesday PM**
2. On **Request Detail**, show the messy raw items and the two clarification questions
3. Submit both clarification answers so the request moves into **Policy Review**
4. Click **Match Catalog**, then **Evaluate Policy**
5. Click **Open Approval Queue**
6. Open **Approvals** and approve the manager task and the procurement task
7. Return to **Request Detail** and click **Generate PO Draft**

---

## Exact Narration

Use this story live:

> This request came in the way fab teams often work under pressure: short, messy, and operationally urgent. Alice from Fab Operations needs KrF photoresist and chamber seal kits before the ETCH-03 maintenance window closes. ProcureFlow does not guess. It asks for the missing operating impact and the delivery timing, then turns the rushed note into a structured procurement record, applies deterministic policy, routes the right approvals, and produces a PO-ready result with a full audit trail.

---

## Recommended Clarification Answers

Use these answers so the rest of the flow is clean and believable:

- **Operational impact answer:** `Fab Line 3 photoresist inventory is below safety stock and ETCH-03 cannot restart after the Tuesday PM window without the new seal kits.`
- **Delivery date answer:** `2026-03-17`

---

## What the Audience Should Notice

### Before

- The request reads like a rushed plant note, not a clean purchase order
- Key fields are missing
- The request cannot move forward safely

### After

- Raw language becomes structured catalog-matched line items
- The request gets a deterministic policy result
- Approval routing is explicit and role-based
- The PO draft is readable and operationally ready
- The audit trail tells the whole story from intake through fulfillment readiness

---

## Expected Deterministic Outcome

After clarification answers are submitted and the workflow is completed:

- **Catalog match:** `KrF Photoresist 5L` + `2 Etch Chamber O-Ring Seal Kits`
- **Expected total:** `$2,090.00`
- **Policy outcome:** manager plus procurement approval required
- **Expected approvers:** Bob Smith (manager), Frank Lee (procurement)
- **End state:** approved request with a generated PO draft and a complete audit trail

---

## Exact 6-Step Live Sequence

1. Start on **Dashboard**, open the seeded ETCH-03 request, and point out that it is already in `Needs Info` because the intake was messy and incomplete.
2. On **Request Detail**, show the raw material lines and answer the two clarification questions using the prepared Fab Line 3 impact and delivery-date responses.
3. Click **Match Catalog** so the request transforms from rushed text into structured semiconductor items with quantities, suppliers, and a calculated total.
4. Click **Evaluate Policy** and explain that the result is deterministic Python: the specialty-material request now requires manager plus procurement review.
5. Click **Open Approval Queue**, move to **Approvals**, and record approvals for Bob Smith and Frank Lee to show controlled routing instead of free-form AI decisions.
6. Return to **Request Detail**, click **Generate PO Draft**, and finish on the audit trail so judges can see request, clarification, policy, approval, and PO events as one coherent operational story.
