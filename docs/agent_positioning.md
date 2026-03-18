# ProcureFlow Agent Positioning

This note defines how to explain IBM watsonx in ProcureFlow without overstating the AI role.

## Positioning Summary

ProcureFlow uses IBM watsonx in a controlled workflow pattern:

- **watsonx Orchestrate** coordinates stage-specific workflow support across intake, clarification, policy summary support, catalog and fulfillment-readiness support, and approval status handling.
- **Granite or another configured watsonx model** handles narrow language tasks such as interpreting messy request wording, drafting clarification questions, and producing grounded explanation text.
- **Deterministic Python services** remain responsible for policy thresholds, routing rules, totals, validation, status transitions, approval outcomes, PO generation, and audit events.

## What AI Does

- Interprets incomplete or messy request language so the workflow can ask better follow-up questions.
- Drafts clarification questions when required fields or operating context are missing.
- Turns deterministic policy and catalog outputs into grounded, business-readable explanations.
- Supports approval-stage communication with concise status and context summaries.
- Keeps the workflow usable even when the original request is vague or rushed.

## What AI Does Not Do

- Decide whether a request is approved or rejected.
- Change policy thresholds, approval paths, totals, pricing, or validation outcomes.
- Override deterministic routing or status transitions.
- Replace procurement, operations, or finance judgment.
- Introduce facts that are not already in the request or deterministic service outputs.

## Why This Separation Improves Trust

- Operations teams can see that plant-critical controls stay deterministic and auditable.
- Procurement teams keep ownership of policy enforcement and approval judgment.
- Finance reviewers can trust that totals, thresholds, and routing are reproducible.
- Judges can quickly understand that AI is used where language is messy, not where governance must be exact.

## How To Explain It During The Demo

- Lead with workflow orchestration, not generic AI.
- Say that watsonx Orchestrate coordinates the workflow stages and the handoffs between them.
- Say that Granite helps when request language is messy or incomplete, and when the app needs grounded explanation text.
- Emphasize that Python services still own the business rules, approval routing, totals, validation, and state changes.
- Be explicit that AI never makes uncontrolled approval decisions.

## Recommended Talk Track

> ProcureFlow uses IBM watsonx in a tightly scoped way. watsonx Orchestrate coordinates intake, clarification, policy explanation, catalog support, and approval-status messaging, while Granite handles the language-heavy work such as interpreting messy requests, drafting clarification questions, and producing grounded summaries. All approval thresholds, routing rules, totals, validation, status transitions, and PO generation remain deterministic Python, so procurement judgment and governance stay fully in control.
