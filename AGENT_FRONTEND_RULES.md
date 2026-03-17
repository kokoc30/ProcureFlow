# AGENT_FRONTEND_RULES.md

## Purpose

This file defines the required working rules for any coding agent contributing to the **ProcureFlow** frontend.

The goal is to keep the app:
- professional
- enterprise-grade
- visually polished
- consistent with the current architecture
- safe from random UI rewrites that break working logic

This project is **not** a generic AI demo.  
It is a **B2B procurement workflow product** for an IBM watsonx / agentic AI hackathon.

---

## How to Use This File

Before making any frontend or UI/UX changes, the coding agent must:

1. read this file first
2. inspect the current repo tree
3. inspect the exact page files it is about to modify
4. preserve all working backend and frontend logic
5. use these rules as the default guardrails for every frontend step

When I give you a new frontend-heavy step, I may say:

> Read and follow `AGENT_FRONTEND_RULES.md` before making changes.

If this file exists in the project root, treat it as an authoritative instruction file for frontend work.

---

## Project Context

**Product:** ProcureFlow Agent  
**Type:** enterprise procurement intake and approval workflow demo  
**Frontend:** HTML, CSS, JavaScript  
**Backend:** Python / FastAPI  
**Agent layer:** IBM watsonx / watsonx Orchestrate  

Current priorities:
1. keep the core workflow correct
2. keep architecture clean
3. make the UI look enterprise-grade
4. avoid flashy AI-demo styling
5. preserve existing conventions and contracts

---

## Current Working Conventions

These must remain true unless I explicitly approve a change.

### Backend / API
- backend stays **snake_case**
- frontend-facing API objects use **camelCase**
- `/api/v1` is the only API base prefix
- `PF.api` is the standard frontend API entry point
- do not replace `PF.api` with scattered raw `fetch()` calls
- do not rename routes casually

### Domain semantics
- `requested_items` = raw free-text intake items
- `items` = normalized structured line items later in the workflow
- policy logic stays deterministic in Python
- request statuses must not be renamed casually
- clarification field names must match backend request fields exactly

### Architecture
- do not introduce a frontend framework
- do not convert the app into React/Vue/etc.
- do not replace the current page structure without approval
- preserve working page flows and current file organization

---

## Workflow Orchestration Rules

These are operating rules for how the coding agent should work on non-trivial frontend tasks.

### 1. Plan Mode Default
For any non-trivial frontend task, first switch into a planning mindset.

Required behavior:
- enter plan mode for any task with 3 or more meaningful steps
- enter plan mode for any task involving architecture, shared styles, data flow, state, or page behavior
- use plan mode for verification passes too, not only for building
- write a short implementation spec before editing when the task is ambiguous
- if something goes sideways, stop and re-plan instead of continuing blindly

### 2. Subagent Strategy
If the environment supports subagents or parallel task execution, use them selectively.

Good uses:
- exploring layout options
- comparing UI structure alternatives
- checking consistency between CSS/JS/HTML
- auditing one page while another pass handles validation

Rules:
- one focused task per subagent
- keep the main thread clean
- use subagents for exploration, research, and parallel analysis
- do not fragment the main implementation logic unnecessarily

### 3. Self-Improvement Loop
After any correction, regression, or user feedback:
- update your working assumptions
- create a clearer rule that prevents the same mistake
- review relevant lessons at the start of the next related task
- treat repeated frontend mistakes as process failures, not random accidents

In practice:
- if a page broke because of naming drift, reinforce naming checks
- if a style regression happened, strengthen dependency inspection before editing
- if validation mapping broke, check API contracts before changing forms again

### 4. Verification Before Done
Never mark a frontend task complete without proving it works.

Required checks:
- run the page and verify behavior
- check browser console for errors
- verify CSS, JS, and API calls all load correctly
- compare intended behavior vs actual behavior
- ask whether a strong senior engineer would approve the change
- when relevant, diff the previous and current behavior, not just the code

### 5. Demand Elegance (Balanced)
For non-trivial changes, pause and ask:
> Is there a more elegant way to do this without over-engineering?

Rules:
- prefer clean structure over patchy fixes
- if a fix feels hacky, replace it with a cleaner solution when realistic
- do not over-engineer obvious small fixes
- challenge your own work before presenting it as complete

### 6. Autonomous Bug Fixing
When a bug is identified:
- inspect logs, errors, and failing behavior first
- trace the failure to root cause
- fix it directly and professionally
- do not ask for unnecessary hand-holding if the problem is already clear
- verify the fix after implementation
- keep user context switching minimal

---

## MCP Usage Rules

The connected MCP servers should be used **selectively**, not blindly.

### Use these MCPs like this

#### 21st.dev MCP
Use for:
- professional SaaS layout patterns
- dashboard structures
- clean cards, tables, filters, side panels
- strong spacing and visual hierarchy
- polished enterprise form composition

#### GitHub UI/UX MCP
Use for:
- usability patterns
- information hierarchy
- enterprise interaction ideas
- workflow clarity
- dashboard and detail-page refinement

#### Google Stitch MCP
Use for:
- page composition
- section layout
- wireframe-like structure refinement
- shell improvements for major workflow screens

#### NanoBananas2 MCP
Use lightly for:
- subtle empty-state visuals
- minor icon/illustration suggestions
- light visual polish only

Do **not** use NanoBananas2 to redesign the product structure.

---

## MCP Guardrails

MCP tools must **not**:
- change backend logic
- change API contracts
- rename fields or route names
- change request status names
- change policy logic
- replace `PF.api`
- rewrite working JavaScript behavior without reason
- turn the app into a generic AI landing page
- inject flashy gradients, neon, oversized blobs, or toy chatbot styling
- make the app look like a marketing site instead of a procurement workflow tool

The MCP tools are there to improve:
- layout
- spacing
- hierarchy
- forms
- tables
- cards
- sidebars
- timeline presentation
- empty states
- loading states
- polished B2B interaction patterns

---

## UI Style Direction

The UI must look like a real enterprise procurement SaaS product.

### Visual tone
- clean
- restrained
- credible
- minimal
- structured
- modern
- polished
- not flashy
- not futuristic for the sake of it
- not “AI-generated looking”

### Preferred style traits
- light neutral backgrounds
- controlled use of accent color
- strong typography hierarchy
- clear section spacing
- polished tables and forms
- clear action bars
- well-structured detail pages
- readable timelines
- purposeful empty states
- subtle shadows
- restrained border radii

### Avoid
- random gradients
- glowing effects
- giant rounded blobs
- card overload
- cluttered dashboards
- oversaturated accent colors
- generic chatbot chrome
- loud visual gimmicks

---

## Frontend Workflow Rule

For each frontend-heavy step, work in **two passes**:

### Pass 1 — Functional implementation
Make the page fully work:
- correct API usage
- correct data binding
- validation
- loading states
- error handling
- state updates
- navigation flow

### Pass 2 — UI polish
Only after the logic works:
- improve spacing
- improve hierarchy
- improve layout
- refine forms/tables/cards/panels
- improve empty/loading/error states
- use MCP tools selectively for better SaaS-quality presentation

Do not skip straight to visual polish before the page works.

---

## Required Behavior for Every Frontend Step

Before editing:
1. inspect the current repo tree
2. inspect the exact page files being changed
3. identify existing CSS and JS dependencies
4. preserve all working logic
5. keep naming and contracts consistent

When editing:
- keep changes modular
- avoid unrelated rewrites
- reuse the existing design system where possible
- keep CSS class naming consistent
- keep page-specific CSS separate where appropriate
- keep behavior inside the current JS file structure unless there is a strong reason to refactor

After editing:
- verify the page still works end-to-end
- verify no console errors
- verify API calls still use `PF.api`
- verify backend payload expectations did not change
- verify styles remain consistent with the rest of the app

---

## Required States on Major Pages

For each main page, include professional handling for:
- loading state
- success state
- empty state
- error state
- validation state
- disabled/submitting state when relevant

This is mandatory for professional-looking product behavior.

---

## Request for Output From the Coding Agent

After any frontend step, the coding agent should return:

1. what it changed
2. exact files changed
3. whether logic was preserved
4. whether any MCP sources influenced the polish
5. what manual checks I should run
6. any remaining UI gaps

---

## Do Not Break These Pages

As the project grows, do not casually break or redesign completed working pages without approval:
- `frontend/pages/request_form.html`
- `frontend/pages/request_detail.html`
- `frontend/pages/dashboard.html`
- `frontend/pages/approval_tasks.html`

When refining one page, make sure it still fits the whole product visually.

---

## Recommended Prompt Add-On

When I give you a new frontend step, assume I may prepend this instruction:

> Read and follow `AGENT_FRONTEND_RULES.md` before making changes. Use MCP tools selectively for presentation polish only. Preserve current architecture, routes, data contracts, and working JavaScript behavior.

Treat that as binding unless I explicitly say otherwise.

---

## Final Rule

This project should feel like a serious product made by a thoughtful founder-engineer.

If a proposed UI change makes the app look:
- more generic
- more flashy
- more cluttered
- less credible
- less consistent
- or more fragile

do **not** make that change.

Always prefer:
**clarity, credibility, polish, consistency, and workflow usability**.
