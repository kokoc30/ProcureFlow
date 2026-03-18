/**
 * ProcureFlow - Request detail page logic.
 *
 * Loads a single request with clarifications, approval tasks, and audit events,
 * renders each section, handles inline clarification responses, and provides
 * contextual workflow actions.
 *
 * Load order: ui.js -> caseUtils.js -> api.js -> requestDetail.js
 */

(function () {
    "use strict";

    var $ = window.PF.$;
    var api = window.PF.api;

    var ACTION_LABELS = {
        request_created: "Request Submitted",
        clarification_requested: "Clarification Opened",
        clarification_answered: "Clarification Resolved",
        catalog_matched: "Catalog Matched",
        catalog_review_required: "Catalog Review Needed",
        policy_evaluated: "Policy Result Recorded",
        approval_assigned: "Approval Routed",
        approval_decided: "Decision Recorded",
        po_generated: "PO Draft Generated",
        po_generation_blocked: "PO Draft Blocked"
    };

    var TIMELINE_BADGES = {
        request_created: { css: "badge-draft", label: "Submitted", tone: "submitted" },
        clarification_requested: { css: "badge-clarification", label: "Clarification", tone: "clarification" },
        clarification_answered: { css: "badge-approved", label: "Answered", tone: "success" },
        catalog_matched: { css: "badge-review", label: "Catalog", tone: "policy" },
        catalog_review_required: { css: "badge-pending", label: "Catalog Review", tone: "approval" },
        policy_evaluated: { css: "badge-review", label: "Policy", tone: "policy" },
        approval_assigned: { css: "badge-pending", label: "Approval", tone: "approval" },
        po_generated: { css: "badge-approved", label: "PO Draft", tone: "success" },
        po_generation_blocked: { css: "badge-rejected", label: "Blocked", tone: "blocked" }
    };

    var requestId = null;
    var detailFeedback = null;
    var usersCache = {};

    document.addEventListener("DOMContentLoaded", function () {
        var params = new URLSearchParams(window.location.search);
        requestId = params.get("id");
        detailFeedback = $("#detail-feedback");

        if (!requestId) {
            showError("No request ID provided.");
            return;
        }

        loadUsers().then(function () {
            loadRequest();
        });
    });

    function loadUsers() {
        return api.getMockUsers().then(function (users) {
            if (Array.isArray(users)) {
                for (var i = 0; i < users.length; i++) {
                    usersCache[users[i].id] = users[i];
                }
            }
        }).catch(function () {
            // Non-critical - the page still renders without cached user names.
        });
    }

    function userName(id) {
        var user = usersCache[id];
        return user ? user.name : id || "System";
    }

    function loadRequest() {
        api.getRequest(requestId).then(function (data) {
            $("#loading-state").style.display = "none";
            $("#detail-content").style.display = "";
            renderAll(data);
        }).catch(function (err) {
            var msg = "Request record not found.";
            if (err && err.data && err.data.detail) {
                msg = err.data.detail;
            }
            showError(msg);
        });
    }

    function refresh() {
        return api.getRequest(requestId).then(function (data) {
            renderAll(data);
            return data;
        }).catch(function () {
            // Ignore refresh failures and leave the current request view intact.
            return null;
        });
    }

    function showError(msg) {
        $("#loading-state").style.display = "none";
        $("#detail-content").style.display = "none";
        $("#error-page").style.display = "";
        $("#error-message").textContent = msg;
        PF.clearFeedback(detailFeedback);
        PF.toast(msg, "error");
    }

    function renderAll(req) {
        renderHeader(req);
        renderInfo(req);
        renderItems(req);
        renderClarifications(req.clarifications || [], req);
        renderApprovalTasks(req.approvalTasks || []);
        renderStatusPanel(req);
        renderActions(req);
        renderPolicyPanel(req);
        renderPoPanel(req);
        renderTimeline(req.auditEvents || []);

        if (PF.aiCards) {
            PF.aiCards.renderAiCards(document.getElementById("ai-cards-container"), req);
        }
    }

    function renderHeader(req) {
        var summary = getSummary(req);
        var clarCounts = getClarificationCounts(req.clarifications || []);
        var poReady = !!req.purchaseOrder;

        $("#detail-title").textContent = req.title || "Untitled Request";
        $("#detail-id").textContent = "Request ID: " + req.id;
        $("#detail-subtitle").textContent = summary.nextAction || fallbackStatusSummary(req);

        var badgeContainer = $("#detail-badge");
        badgeContainer.innerHTML = "";
        badgeContainer.appendChild(PF.statusBadge(req.status));

        var metaContainer = $("#detail-overview-meta");
        metaContainer.innerHTML = "";

        var metaItems = [
            { label: "Request Owner", value: userName(req.requesterId) },
            { label: "Department", value: req.department || "\u2014" },
            { label: "Cost Center", value: req.costCenter || "\u2014" },
            { label: "Target Delivery", value: PF.formatDate(req.deliveryDate) },
            { label: "Submitted", value: PF.formatDateTime(req.createdAt) }
        ];

        if (req.urgency && req.urgency !== "standard") {
            metaItems.splice(3, 0, {
                label: "Priority",
                value: capitalize(req.urgency)
            });
        }

        for (var i = 0; i < metaItems.length; i++) {
            metaContainer.appendChild(buildOverviewChip(metaItems[i].label, metaItems[i].value));
        }

        var summaryStrip = $("#detail-summary-strip");
        summaryStrip.innerHTML = "";

        var metrics = [
            {
                label: "Line Items",
                value: PF.formatNumber(getItemCount(req)),
                note: req.items && req.items.length > 0
                    ? "Normalized for sourcing and policy review"
                    : "Captured directly from intake"
            },
            {
                label: "Current Value",
                value: req.totalCents > 0 ? PF.formatCurrency(req.totalCents) : "Pending",
                note: req.totalCents > 0
                    ? "Based on the current request total"
                    : "Pricing appears after structured matching"
            },
            {
                label: "Clarifications",
                value: clarCounts.open > 0
                    ? pluralize(clarCounts.open, "Open Question")
                    : "None Open",
                note: clarCounts.answered > 0
                    ? pluralize(clarCounts.answered, "Resolved Question")
                    : "No responses recorded yet"
            },
            {
                label: "PO Readiness",
                value: poReady
                    ? (req.purchaseOrder.poNumber || "Draft Ready")
                    : (req.status === "approved" ? "Ready to Generate" : "In Workflow"),
                note: poReady
                    ? (req.purchaseOrder.reviewRequired ? "Procurement review still required" : "Draft is ready for handoff")
                    : poPlaceholderMessage(req)
            }
        ];

        for (var j = 0; j < metrics.length; j++) {
            summaryStrip.appendChild(buildHeaderStat(metrics[j]));
        }
    }

    function renderInfo(req) {
        var container = $("#info-fields");
        container.innerHTML = "";

        var metaGrid = document.createElement("div");
        metaGrid.className = "summary-meta-grid";

        var summaryFields = [
            { label: "Request Owner", value: userName(req.requesterId), empty: false },
            { label: "Owning Department", value: req.department || "\u2014", empty: !req.department },
            { label: "Cost Center", value: req.costCenter || "\u2014", empty: !req.costCenter },
            { label: "Target Delivery", value: PF.formatDate(req.deliveryDate), empty: !req.deliveryDate }
        ];

        for (var i = 0; i < summaryFields.length; i++) {
            metaGrid.appendChild(buildSummaryField(summaryFields[i].label, summaryFields[i].value, summaryFields[i].empty));
        }

        container.appendChild(metaGrid);

        var narrativeGrid = document.createElement("div");
        narrativeGrid.className = "summary-narrative-grid";

        narrativeGrid.appendChild(buildNarrativeCard(
            "Operational Justification",
            req.justification || "No justification has been captured yet.",
            !req.justification
        ));
        narrativeGrid.appendChild(buildNarrativeCard(
            "Operational Context",
            req.description || "No additional operating context has been captured yet.",
            !req.description
        ));

        container.appendChild(narrativeGrid);
    }

    function capitalize(str) {
        if (!str) return "";
        return str.charAt(0).toUpperCase() + str.slice(1).replace(/_/g, " ");
    }

    function renderItems(req) {
        var container = $("#items-content");
        container.innerHTML = "";

        var items = req.items && req.items.length > 0 ? req.items : null;
        var raw = req.requestedItems || [];
        var suppliers = getSupplierCount(items || []);

        if (items) {
            container.appendChild(buildItemsSummary(
                "Structured line items are ready for sourcing, policy review, and downstream PO preparation.",
                [
                    makeBadge("badge-review", "Normalized"),
                    makeBadge("badge-draft", pluralize(items.length, "Line Item")),
                    suppliers > 0 ? makeBadge("badge-draft", pluralize(suppliers, "Supplier")) : null
                ]
            ));

            var wrap = document.createElement("div");
            wrap.className = "table-wrap";

            var table = document.createElement("table");
            table.className = "data-table";

            var thead = document.createElement("thead");
            thead.innerHTML =
                "<tr><th>Material / Part / Service</th><th>Qty / Lot</th><th>Unit Value</th><th>Supplier</th></tr>";
            table.appendChild(thead);

            var tbody = document.createElement("tbody");
            for (var j = 0; j < items.length; j++) {
                var item = items[j];
                var tr = document.createElement("tr");
                tr.innerHTML =
                    "<td><div class=\"items-description-cell\">" +
                    "<span class=\"items-description-main\">" + esc(item.description) + "</span>" +
                    (item.catalogId
                        ? "<span class=\"items-description-meta\">Catalog match: " + esc(item.catalogId) + "</span>"
                        : "") +
                    "</div></td>" +
                    "<td>" + esc(String(item.quantity)) + "</td>" +
                    "<td>" + PF.formatCurrency(item.unitPriceCents) + "</td>" +
                    "<td>" + esc(item.vendor || "\u2014") + "</td>";
                tbody.appendChild(tr);
            }

            table.appendChild(tbody);
            wrap.appendChild(table);
            container.appendChild(wrap);

            if (req.totalCents > 0) {
                var totalRow = document.createElement("div");
                totalRow.className = "items-total";
                totalRow.innerHTML = "<strong>Total Value:</strong> " + PF.formatCurrency(req.totalCents);
                container.appendChild(totalRow);
            }
        } else if (raw.length > 0) {
            container.appendChild(buildItemsSummary(
                "Submitted intake lines are shown as-entered until catalog matching creates structured line items.",
                [
                    makeBadge("badge-clarification", "Awaiting Normalization"),
                    makeBadge("badge-draft", pluralize(raw.length, "Submitted Line"))
                ]
            ));

            var stack = document.createElement("div");
            stack.className = "request-item-stack";

            for (var k = 0; k < raw.length; k++) {
                var card = document.createElement("div");
                card.className = "request-item-card";

                var index = document.createElement("div");
                index.className = "request-item-index";
                index.textContent = k + 1;

                var body = document.createElement("div");

                var label = document.createElement("div");
                label.className = "request-item-label";
                label.textContent = "Submitted intake line";

                var text = document.createElement("p");
                text.className = "request-item-text";
                text.textContent = raw[k];

                body.appendChild(label);
                body.appendChild(text);
                card.appendChild(index);
                card.appendChild(body);
                stack.appendChild(card);
            }

            container.appendChild(stack);
        } else {
            container.appendChild(PF.buildStatePanel({
                compact: true,
                tone: "info",
                title: "No requested items yet",
                text: "Materials, parts, or services will appear here once the intake is normalized or updated."
            }));
        }
    }

    function renderClarifications(clars, req) {
        var container = $("#clarifications-content");
        container.innerHTML = "";

        if (!clars || clars.length === 0) {
            container.appendChild(PF.buildStatePanel({
                compact: true,
                tone: "success",
                title: "No clarification requests are open",
                text: "The request has everything it needs to continue through the workflow right now."
            }));
            return;
        }

        var counts = getClarificationCounts(clars);
        var summary = document.createElement("div");
        summary.className = "clarification-summary";

        var summaryCopy = document.createElement("p");
        summaryCopy.className = "clarification-summary-text";
        if (counts.open > 0 && req.status === "clarification") {
            summaryCopy.textContent = "Outstanding clarification responses are blocking the request from moving back into policy review.";
        } else if (counts.open > 0) {
            summaryCopy.textContent = "Clarification history is preserved here, including any items that still need a response.";
        } else {
            summaryCopy.textContent = "All clarification questions have been answered and remain recorded for audit review.";
        }

        var summaryBadges = document.createElement("div");
        summaryBadges.className = "badge-group";
        summaryBadges.appendChild(makeBadge("badge-clarification", pluralize(counts.open, "Open Question")));
        summaryBadges.appendChild(makeBadge("badge-approved", pluralize(counts.answered, "Resolved Question")));

        summary.appendChild(summaryCopy);
        summary.appendChild(summaryBadges);
        container.appendChild(summary);

        for (var i = 0; i < clars.length; i++) {
            var clarification = clars[i];
            var answered = clarification.status === "answered";

            var card = document.createElement("div");
            card.className = "clarification-card " +
                (answered ? "clarification-card--resolved" : "clarification-card--open");

            var statusRow = document.createElement("div");
            statusRow.className = "clarification-status-row";

            var statusMeta = document.createElement("div");
            statusMeta.className = "clarification-status-meta";
            statusMeta.appendChild(makeBadge(
                answered ? "badge-approved" : "badge-clarification",
                answered ? "Resolved" : "Open"
            ));

            if (clarification.field) {
                var fieldTag = document.createElement("span");
                fieldTag.className = "clarification-field-tag";
                fieldTag.textContent = capitalize(clarification.field);
                statusMeta.appendChild(fieldTag);
            }

            statusRow.appendChild(statusMeta);

            var stamp = document.createElement("div");
            stamp.className = "clarification-meta";
            stamp.textContent = (answered ? "Answered " : "Requested ") +
                PF.formatDateTime(answered ? clarification.updatedAt : clarification.createdAt);
            statusRow.appendChild(stamp);

            card.appendChild(statusRow);

            var question = document.createElement("p");
            question.className = "clarification-question";
            question.textContent = clarification.question;
            card.appendChild(question);

            if (answered) {
                var answerWrap = document.createElement("div");
                answerWrap.className = "clarification-answer";

                var answerLabel = document.createElement("div");
                answerLabel.className = "clarification-answer-label";
                answerLabel.textContent = "Recorded response";

                var answerText = document.createElement("p");
                answerText.className = "clarification-answer-text";
                answerText.textContent = clarification.answer;

                var answeredMeta = document.createElement("div");
                answeredMeta.className = "clarification-meta";
                answeredMeta.textContent = "Captured " + PF.formatDateTime(clarification.updatedAt);

                answerWrap.appendChild(answerLabel);
                answerWrap.appendChild(answerText);
                answerWrap.appendChild(answeredMeta);
                card.appendChild(answerWrap);
            } else if (req.status === "clarification") {
                card.appendChild(buildAnswerForm(clarification, req));
            } else {
                var pendingNote = document.createElement("p");
                pendingNote.className = "clarification-pending-note";
                pendingNote.textContent = "This clarification is still open and waiting for a requester response.";
                card.appendChild(pendingNote);
            }

            container.appendChild(card);
        }
    }

    function buildAnswerForm(clarification, req) {
        var form = document.createElement("div");
        form.className = "clarification-answer-form";

        var label = document.createElement("label");
        label.className = "clarification-form-label";
        label.setAttribute("for", "clarification-response-" + clarification.id);
        label.textContent = "Response";

        var hint = document.createElement("p");
        hint.className = "clarification-form-hint";
        hint.textContent = "Add the missing operating or procurement context. The response stays attached to the request history.";

        var feedbackEl = document.createElement("div");
        feedbackEl.className = "state-banner-region";

        var textarea = document.createElement("textarea");
        textarea.id = "clarification-response-" + clarification.id;
        textarea.className = "form-textarea";
        textarea.placeholder = "Provide the missing operating or procurement detail...";
        textarea.rows = 3;

        var errorEl = document.createElement("div");
        errorEl.className = "form-error";
        errorEl.style.display = "none";

        var btn = document.createElement("button");
        btn.type = "button";
        btn.className = "btn btn-primary btn-sm";
        btn.textContent = "Submit Response";

        btn.addEventListener("click", function () {
            var answer = textarea.value.trim();
            if (!answer) {
                errorEl.textContent = "Response cannot be empty.";
                errorEl.style.display = "";
                textarea.classList.add("is-invalid");
                return;
            }

            errorEl.style.display = "none";
            textarea.classList.remove("is-invalid");
            PF.clearFeedback(feedbackEl);

            PF.setLoading(btn, true);
            textarea.disabled = true;

            api.answerClarification(clarification.id, {
                answer: answer,
                userId: req.requesterId
            }).then(function () {
                PF.toast("Clarification response submitted", "success");
                return refresh();
            }).then(function (fresh) {
                if (fresh) {
                    PF.setFeedback(detailFeedback, {
                        tone: "success",
                        title: "Clarification response submitted",
                        message: "The response was saved and the request detail has been refreshed."
                    });
                } else {
                    PF.setFeedback(detailFeedback, {
                        tone: "warning",
                        title: "Response saved",
                        message: "The clarification response was recorded, but the latest request detail could not be refreshed."
                    });
                    PF.setLoading(btn, false);
                    btn.textContent = "Response Submitted";
                    btn.disabled = true;
                    textarea.disabled = true;
                }
            }).catch(function (err) {
                var msg = "Failed to submit clarification response.";
                if (err && err.data && err.data.detail) {
                    msg = err.data.detail;
                }

                PF.toast(msg, "error");
                PF.setFeedback(feedbackEl, {
                    tone: "error",
                    title: "Response could not be submitted",
                    message: msg
                });
                PF.setLoading(btn, false);
                textarea.disabled = false;

                if (err && err.status === 409) {
                    refresh().then(function (fresh) {
                        if (fresh) {
                            PF.setFeedback(detailFeedback, {
                                tone: "info",
                                title: "Clarification already updated",
                                message: "The request detail was refreshed with the latest clarification status."
                            });
                        }
                    });
                }
            });
        });

        var footer = document.createElement("div");
        footer.className = "clarification-form-footer";

        var note = document.createElement("span");
        note.className = "clarification-form-note";
        note.textContent = "Submitting updates the audit trail and refreshes the request state.";

        footer.appendChild(note);
        footer.appendChild(btn);

        form.appendChild(label);
        form.appendChild(hint);
        form.appendChild(feedbackEl);
        form.appendChild(textarea);
        form.appendChild(errorEl);
        form.appendChild(footer);
        return form;
    }

    function renderApprovalTasks(tasks) {
        var card = $("#approvals-card");
        var container = $("#approvals-content");

        if (!tasks || tasks.length === 0) {
            card.style.display = "none";
            return;
        }

        card.style.display = "";
        container.innerHTML = "";

        for (var i = 0; i < tasks.length; i++) {
            var task = tasks[i];
            var row = document.createElement("div");
            row.className = "approval-task-row";

            var roleBadge = document.createElement("span");
            roleBadge.className = "badge badge-review";
            roleBadge.textContent = PF.ROLE_LABELS[task.role] || task.role;
            row.appendChild(roleBadge);

            var approver = document.createElement("span");
            approver.className = "approval-task-approver";
            approver.textContent = userName(task.approverId);
            row.appendChild(approver);

            var decisionBadge = document.createElement("span");
            if (task.decision === "approved") {
                decisionBadge.className = "badge badge-approved";
                decisionBadge.textContent = "Approved";
            } else if (task.decision === "rejected") {
                decisionBadge.className = "badge badge-rejected";
                decisionBadge.textContent = "Rejected";
            } else {
                decisionBadge.className = "badge badge-pending";
                decisionBadge.textContent = "Queued";
            }
            row.appendChild(decisionBadge);

            if (task.comment) {
                var comment = document.createElement("div");
                comment.className = "approval-task-comment";
                comment.textContent = task.comment;
                row.appendChild(comment);
            }

            container.appendChild(row);
        }
    }

    function renderActions(req) {
        var card = $("#actions-card");
        var container = $("#actions-panel");
        container.innerHTML = "";

        var actions = [];
        var hasItems = req.items && req.items.length > 0;
        var hasPolicyResult = !!req.policyResult;
        var hasApprovalTasks = req.approvalTasks && req.approvalTasks.length > 0;
        var hasPo = !!req.purchaseOrder;

        if (req.status === "policy_review" && !hasItems) {
            actions.push({
                label: "Match Catalog",
                description: "Normalize submitted materials and parts against catalog entries.",
                handler: function (btn, feedback) { actionMatchCatalog(btn, feedback); }
            });
        }

        if (req.status === "policy_review" && hasItems && !hasPolicyResult) {
            actions.push({
                label: "Evaluate Policy",
                description: "Record the policy result and required approval path.",
                handler: function (btn, feedback) { actionEvaluatePolicy(btn, feedback); }
            });
        }

        if (req.status === "pending_approval" && !hasApprovalTasks) {
            actions.push({
                label: "Open Approval Queue",
                description: "Create approval tasks for the required review roles.",
                handler: function (btn, feedback) { actionStartApproval(btn, feedback); }
            });
        }

        if (req.status === "approved" && !hasPo) {
            actions.push({
                label: "Generate PO Draft",
                description: "Prepare the request for fulfillment readiness.",
                handler: function (btn, feedback) { actionGeneratePo(btn, feedback); }
            });
        }

        if (actions.length === 0) {
            card.style.display = "none";
            return;
        }

        card.style.display = "";

        var feedback = document.createElement("div");
        feedback.className = "state-banner-region mb-3";
        container.appendChild(feedback);

        for (var j = 0; j < actions.length; j++) {
            var action = actions[j];
            var wrap = document.createElement("div");
            wrap.className = "action-item";

            var desc = document.createElement("p");
            desc.className = "action-description";
            desc.textContent = action.description;
            wrap.appendChild(desc);

            var btn = document.createElement("button");
            btn.type = "button";
            btn.className = "btn btn-primary action-btn";
            btn.textContent = action.label;
            btn.addEventListener("click", (function (handler) {
                return function () { handler(this, feedback); };
            })(action.handler));
            wrap.appendChild(btn);

            container.appendChild(wrap);
        }
    }

    function actionMatchCatalog(btn, feedback) {
        PF.setLoading(btn, true);
        PF.clearFeedback(feedback);
        api.matchCatalog({ requestId: requestId }).then(function () {
            PF.toast("Catalog match recorded", "success");
            return refresh();
        }).then(function (fresh) {
            showRefreshFeedback(
                fresh,
                "Catalog match recorded",
                "Submitted line items were normalized and the request detail has been refreshed.",
                btn
            );
        }).catch(function (err) {
            var message = errMsg(err, "Catalog match failed.");
            PF.toast(message, "error");
            PF.setFeedback(feedback, {
                tone: "error",
                title: "Catalog match failed",
                message: message
            });
            PF.setLoading(btn, false);
        });
    }

    function actionEvaluatePolicy(btn, feedback) {
        PF.setLoading(btn, true);
        PF.clearFeedback(feedback);
        api.evaluatePolicy(requestId).then(function () {
            PF.toast("Policy result recorded", "success");
            return refresh();
        }).then(function (fresh) {
            showRefreshFeedback(
                fresh,
                "Policy result recorded",
                "The policy outcome has been saved and the request detail has been refreshed.",
                btn
            );
        }).catch(function (err) {
            var message = errMsg(err, "Policy evaluation failed.");
            PF.toast(message, "error");
            PF.setFeedback(feedback, {
                tone: "error",
                title: "Policy evaluation failed",
                message: message
            });
            PF.setLoading(btn, false);
        });
    }

    function actionStartApproval(btn, feedback) {
        PF.setLoading(btn, true);
        PF.clearFeedback(feedback);
        api.startApproval(requestId).then(function () {
            PF.toast("Approval queue created", "success");
            return refresh();
        }).then(function (fresh) {
            showRefreshFeedback(
                fresh,
                "Approval queue created",
                "Review tasks were created and the request detail has been refreshed.",
                btn
            );
        }).catch(function (err) {
            var message = errMsg(err, "Failed to open approval queue.");
            PF.toast(message, "error");
            PF.setFeedback(feedback, {
                tone: "error",
                title: "Approval queue could not be opened",
                message: message
            });
            PF.setLoading(btn, false);
        });
    }

    function actionGeneratePo(btn, feedback) {
        PF.setLoading(btn, true);
        PF.clearFeedback(feedback);
        api.generatePo(requestId).then(function () {
            PF.toast("PO draft generated", "success");
            return refresh();
        }).then(function (fresh) {
            showRefreshFeedback(
                fresh,
                "PO draft generated",
                "The purchase order draft is available and the request detail has been refreshed.",
                btn
            );
        }).catch(function (err) {
            var message = errMsg(err, "Failed to generate PO draft.");
            PF.toast(message, "error");
            PF.setFeedback(feedback, {
                tone: "error",
                title: "PO draft could not be generated",
                message: message
            });
            PF.setLoading(btn, false);
        });
    }

    function errMsg(err, fallback) {
        if (err && err.data && err.data.detail) return err.data.detail;
        return fallback;
    }

    function showRefreshFeedback(fresh, title, message, btn) {
        if (!fresh && btn) {
            PF.setLoading(btn, false);
            btn.disabled = true;
        }

        PF.setFeedback(detailFeedback, {
            tone: fresh ? "success" : "warning",
            title: title,
            message: fresh
                ? message
                : "The action completed, but the latest request detail could not be refreshed."
        });
    }

    function renderPolicyPanel(req) {
        var card = $("#policy-card");
        var container = $("#policy-panel");

        if (!req.policyResult) {
            card.style.display = "none";
            return;
        }

        card.style.display = "";
        container.innerHTML = "";

        var policyResult = req.policyResult;

        var statusRow = document.createElement("div");
        statusRow.className = "field-row";
        statusRow.innerHTML =
            '<span class="field-label">Outcome</span>' +
            '<span class="field-value">' +
            (policyResult.passed
                ? '<span class="badge badge-approved">Cleared</span>'
                : '<span class="badge badge-rejected">Blocked</span>') +
            "</span>";
        container.appendChild(statusRow);

        if (policyResult.requiredApprovers && policyResult.requiredApprovers.length > 0) {
            var approverRow = document.createElement("div");
            approverRow.className = "field-row";

            var approverLabel = document.createElement("span");
            approverLabel.className = "field-label";
            approverLabel.textContent = "Approval Path";

            var approverValue = document.createElement("span");
            approverValue.className = "field-value policy-approvers";

            for (var k = 0; k < policyResult.requiredApprovers.length; k++) {
                var approverBadge = document.createElement("span");
                approverBadge.className = "badge badge-review";
                approverBadge.textContent = PF.ROLE_LABELS[policyResult.requiredApprovers[k]] || policyResult.requiredApprovers[k];
                approverValue.appendChild(approverBadge);
            }

            approverRow.appendChild(approverLabel);
            approverRow.appendChild(approverValue);
            container.appendChild(approverRow);
        } else if (policyResult.passed) {
            var autoRow = document.createElement("div");
            autoRow.className = "field-row";
            autoRow.innerHTML =
                '<span class="field-label">Approval Path</span>' +
                '<span class="field-value">Auto-approved (no manual approval required)</span>';
            container.appendChild(autoRow);
        }

        if (policyResult.flags && policyResult.flags.length > 0) {
            var flagsWrap = document.createElement("div");
            flagsWrap.className = "policy-flags";

            for (var m = 0; m < policyResult.flags.length; m++) {
                var flag = policyResult.flags[m];
                var flagEl = document.createElement("div");
                flagEl.className = "policy-flag " + (flag.passed ? "policy-flag-pass" : "policy-flag-fail");
                flagEl.innerHTML =
                    '<span class="policy-flag-icon">' + (flag.passed ? "&#10003;" : "&#10007;") + "</span>" +
                    "<span>" + esc(flag.message) + "</span>";
                flagsWrap.appendChild(flagEl);
            }

            container.appendChild(flagsWrap);
        }
    }

    function renderStatusPanel(req) {
        var container = $("#status-panel");
        container.innerHTML = "";

        var summary = getSummary(req);
        var clarCounts = getClarificationCounts(req.clarifications || []);
        var approvalCounts = getApprovalCounts(req.approvalTasks || []);

        var overview = document.createElement("div");
        overview.className = "status-overview";

        var badgeWrap = document.createElement("div");
        badgeWrap.className = "status-badge-wrap";
        badgeWrap.appendChild(PF.statusBadge(req.status));
        overview.appendChild(badgeWrap);

        var headline = document.createElement("p");
        headline.className = "status-headline";
        headline.textContent = summary.statusLabel || statusLabel(req.status);
        overview.appendChild(headline);

        var nextStep = document.createElement("p");
        nextStep.className = "status-summary";
        nextStep.textContent = summary.nextAction || fallbackStatusSummary(req);
        overview.appendChild(nextStep);

        container.appendChild(overview);

        var metricGrid = document.createElement("div");
        metricGrid.className = "status-metric-grid";
        metricGrid.appendChild(buildStatusMetric(
            "Open clarifications",
            PF.formatNumber(clarCounts.open),
            clarCounts.open > 0 ? "Responses still required" : "Queue is clear"
        ));
        metricGrid.appendChild(buildStatusMetric(
            "Pending approvals",
            approvalCounts.pending > 0 ? PF.formatNumber(approvalCounts.pending) : "\u2014",
            approvalCounts.total > 0 ? "Tasks still waiting on reviewers" : "Approval queue not opened"
        ));
        metricGrid.appendChild(buildStatusMetric(
            "PO readiness",
            req.purchaseOrder ? "Draft Ready" : (req.status === "approved" ? "Ready" : "Pending"),
            req.purchaseOrder
                ? (req.purchaseOrder.reviewRequired ? "Review required before release" : "Draft available for fulfillment")
                : poPlaceholderMessage(req)
        ));
        container.appendChild(metricGrid);

        var fields = [
            { label: "Submitted", value: PF.formatDateTime(req.createdAt), empty: !req.createdAt },
            { label: "Last Updated", value: PF.formatDateTime(req.updatedAt), empty: !req.updatedAt },
            { label: "Request Value", value: req.totalCents > 0 ? PF.formatCurrency(req.totalCents) : "Pending", empty: req.totalCents <= 0 }
        ];

        for (var i = 0; i < fields.length; i++) {
            container.appendChild(buildFieldRow(fields[i].label, fields[i].value, fields[i].empty));
        }
    }

    function renderPoPanel(req) {
        var container = $("#po-panel");
        container.innerHTML = "";

        if (req.purchaseOrder) {
            var po = req.purchaseOrder;

            var state = document.createElement("div");
            state.className = "po-state";
            state.appendChild(makeBadge(
                po.reviewRequired ? "badge-pending" : "badge-approved",
                po.reviewRequired ? "Review Required" : "Draft Ready"
            ));
            container.appendChild(state);

            var fields = [
                { label: "PO Number", value: po.poNumber, empty: !po.poNumber },
                { label: "Draft Total", value: PF.formatCurrency(po.totalCents), empty: false },
                { label: "Generated", value: PF.formatDateTime(po.createdAt), empty: !po.createdAt }
            ];

            for (var j = 0; j < fields.length; j++) {
                container.appendChild(buildFieldRow(fields[j].label, fields[j].value, fields[j].empty));
            }

            var suppliers = po.vendorSummary ? Object.keys(po.vendorSummary).length : 0;
            if (suppliers > 0) {
                container.appendChild(buildFieldRow("Suppliers", pluralize(suppliers, "Supplier"), false));
            }

            if (po.summary) {
                var summary = document.createElement("p");
                summary.className = "po-summary";
                summary.textContent = po.summary;
                container.appendChild(summary);
            }
        } else {
            var placeholder = document.createElement("div");
            placeholder.className = "po-placeholder";
            placeholder.appendChild(makeBadge(
                req.status === "approved" ? "badge-pending" : "badge-draft",
                req.status === "approved" ? "Ready to Generate" : "Pending Workflow"
            ));

            var placeholderText = document.createElement("p");
            placeholderText.className = "po-placeholder-text";
            placeholderText.textContent = poPlaceholderMessage(req);
            placeholder.appendChild(placeholderText);

            container.appendChild(placeholder);
        }
    }

    function renderTimeline(events) {
        var container = $("#timeline-content");
        container.innerHTML = "";

        if (!events || events.length === 0) {
            container.appendChild(PF.buildStatePanel({
                compact: true,
                tone: "info",
                title: "No audit activity yet",
                text: "New workflow activity will appear here as soon as the request moves through review, approval, or PO preparation."
            }));
            return;
        }

        var sorted = events.slice().sort(function (a, b) {
            return a.createdAt < b.createdAt ? 1 : -1;
        });

        var timeline = document.createElement("div");
        timeline.className = "timeline detail-timeline";

        var currentGroupKey = null;
        var currentGroupEvents = null;

        for (var k = 0; k < sorted.length; k++) {
            var eventItem = sorted[k];
            var groupKey = timelineGroupKey(eventItem.createdAt);

            if (groupKey !== currentGroupKey) {
                var group = document.createElement("div");
                group.className = "timeline-group";

                var groupLabel = document.createElement("div");
                groupLabel.className = "timeline-group-label";
                groupLabel.textContent = formatTimelineDate(eventItem.createdAt);

                currentGroupEvents = document.createElement("div");
                currentGroupEvents.className = "timeline-group-events";

                group.appendChild(groupLabel);
                group.appendChild(currentGroupEvents);
                timeline.appendChild(group);

                currentGroupKey = groupKey;
            }

            currentGroupEvents.appendChild(buildTimelineItem(eventItem));
        }

        container.appendChild(timeline);
    }

    function esc(str) {
        if (!str) return "";
        var div = document.createElement("div");
        div.textContent = str;
        return div.innerHTML;
    }

    function buildOverviewChip(label, value) {
        var chip = document.createElement("div");
        chip.className = "detail-overview-chip";

        var lbl = document.createElement("span");
        lbl.className = "detail-overview-chip-label";
        lbl.textContent = label;

        var val = document.createElement("span");
        val.className = "detail-overview-chip-value" + (value === "\u2014" ? " detail-empty-value" : "");
        val.textContent = value;

        chip.appendChild(lbl);
        chip.appendChild(val);
        return chip;
    }

    function buildHeaderStat(metric) {
        var stat = document.createElement("div");
        stat.className = "detail-summary-stat";

        var label = document.createElement("div");
        label.className = "detail-summary-stat-label";
        label.textContent = metric.label;

        var value = document.createElement("div");
        value.className = "detail-summary-stat-value";
        value.textContent = metric.value;

        var note = document.createElement("div");
        note.className = "detail-summary-stat-note";
        note.textContent = metric.note;

        stat.appendChild(label);
        stat.appendChild(value);
        stat.appendChild(note);
        return stat;
    }

    function buildSummaryField(label, value, empty) {
        var card = document.createElement("div");
        card.className = "summary-field-card";

        var lbl = document.createElement("span");
        lbl.className = "field-label";
        lbl.textContent = label;

        var val = document.createElement("span");
        val.className = "field-value" + (empty ? " detail-empty-value" : "");
        val.textContent = value;

        card.appendChild(lbl);
        card.appendChild(val);
        return card;
    }

    function buildNarrativeCard(label, text, empty) {
        var card = document.createElement("div");
        card.className = "summary-narrative-card";

        var lbl = document.createElement("span");
        lbl.className = "field-label";
        lbl.textContent = label;

        var body = document.createElement("p");
        body.className = "summary-narrative-text" + (empty ? " detail-empty-value" : "");
        body.textContent = text;

        card.appendChild(lbl);
        card.appendChild(body);
        return card;
    }

    function buildItemsSummary(copy, badges) {
        var summary = document.createElement("div");
        summary.className = "items-summary-bar";

        var text = document.createElement("p");
        text.className = "items-summary-copy";
        text.textContent = copy;

        var badgeWrap = document.createElement("div");
        badgeWrap.className = "items-badge-group";

        for (var i = 0; i < badges.length; i++) {
            if (badges[i]) badgeWrap.appendChild(badges[i]);
        }

        summary.appendChild(text);
        summary.appendChild(badgeWrap);
        return summary;
    }

    function buildStatusMetric(label, value, note) {
        var metric = document.createElement("div");
        metric.className = "status-metric";

        var metricLabel = document.createElement("span");
        metricLabel.className = "status-metric-label";
        metricLabel.textContent = label;

        var metricValue = document.createElement("strong");
        metricValue.className = "status-metric-value";
        metricValue.textContent = value;

        var metricNote = document.createElement("span");
        metricNote.className = "status-metric-note";
        metricNote.textContent = note;

        metric.appendChild(metricLabel);
        metric.appendChild(metricValue);
        metric.appendChild(metricNote);
        return metric;
    }

    function buildFieldRow(label, value, empty) {
        var row = document.createElement("div");
        row.className = "field-row";

        var lbl = document.createElement("span");
        lbl.className = "field-label";
        lbl.textContent = label;

        var val = document.createElement("span");
        val.className = "field-value" + (empty ? " detail-empty-value" : "");
        val.textContent = value;

        row.appendChild(lbl);
        row.appendChild(val);
        return row;
    }

    function buildTimelineItem(eventItem) {
        var config = getTimelineBadge(eventItem);
        var item = document.createElement("div");
        item.className = "timeline-item timeline-item--" + config.tone;

        var marker = document.createElement("div");
        marker.className = "timeline-marker";

        var content = document.createElement("div");
        content.className = "timeline-content";

        var header = document.createElement("div");
        header.className = "timeline-item-header";

        var title = document.createElement("div");
        title.className = "timeline-title";
        title.textContent = ACTION_LABELS[eventItem.action] || eventItem.action;

        header.appendChild(title);
        header.appendChild(makeBadge(config.css, config.label));
        content.appendChild(header);

        var meta = document.createElement("div");
        meta.className = "timeline-meta";

        var timeChip = document.createElement("span");
        timeChip.className = "timeline-time-chip";
        timeChip.textContent = formatTimelineTime(eventItem.createdAt);

        var actor = document.createElement("span");
        actor.className = "timeline-actor";
        actor.textContent = userName(eventItem.actorId);

        meta.appendChild(timeChip);
        meta.appendChild(actor);
        content.appendChild(meta);

        if (eventItem.detail) {
            var detail = document.createElement("p");
            detail.className = "timeline-detail";
            detail.textContent = eventItem.detail;
            content.appendChild(detail);
        }

        item.appendChild(marker);
        item.appendChild(content);
        return item;
    }

    function makeBadge(cssClass, text) {
        var badge = document.createElement("span");
        badge.className = "badge " + cssClass;
        badge.textContent = text;
        return badge;
    }

    function getSummary(req) {
        return req && req.summary ? req.summary : {};
    }

    function getItemCount(req) {
        var summary = getSummary(req);
        if (typeof summary.itemCount === "number") return summary.itemCount;
        if (req.items && req.items.length > 0) return req.items.length;
        return (req.requestedItems || []).length;
    }

    function getClarificationCounts(clars) {
        var counts = { open: 0, answered: 0 };
        for (var i = 0; i < clars.length; i++) {
            if (clars[i].status === "answered") counts.answered += 1;
            else counts.open += 1;
        }
        return counts;
    }

    function getApprovalCounts(tasks) {
        var counts = { total: 0, pending: 0, decided: 0 };
        for (var i = 0; i < tasks.length; i++) {
            counts.total += 1;
            if (tasks[i].decision && tasks[i].decision !== "pending") counts.decided += 1;
            else counts.pending += 1;
        }
        return counts;
    }

    function getSupplierCount(items) {
        var seen = {};
        var total = 0;
        for (var i = 0; i < items.length; i++) {
            if (items[i].vendor && !seen[items[i].vendor]) {
                seen[items[i].vendor] = true;
                total += 1;
            }
        }
        return total;
    }

    function pluralize(count, singular) {
        return count + " " + singular + (count === 1 ? "" : "s");
    }

    function statusLabel(status) {
        var info = PF.STATUS_MAP[status];
        return info ? info.label : capitalize(status || "Unknown");
    }

    function fallbackStatusSummary(req) {
        var clarCounts = getClarificationCounts(req.clarifications || []);
        if (req.status === "clarification") {
            return clarCounts.open > 0
                ? pluralize(clarCounts.open, "clarification") + " still need a response before policy review can continue."
                : "Clarification responses are being reviewed.";
        }
        if (req.status === "policy_review") {
            return "The request is staged for policy evaluation and downstream routing.";
        }
        if (req.status === "pending_approval") {
            return "Approval tasks are open and the request is waiting on reviewer decisions.";
        }
        if (req.status === "approved") {
            return req.purchaseOrder
                ? "Approval is complete and the PO draft is available for fulfillment handoff."
                : "Approval is complete and the request is ready for PO generation.";
        }
        if (req.status === "rejected") {
            return "The request was rejected and remains available for audit review.";
        }
        return "Request details and workflow history are available below.";
    }

    function poPlaceholderMessage(req) {
        if (req.status === "approved") {
            return "The request is approved and can move into PO draft generation when you are ready.";
        }
        if (req.status === "rejected") {
            return "No purchase order is generated for rejected requests unless the workflow is reopened.";
        }
        return "A PO draft appears here after the request clears review and approval.";
    }

    function getTimelineBadge(eventItem) {
        if (eventItem.action === "approval_decided") {
            var detail = (eventItem.detail || "").toLowerCase();
            if (detail.indexOf("reject") !== -1) {
                return { css: "badge-rejected", label: "Rejected", tone: "blocked" };
            }
            return { css: "badge-approved", label: "Approved", tone: "success" };
        }

        return TIMELINE_BADGES[eventItem.action] || {
            css: "badge-draft",
            label: "Audit",
            tone: "submitted"
        };
    }

    function timelineGroupKey(isoString) {
        if (!isoString) return "unknown";
        var date = new Date(isoString);
        return [
            date.getFullYear(),
            date.getMonth() + 1,
            date.getDate()
        ].join("-");
    }

    function formatTimelineDate(isoString) {
        if (!isoString) return "\u2014";
        var date = new Date(isoString);
        return date.toLocaleDateString("en-US", {
            weekday: "short",
            month: "short",
            day: "numeric",
            year: "numeric"
        });
    }

    function formatTimelineTime(isoString) {
        if (!isoString) return "\u2014";
        var date = new Date(isoString);
        return date.toLocaleTimeString("en-US", {
            hour: "numeric",
            minute: "2-digit"
        });
    }
})();
