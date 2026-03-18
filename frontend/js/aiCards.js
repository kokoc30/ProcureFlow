/**
 * ProcureFlow - AI assistance card rendering module.
 *
 * Provides structured, on-demand AI workflow assistance cards for:
 *   - Intake analysis (clarification guidance)
 *   - Policy explanation
 *   - Catalog match explanation
 *   - Approval summary
 *
 * Also provides the intake preview panel for the request form page.
 *
 * Load order: ui.js -> caseUtils.js -> api.js -> aiCards.js -> page script.
 */

(function () {
    "use strict";

    var api = PF.api;

    /* ==================================================================
       Field label map (mirrors backend _CHECKABLE_FIELDS)
       ================================================================== */

    var FIELD_LABELS = {
        justification: "Justification",
        cost_center: "Cost Center",
        delivery_date: "Delivery Date",
    };

    /* ==================================================================
       Shared DOM helpers
       ================================================================== */

    function el(tag, cls, text) {
        var node = document.createElement(tag);
        if (cls) node.className = cls;
        if (text) node.textContent = text;
        return node;
    }

    function aiBadge(aiAvailable) {
        var span = el("span", "ai-badge");
        if (aiAvailable) {
            span.classList.add("ai-badge-ai");
            span.textContent = "AI-Generated";
        } else {
            span.classList.add("ai-badge-template");
            span.textContent = "Template";
        }
        return span;
    }

    function skeletonLoading() {
        var wrap = el("div", "ai-loading");
        for (var i = 0; i < 3; i++) {
            wrap.appendChild(el("div", "skeleton skeleton-line"));
        }
        return wrap;
    }

    function errorBlock(message, onRetry) {
        var wrap = el("div", "ai-error-state");
        var msg = el("p", "ai-error-text", message);
        wrap.appendChild(msg);
        if (onRetry) {
            var btn = el("button", "btn btn-ghost btn-sm", "Retry");
            btn.addEventListener("click", onRetry);
            wrap.appendChild(btn);
        }
        return wrap;
    }

    /* ==================================================================
       Card factory
       ================================================================== */

    /**
     * Create an AI card shell with header, badge slot, generate button, and body.
     * Returns a controller object with references and state helpers.
     */
    function createAiCard(id, title) {
        var card = el("div", "card ai-card mb-4");
        card.setAttribute("data-ai-card", id);

        // Header
        var header = el("div", "card-header");
        var titleEl = el("span", "ai-card-title", title);
        var badgeSlot = el("span", "ai-badge-slot");
        var btn = el("button", "btn btn-secondary btn-sm ai-generate-btn", "Generate");

        header.appendChild(titleEl);
        header.appendChild(badgeSlot);
        header.appendChild(btn);

        // Body
        var body = el("div", "card-body");
        var empty = el("p", "ai-empty-text", "Click Generate to run AI analysis.");
        empty.style.fontSize = "var(--text-sm)";
        empty.style.color = "var(--color-text-muted)";
        body.appendChild(empty);

        card.appendChild(header);
        card.appendChild(body);

        var refs = {
            card: card,
            body: body,
            badge: badgeSlot,
            btn: btn,
            generated: false,
        };

        return refs;
    }

    function setLoading(refs) {
        refs.body.innerHTML = "";
        refs.body.appendChild(skeletonLoading());
        PF.setLoading(refs.btn, true);
    }

    function setError(refs, message, onRetry) {
        refs.body.innerHTML = "";
        refs.body.appendChild(errorBlock(message, onRetry));
        PF.setLoading(refs.btn, false);
    }

    function setContent(refs, contentEl, aiAvailable) {
        refs.body.innerHTML = "";
        refs.body.appendChild(contentEl);
        refs.badge.innerHTML = "";
        refs.badge.appendChild(aiBadge(aiAvailable));
        refs.generated = true;
        PF.setLoading(refs.btn, false);
        refs.btn.textContent = "Refresh";
    }

    /* ==================================================================
       Intake analysis content builder
       ================================================================== */

    function buildIntakeContent(data) {
        var wrap = el("div", "ai-card-content");

        // Summary
        if (data.intakeSummary) {
            wrap.appendChild(el("p", "ai-summary-text", data.intakeSummary));
        }

        // Missing fields
        if (data.missingFields && data.missingFields.length > 0) {
            wrap.appendChild(el("div", "ai-section-label", "Missing Fields"));
            var tags = el("div", "ai-missing-tags");
            for (var i = 0; i < data.missingFields.length; i++) {
                var label = FIELD_LABELS[data.missingFields[i]] || data.missingFields[i];
                tags.appendChild(el("span", "badge badge-clarification", label));
            }
            wrap.appendChild(tags);
        }

        // Suggested questions
        if (data.suggestedQuestions && data.suggestedQuestions.length > 0) {
            wrap.appendChild(el("div", "ai-section-label", "Clarification Questions"));
            for (var j = 0; j < data.suggestedQuestions.length; j++) {
                var q = data.suggestedQuestions[j];
                var item = el("div", "ai-question-item");

                var qText = el("div", "ai-question-text", q.question);
                item.appendChild(qText);

                if (q.field) {
                    var fieldLabel = FIELD_LABELS[q.field] || q.field;
                    var tag = el("span", "clarification-field-tag", fieldLabel);
                    qText.appendChild(tag);
                }

                if (q.reason) {
                    item.appendChild(el("div", "ai-question-reason", q.reason));
                }

                wrap.appendChild(item);
            }
        }

        return wrap;
    }

    /* ==================================================================
       Policy explanation content builder
       ================================================================== */

    function buildPolicyContent(data) {
        var wrap = el("div", "ai-card-content");

        if (data.businessSummary) {
            wrap.appendChild(el("p", "ai-summary-text", data.businessSummary));
        }

        if (data.flagExplanations && data.flagExplanations.length > 0) {
            wrap.appendChild(el("div", "ai-section-label", "Policy Flags"));
            var flags = el("div", "policy-flags");
            for (var i = 0; i < data.flagExplanations.length; i++) {
                var f = data.flagExplanations[i];
                var row = el("div", "policy-flag " + (f.passed ? "policy-flag-pass" : "policy-flag-fail"));

                var icon = el("span", "policy-flag-icon", f.passed ? "\u2713" : "\u2717");
                row.appendChild(icon);

                var text = el("span", "policy-flag-text");
                var name = el("strong", null, f.ruleName + ": ");
                text.appendChild(name);
                text.appendChild(document.createTextNode(f.explanation));
                row.appendChild(text);

                flags.appendChild(row);
            }
            wrap.appendChild(flags);
        }

        if (data.nextSteps) {
            wrap.appendChild(el("div", "ai-section-label", "Next Steps"));
            wrap.appendChild(el("p", "ai-summary-text", data.nextSteps));
        }

        return wrap;
    }

    /* ==================================================================
       Catalog explanation content builder
       ================================================================== */

    function buildCatalogContent(data) {
        var wrap = el("div", "ai-card-content");

        if (data.matchNarrative) {
            wrap.appendChild(el("p", "ai-summary-text", data.matchNarrative));
        }

        if (data.itemExplanations && data.itemExplanations.length > 0) {
            wrap.appendChild(el("div", "ai-section-label", "Item Matches"));
            for (var i = 0; i < data.itemExplanations.length; i++) {
                var item = data.itemExplanations[i];
                var row = el("div", "ai-match-row");

                var orig = el("span", "ai-match-original", item.originalText);
                row.appendChild(orig);

                row.appendChild(el("span", "ai-match-arrow", "\u2192"));

                var target = item.matchedTo || "Unresolved";
                var targetCls = item.matchedTo ? "ai-match-target" : "ai-match-target ai-match-unresolved";
                row.appendChild(el("span", targetCls, target));

                if (item.confidenceNote) {
                    row.appendChild(el("span", "ai-match-confidence", item.confidenceNote));
                }

                wrap.appendChild(row);
            }
        }

        if (data.unresolvedGuidance) {
            wrap.appendChild(el("div", "ai-section-label", "Guidance"));
            wrap.appendChild(el("p", "ai-summary-text", data.unresolvedGuidance));
        }

        return wrap;
    }

    /* ==================================================================
       Approval notification content builder
       ================================================================== */

    function buildApprovalContent(data) {
        var wrap = el("div", "ai-card-content");

        if (data.notificationSummary) {
            wrap.appendChild(el("p", "ai-summary-text", data.notificationSummary));
        }

        var fields = [
            { label: "Line Items", value: data.lineItemsSummary },
            { label: "Policy Context", value: data.policyContext },
            { label: "Urgency", value: data.urgencyNote },
        ];

        for (var i = 0; i < fields.length; i++) {
            if (!fields[i].value) continue;
            var row = el("div", "field-row");
            row.appendChild(el("span", "field-label", fields[i].label));
            row.appendChild(el("span", "field-value", fields[i].value));
            wrap.appendChild(row);
        }

        return wrap;
    }

    /* ==================================================================
       Card renderers for request_detail
       ================================================================== */

    function renderIntakeCard(container, requestId) {
        var refs = createAiCard("intake", "Clarification Guidance");

        function generate() {
            setLoading(refs);
            api.intakeAnalysis(requestId).then(function (data) {
                setContent(refs, buildIntakeContent(data), data.aiAvailable);
            }).catch(function (err) {
                setError(refs, err.message || "Failed to load intake analysis.", generate);
            });
        }

        refs.btn.addEventListener("click", generate);
        container.appendChild(refs.card);
    }

    function renderPolicyCard(container, requestId) {
        var refs = createAiCard("policy", "Policy Explanation");

        function generate() {
            setLoading(refs);
            api.policyExplanation(requestId).then(function (data) {
                setContent(refs, buildPolicyContent(data), data.aiAvailable);
            }).catch(function (err) {
                setError(refs, err.message || "Failed to load policy explanation.", generate);
            });
        }

        refs.btn.addEventListener("click", generate);
        container.appendChild(refs.card);
    }

    function renderCatalogCard(container, requestId) {
        var refs = createAiCard("catalog", "Catalog Match Explanation");

        function generate() {
            setLoading(refs);
            api.catalogExplanation({ requestId: requestId }).then(function (data) {
                setContent(refs, buildCatalogContent(data), data.aiAvailable);
            }).catch(function (err) {
                setError(refs, err.message || "Failed to load catalog explanation.", generate);
            });
        }

        refs.btn.addEventListener("click", generate);
        container.appendChild(refs.card);
    }

    function renderApprovalCard(container, requestId) {
        var refs = createAiCard("approval", "Approval Summary");

        function generate() {
            setLoading(refs);
            api.approvalNotification(requestId, {}).then(function (data) {
                setContent(refs, buildApprovalContent(data), data.aiAvailable);
            }).catch(function (err) {
                setError(refs, err.message || "Failed to load approval summary.", generate);
            });
        }

        refs.btn.addEventListener("click", generate);
        container.appendChild(refs.card);
    }

    /* ==================================================================
       Orchestrator: render cards by request status
       ================================================================== */

    var STATUS_CARDS = {
        clarification:    ["intake"],
        policy_review:    ["intake", "policy", "catalog"],
        pending_approval: ["policy", "catalog", "approval"],
        approved:         ["policy"],
        rejected:         ["policy"],
    };

    var CARD_RENDERERS = {
        intake:   renderIntakeCard,
        policy:   renderPolicyCard,
        catalog:  renderCatalogCard,
        approval: renderApprovalCard,
    };

    function renderAiCards(container, req) {
        if (!container) return;

        // Clear previous AI cards
        var existing = container.querySelectorAll("[data-ai-card]");
        for (var i = 0; i < existing.length; i++) {
            existing[i].remove();
        }

        var cards = STATUS_CARDS[req.status];
        if (!cards) return;

        for (var j = 0; j < cards.length; j++) {
            var renderer = CARD_RENDERERS[cards[j]];
            if (renderer) {
                renderer(container, req.id);
            }
        }
    }

    /* ==================================================================
       Intake panel for request_form page
       ================================================================== */

    /**
     * Create the AI Intake Review panel in the form aside.
     * Returns a controller with methods for requestForm.js to call.
     *
     * @param {HTMLElement} container - The #intake-ai-panel element
     * @param {function} getFormData - Callback that returns current form data
     * @returns {{ analyzePreview: function, showRunIntakeResult: function }}
     */
    function renderIntakePanel(container, getFormData) {
        if (!container) return null;

        // Build card structure
        var card = el("div", "card ai-card ai-intake-panel");

        var header = el("div", "card-header");
        var titleEl = el("span", "ai-card-title", "AI Intake Review");
        var badgeSlot = el("span", "ai-badge-slot");
        var analyzeBtn = el("button", "btn btn-secondary btn-sm ai-generate-btn", "Analyze Draft");

        header.appendChild(titleEl);
        header.appendChild(badgeSlot);
        header.appendChild(analyzeBtn);

        var body = el("div", "card-body");
        var hint = el("p", "ai-empty-text",
            "Fill in your request details, then click Analyze Draft to preview AI intake feedback.");
        hint.style.fontSize = "var(--text-sm)";
        hint.style.color = "var(--color-text-muted)";
        body.appendChild(hint);

        card.appendChild(header);
        card.appendChild(body);
        container.appendChild(card);

        // State
        var refs = { card: card, body: body, badge: badgeSlot, btn: analyzeBtn, generated: false };

        function doAnalyze() {
            if (!getFormData) return;
            var formData = getFormData();

            setLoading(refs);
            api.intakePreview(formData).then(function (data) {
                setContent(refs, buildIntakeContent(data), data.aiAvailable);
            }).catch(function (err) {
                setError(refs, err.message || "Failed to analyze draft.", doAnalyze);
            });
        }

        analyzeBtn.addEventListener("click", doAnalyze);

        return {
            /**
             * Show the result from runIntake (post-submission).
             */
            showRunIntakeResult: function (analysis, requestId) {
                setContent(refs, buildIntakeContent(analysis), analysis.aiAvailable);

                // Add "View Request" link
                var link = el("a", "btn btn-primary btn-sm mt-3",
                    "View Request Details \u2192");
                link.href = "/static/pages/request_detail.html?id=" + requestId;
                link.style.display = "inline-block";
                refs.body.appendChild(link);

                // Disable analyze button after submission
                refs.btn.style.display = "none";
            },

            /**
             * Reset the panel to initial state.
             */
            reset: function () {
                refs.body.innerHTML = "";
                var hint = el("p", "ai-empty-text",
                    "Fill in your request details, then click Analyze Draft to preview AI intake feedback.");
                hint.style.fontSize = "var(--text-sm)";
                hint.style.color = "var(--color-text-muted)";
                refs.body.appendChild(hint);
                refs.badge.innerHTML = "";
                refs.btn.textContent = "Analyze Draft";
                refs.btn.style.display = "";
                refs.generated = false;
                PF.setLoading(refs.btn, false);
            },
        };
    }

    /* ==================================================================
       Public API
       ================================================================== */

    window.PF.aiCards = {
        renderAiCards: renderAiCards,
        renderIntakePanel: renderIntakePanel,
    };
})();
