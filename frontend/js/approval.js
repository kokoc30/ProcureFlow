/**
 * ProcureFlow - Approval queue page logic.
 *
 * Loads approval tasks, groups them by pending versus decided,
 * and provides a review workspace for recording decisions.
 *
 * Load order: ui.js -> caseUtils.js -> api.js -> approval.js
 */

(function () {
    "use strict";

    var $ = window.PF.$;
    var api = window.PF.api;
    var setLoading = window.PF.setLoading;

    var feedbackEl = null;
    var refreshBtn = null;

    var ERROR_ICON =
        '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">' +
        '<circle cx="12" cy="12" r="10"></circle>' +
        '<line x1="12" y1="8" x2="12" y2="12"></line>' +
        '<line x1="12" y1="16" x2="12.01" y2="16"></line>' +
        "</svg>";

    var CLEAR_ICON =
        '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">' +
        '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>' +
        '<polyline points="22 4 12 14.01 9 11.01"></polyline>' +
        "</svg>";

    var usersCache = {};
    var requestsCache = {};
    var requestDetailsCache = {};
    var pendingTasks = [];
    var decidedTasks = [];
    var activeTaskId = null;
    var noteDrafts = {};

    document.addEventListener("DOMContentLoaded", function () {
        feedbackEl = $("#approval-feedback");
        refreshBtn = $("#refresh-btn");

        loadUsers()
            .then(loadRequestsCache)
            .then(loadTasks);

        if (refreshBtn) {
            refreshBtn.addEventListener("click", function () {
                loadRequestsCache().then(function () {
                    return loadTasks({
                        announceSuccess: true,
                        triggerButton: refreshBtn
                    });
                });
            });
        }
    });

    function loadUsers() {
        return api.getMockUsers().then(function (users) {
            if (Array.isArray(users)) {
                for (var i = 0; i < users.length; i++) {
                    usersCache[users[i].id] = users[i];
                }
            }
        }).catch(function () {
            // Non-critical - queue cards can still render fallback labels.
        });
    }

    function loadRequestsCache() {
        return api.listRequests({ pageSize: 100 }).then(function (res) {
            var data = res.data || [];
            requestsCache = {};
            for (var i = 0; i < data.length; i++) {
                requestsCache[data[i].id] = data[i];
            }
        }).catch(function () {
            // Non-critical - queue cards will render without cached request metadata.
        });
    }

    function userName(id) {
        var user = usersCache[id];
        return user ? user.name : id || "\u2014";
    }

    function roleLabel(role) {
        return PF.ROLE_LABELS[role] || role;
    }

    function loadTasks(options) {
        options = options || {};
        showState("loading");
        PF.clearFeedback(feedbackEl);

        if (options.triggerButton) {
            setLoading(options.triggerButton, true);
        }

        return api.listApprovalTasks().then(function (tasks) {
            if (!Array.isArray(tasks)) tasks = [];

            pendingTasks = [];
            decidedTasks = [];

            for (var i = 0; i < tasks.length; i++) {
                if (tasks[i].decision === "pending") pendingTasks.push(tasks[i]);
                else decidedTasks.push(tasks[i]);
            }

            pendingTasks.sort(function (a, b) {
                return (a.createdAt || "") > (b.createdAt || "") ? 1 : -1;
            });

            decidedTasks.sort(function (a, b) {
                return (a.decidedAt || a.createdAt || "") < (b.decidedAt || b.createdAt || "") ? 1 : -1;
            });

            activeTaskId = nextActiveTaskId(activeTaskId);

            renderOverview(pendingTasks, decidedTasks);
            renderPending(pendingTasks);
            renderDecided(decidedTasks);
            renderReviewPanel(getActiveTask());
            showState("content");

            if (options.announceSuccess) {
                PF.setFeedback(feedbackEl, {
                    tone: "success",
                    title: "Approval queue refreshed",
                    message: "Pending tasks and recorded decisions are up to date."
                });
                PF.toast("Approval queue refreshed", "success");
            }
            return true;
        }).catch(function (err) {
            var msg = "Failed to load the approval queue.";
            if (err && err.data && err.data.detail) {
                msg = err.data.detail;
            }
            renderErrorState(msg);
            showState("error");
            PF.toast(msg, "error");
            return false;
        }).finally(function () {
            if (options.triggerButton) {
                setLoading(options.triggerButton, false);
            }
        });
    }

    function nextActiveTaskId(currentId) {
        for (var i = 0; i < pendingTasks.length; i++) {
            if (pendingTasks[i].id === currentId) return currentId;
        }

        if (pendingTasks.length > 0) {
            return pendingTasks[0].id;
        }

        for (var j = 0; j < decidedTasks.length; j++) {
            if (decidedTasks[j].id === currentId) return currentId;
        }

        return decidedTasks.length > 0 ? decidedTasks[0].id : null;
    }

    function getAllTasks() {
        return pendingTasks.concat(decidedTasks);
    }

    function getActiveTask() {
        var tasks = getAllTasks();
        for (var i = 0; i < tasks.length; i++) {
            if (tasks[i].id === activeTaskId) return tasks[i];
        }
        return null;
    }

    function selectTask(taskId) {
        if (!taskId || taskId === activeTaskId) {
            var currentTask = getActiveTask();
            if (currentTask) ensureRequestDetail(currentTask.requestId);
            return;
        }

        activeTaskId = taskId;
        renderPending(pendingTasks);
        renderDecided(decidedTasks);
        renderReviewPanel(getActiveTask());
    }

    function renderOverview(pending, decided) {
        var container = $("#approval-overview");
        if (!container) return;

        container.innerHTML = "";

        var grid = document.createElement("div");
        grid.className = "approval-overview-grid";

        var openRequests = countDistinctRequestIds(pending);
        var activeApprovers = countDistinctApprovers(pending);
        var rejectedCount = countDecisions(decided, "rejected");

        var metrics = [
            {
                label: "Awaiting Decision",
                value: PF.formatNumber(pending.length),
                note: openRequests > 0 ? pluralize(openRequests, "Request") + " currently in queue" : "Queue is clear"
            },
            {
                label: "Active Approvers",
                value: activeApprovers > 0 ? PF.formatNumber(activeApprovers) : "\u2014",
                note: pending.length > 0 ? "Distinct reviewers assigned across open tasks" : "No reviewers currently blocked"
            },
            {
                label: "Completed Decisions",
                value: PF.formatNumber(decided.length),
                note: rejectedCount > 0 ? pluralize(rejectedCount, "Rejection") + " recorded in history" : "Decision history remains audit-ready"
            }
        ];

        for (var i = 0; i < metrics.length; i++) {
            grid.appendChild(buildOverviewMetric(metrics[i]));
        }

        container.appendChild(grid);
    }

    function renderPending(tasks) {
        var container = $("#pending-list");
        var emptyEl = $("#pending-empty");
        container.innerHTML = "";
        emptyEl.innerHTML = "";

        if (tasks.length === 0) {
            emptyEl.appendChild(PF.buildStatePanel({
                tone: "success",
                iconHtml: CLEAR_ICON,
                title: "Approval queue is clear",
                text: "Requests that need a manual decision will appear here as soon as they are routed for review.",
                action: {
                    label: "View Dashboard",
                    href: "/static/pages/dashboard.html"
                }
            }));
            emptyEl.style.display = "";
            return;
        }

        emptyEl.style.display = "none";

        for (var i = 0; i < tasks.length; i++) {
            container.appendChild(buildTaskCard(tasks[i], true));
        }
    }

    function renderDecided(tasks) {
        var section = $("#decided-section");
        var container = $("#decided-list");
        container.innerHTML = "";

        if (tasks.length === 0) {
            section.style.display = "none";
            return;
        }

        section.style.display = "";

        for (var i = 0; i < tasks.length; i++) {
            container.appendChild(buildTaskCard(tasks[i], false));
        }
    }

    function buildTaskCard(task, isPending) {
        var req = requestsCache[task.requestId] || {};
        var detailEntry = requestDetailsCache[task.requestId];
        var detail = detailEntry && detailEntry.status === "ready" ? detailEntry.data : null;
        var selected = task.id === activeTaskId;

        var card = document.createElement("article");
        card.className = "card approval-card " +
            (isPending ? "approval-card--pending" : "approval-card--decided") +
            (selected ? " approval-card--selected" : "");
        card.tabIndex = 0;
        card.setAttribute("role", "button");
        card.setAttribute("aria-pressed", selected ? "true" : "false");

        card.addEventListener("click", function (evt) {
            if (evt.target && evt.target.closest && evt.target.closest("a")) return;
            selectTask(task.id);
        });

        card.addEventListener("keydown", function (evt) {
            if (evt.key === "Enter" || evt.key === " ") {
                evt.preventDefault();
                selectTask(task.id);
            }
        });

        var header = document.createElement("div");
        header.className = "card-header approval-card-header";

        var heading = document.createElement("div");
        heading.className = "approval-card-heading";

        var title = document.createElement("a");
        title.href = "/static/pages/request_detail.html?id=" + task.requestId;
        title.textContent = req.title || "Request " + shortId(task.requestId);
        title.className = "approval-request-link";
        heading.appendChild(title);

        var subline = document.createElement("div");
        subline.className = "approval-request-subline";
        subline.textContent = "Request ID " + shortId(task.requestId) +
            (req.department ? " • " + req.department : "");
        heading.appendChild(subline);

        var badges = document.createElement("div");
        badges.className = "badge-group approval-card-badges";
        badges.appendChild(makeBadge("badge-review", roleLabel(task.role)));
        if (req.status) {
            badges.appendChild(PF.statusBadge(req.status));
        }
        if (!isPending) {
            badges.appendChild(makeBadge(
                task.decision === "approved" ? "badge-approved" : "badge-rejected",
                task.decision === "approved" ? "Approved" : "Rejected"
            ));
        }

        header.appendChild(heading);
        header.appendChild(badges);
        card.appendChild(header);

        var body = document.createElement("div");
        body.className = "card-body";

        var summary = document.createElement("p");
        summary.className = "approval-card-summary";
        summary.textContent = buildTaskSummary(task, req, detail);
        body.appendChild(summary);

        var metrics = document.createElement("div");
        metrics.className = "approval-summary";

        var fields = isPending
            ? [
                { label: "Assigned To", value: userName(task.approverId) },
                { label: "Request Owner", value: userName(req.requesterId) },
                { label: "Request Value", value: req.totalCents > 0 ? PF.formatCurrency(req.totalCents) : "Pending" },
                { label: "Queued", value: PF.formatDateTime(task.createdAt) }
            ]
            : [
                { label: "Reviewed By", value: userName(task.approverId) },
                { label: "Request Owner", value: userName(req.requesterId) },
                { label: "Request Value", value: req.totalCents > 0 ? PF.formatCurrency(req.totalCents) : "Pending" },
                { label: "Recorded", value: PF.formatDateTime(task.decidedAt || task.createdAt) }
            ];

        for (var i = 0; i < fields.length; i++) {
            metrics.appendChild(buildMetricBlock(fields[i].label, fields[i].value));
        }

        body.appendChild(metrics);

        if (task.comment) {
            var comment = document.createElement("p");
            comment.className = "approval-card-comment";
            comment.textContent = task.comment;
            body.appendChild(comment);
        }

        var footer = document.createElement("div");
        footer.className = "approval-card-footer";

        var selection = document.createElement("span");
        selection.className = selected
            ? "inline-alert inline-alert-info"
            : "approval-card-hint";
        selection.textContent = selected
            ? "Open in review detail"
            : (isPending ? "Select to review and decide" : "Select to inspect decision detail");

        footer.appendChild(selection);

        if (detailEntry && detailEntry.status === "loading") {
            var loading = document.createElement("span");
            loading.className = "approval-card-loading text-muted";
            loading.textContent = "Loading detail...";
            footer.appendChild(loading);
        }

        body.appendChild(footer);
        card.appendChild(body);
        return card;
    }

    function buildTaskSummary(task, req, detail) {
        var summary = detail && detail.summary ? detail.summary.nextAction : "";

        if (summary) {
            return summary;
        }

        if (task.decision === "pending") {
            return "Review the request context, capture an optional note, and record the " + roleLabel(task.role).toLowerCase() + " decision.";
        }

        if (task.decision === "approved") {
            return "Approval was recorded and the request remained in the operational workflow.";
        }

        return "Rejection was recorded and the request workflow was halted for follow-up.";
    }

    function renderReviewPanel(task) {
        var panel = $("#review-panel");
        if (!panel) return;

        panel.innerHTML = "";

        if (!task) {
            panel.innerHTML =
                '<div class="empty-state approval-review-empty">' +
                '<div class="empty-state-icon">✓</div>' +
                '<p class="empty-state-text">Select an approval item to review request details and record a decision.</p>' +
                "</div>";
            return;
        }

        var req = requestsCache[task.requestId] || {};
        var detailEntry = requestDetailsCache[task.requestId];
        var detail = detailEntry && detailEntry.status === "ready" ? detailEntry.data : null;

        if (!detailEntry) {
            ensureRequestDetail(task.requestId);
            detailEntry = requestDetailsCache[task.requestId];
        }

        var shell = document.createElement("div");
        shell.className = "approval-review-shell";

        var header = document.createElement("div");
        header.className = "approval-review-header";

        var kicker = document.createElement("p");
        kicker.className = "approval-review-kicker";
        kicker.textContent = task.decision === "pending" ? "Decision Workspace" : "Recorded Decision";
        header.appendChild(kicker);

        var title = document.createElement("a");
        title.href = "/static/pages/request_detail.html?id=" + task.requestId;
        title.className = "approval-review-title";
        title.textContent = req.title || (detail && detail.title) || "Request " + shortId(task.requestId);
        header.appendChild(title);

        var idLine = document.createElement("div");
        idLine.className = "approval-review-id";
        idLine.textContent = "Request ID: " + task.requestId;
        header.appendChild(idLine);

        var badgeRow = document.createElement("div");
        badgeRow.className = "badge-group approval-review-badges";
        badgeRow.appendChild(makeBadge("badge-review", roleLabel(task.role)));
        if (req.status) {
            badgeRow.appendChild(PF.statusBadge(req.status));
        }
        if (task.decision !== "pending") {
            badgeRow.appendChild(makeBadge(
                task.decision === "approved" ? "badge-approved" : "badge-rejected",
                task.decision === "approved" ? "Approved" : "Rejected"
            ));
        }
        header.appendChild(badgeRow);

        var nextAction = detail && detail.summary && detail.summary.nextAction
            ? detail.summary.nextAction
            : buildTaskSummary(task, req, detail);
        var summary = document.createElement("p");
        summary.className = "approval-review-summary";
        summary.textContent = nextAction;
        header.appendChild(summary);

        shell.appendChild(header);

        var meta = document.createElement("div");
        meta.className = "approval-review-meta";

        var metaFields = [
            { label: "Assigned To", value: userName(task.approverId) },
            { label: "Request Owner", value: userName((detail && detail.requesterId) || req.requesterId) },
            { label: "Department", value: (detail && detail.department) || req.department || "\u2014" },
            { label: "Request Value", value: requestValue(detail || req) },
            { label: "Submitted", value: PF.formatDateTime((detail && detail.createdAt) || req.createdAt) },
            { label: task.decision === "pending" ? "Queued" : "Recorded", value: PF.formatDateTime(task.decidedAt || task.createdAt) }
        ];

        for (var i = 0; i < metaFields.length; i++) {
            meta.appendChild(buildMetricBlock(metaFields[i].label, metaFields[i].value));
        }

        shell.appendChild(meta);

        if (detailEntry && detailEntry.status === "error") {
            shell.appendChild(buildInlineMessage(
                "inline-alert inline-alert-warning approval-review-alert",
                "Detailed request preview is temporarily unavailable. Decision controls still work."
            ));
        }

        if (detailEntry && detailEntry.status === "loading") {
            shell.appendChild(buildReviewLoadingBlock());
        } else {
            shell.appendChild(buildContextSection(detail || req));
            shell.appendChild(buildItemsSection(detail || req));
        }

        if (task.decision === "pending") {
            shell.appendChild(buildDecisionSection(task));
        } else {
            shell.appendChild(buildRecordedDecisionSection(task));
        }

        panel.appendChild(shell);
    }

    function buildContextSection(req) {
        var section = document.createElement("section");
        section.className = "approval-review-section";

        var title = document.createElement("h3");
        title.className = "approval-review-section-title";
        title.textContent = "Request Context";
        section.appendChild(title);

        var grid = document.createElement("div");
        grid.className = "approval-context-grid";
        grid.appendChild(buildContextCard(
            "Operational Justification",
            req.justification || "No justification was captured on the request."
        ));
        grid.appendChild(buildContextCard(
            "Operational Context",
            req.description || "No additional operating context was captured on the request."
        ));
        section.appendChild(grid);

        return section;
    }

    function buildItemsSection(req) {
        var section = document.createElement("section");
        section.className = "approval-review-section";

        var title = document.createElement("h3");
        title.className = "approval-review-section-title";
        title.textContent = "Requested Items";
        section.appendChild(title);

        var items = [];
        if (req.items && req.items.length > 0) {
            for (var i = 0; i < req.items.length; i++) {
                items.push(req.items[i].description);
            }
        } else {
            items = req.requestedItems || [];
        }

        if (!items.length) {
            var empty = document.createElement("p");
            empty.className = "approval-items-empty";
            empty.textContent = "No item detail is available for this request.";
            section.appendChild(empty);
            return section;
        }

        var list = document.createElement("div");
        list.className = "approval-item-stack";

        for (var j = 0; j < items.length && j < 5; j++) {
            var item = document.createElement("div");
            item.className = "approval-item";

            var marker = document.createElement("span");
            marker.className = "approval-item-index";
            marker.textContent = j + 1;

            var text = document.createElement("span");
            text.className = "approval-item-text";
            text.textContent = items[j];

            item.appendChild(marker);
            item.appendChild(text);
            list.appendChild(item);
        }

        section.appendChild(list);

        if (items.length > 5) {
            var overflow = document.createElement("p");
            overflow.className = "approval-items-overflow";
            overflow.textContent = "+" + (items.length - 5) + " additional item" + (items.length - 5 === 1 ? "" : "s") + " on the request detail page.";
            section.appendChild(overflow);
        }

        return section;
    }

    function buildDecisionSection(task) {
        var section = document.createElement("section");
        section.className = "approval-review-section approval-decision-section";

        var title = document.createElement("h3");
        title.className = "approval-review-section-title";
        title.textContent = "Record Decision";
        section.appendChild(title);

        var hint = document.createElement("p");
        hint.className = "approval-decision-hint";
        hint.textContent = "Decision notes are optional, but they help with downstream audit review and are especially useful when rejecting a request.";
        section.appendChild(hint);

        var feedback = document.createElement("div");
        feedback.className = "state-banner-region";
        section.appendChild(feedback);

        var textarea = document.createElement("textarea");
        textarea.className = "form-textarea approval-decision-textarea";
        textarea.placeholder = "Add an approval note or rejection reason (optional)";
        textarea.rows = 4;
        textarea.value = noteDrafts[task.id] || "";
        textarea.addEventListener("input", function () {
            noteDrafts[task.id] = textarea.value;
        });
        section.appendChild(textarea);

        var footer = document.createElement("div");
        footer.className = "approval-decision-footer";

        var note = document.createElement("span");
        note.className = "approval-decision-note";
        note.textContent = "Buttons stay disabled while the decision is being submitted.";
        footer.appendChild(note);

        var actions = document.createElement("div");
        actions.className = "approval-actions";

        var rejectBtn = document.createElement("button");
        rejectBtn.type = "button";
        rejectBtn.className = "btn btn-danger btn-sm";
        rejectBtn.textContent = "Reject";

        var approveBtn = document.createElement("button");
        approveBtn.type = "button";
        approveBtn.className = "btn btn-primary btn-sm";
        approveBtn.textContent = "Approve";

        rejectBtn.addEventListener("click", function () {
            handleDecision(task, "rejected", textarea, rejectBtn, approveBtn, feedback);
        });
        approveBtn.addEventListener("click", function () {
            handleDecision(task, "approved", textarea, approveBtn, rejectBtn, feedback);
        });

        actions.appendChild(rejectBtn);
        actions.appendChild(approveBtn);
        footer.appendChild(actions);

        section.appendChild(footer);
        return section;
    }

    function buildRecordedDecisionSection(task) {
        var section = document.createElement("section");
        section.className = "approval-review-section approval-recorded-section";

        var title = document.createElement("h3");
        title.className = "approval-review-section-title";
        title.textContent = "Decision Record";
        section.appendChild(title);

        var status = document.createElement("div");
        status.className = "approval-recorded-status";
        status.appendChild(makeBadge(
            task.decision === "approved" ? "badge-approved" : "badge-rejected",
            task.decision === "approved" ? "Approved" : "Rejected"
        ));
        section.appendChild(status);

        var text = document.createElement("p");
        text.className = "approval-recorded-text";
        text.textContent = "Recorded by " + userName(task.approverId) + " on " + PF.formatDateTime(task.decidedAt || task.createdAt) + ".";
        section.appendChild(text);

        if (task.comment) {
            var comment = document.createElement("div");
            comment.className = "approval-recorded-comment";
            comment.textContent = task.comment;
            section.appendChild(comment);
        }

        return section;
    }

    function handleDecision(task, decision, textarea, activeBtn, otherBtn, feedback) {
        var comment = textarea.value.trim();

        PF.setLoading(activeBtn, true);
        otherBtn.disabled = true;
        textarea.disabled = true;
        PF.clearFeedback(feedback);

        api.recordDecision(task.id, {
            approverId: task.approverId,
            decision: decision,
            comment: comment || null
        }).then(function () {
            delete noteDrafts[task.id];
            PF.toast(decision === "approved" ? "Approval recorded" : "Rejection recorded", "success");
            return loadRequestsCache().then(function () {
                return loadTasks();
            }).then(function (loaded) {
                PF.setFeedback(feedbackEl, {
                    tone: loaded ? "success" : "warning",
                    title: decision === "approved" ? "Approval recorded" : "Rejection recorded",
                    message: loaded
                        ? (decision === "approved"
                            ? "The task moved into decision history and the queue has been refreshed."
                            : "The rejection was recorded and the queue has been refreshed.")
                        : "The decision was recorded, but the latest queue state could not be refreshed."
                });
            });
        }).catch(function (err) {
            var msg = "Failed to record the decision.";
            if (err && err.data && err.data.detail) {
                msg = err.data.detail;
            }
            PF.toast(msg, "error");
            PF.setFeedback(feedback, {
                tone: "error",
                title: "Decision could not be recorded",
                message: msg
            });
            PF.setLoading(activeBtn, false);
            otherBtn.disabled = false;
            textarea.disabled = false;
        });
    }

    function ensureRequestDetail(requestId) {
        var cached = requestDetailsCache[requestId];
        if (cached && (cached.status === "loading" || cached.status === "ready")) {
            return;
        }

        requestDetailsCache[requestId] = { status: "loading" };
        if (getActiveTask() && getActiveTask().requestId === requestId) {
            renderReviewPanel(getActiveTask());
            renderPending(pendingTasks);
            renderDecided(decidedTasks);
        }

        api.getRequest(requestId).then(function (req) {
            requestDetailsCache[requestId] = {
                status: "ready",
                data: req
            };
            requestsCache[requestId] = req;

            var active = getActiveTask();
            if (active && active.requestId === requestId) {
                renderReviewPanel(active);
                renderPending(pendingTasks);
                renderDecided(decidedTasks);
            }
        }).catch(function () {
            requestDetailsCache[requestId] = {
                status: "error"
            };

            var active = getActiveTask();
            if (active && active.requestId === requestId) {
                renderReviewPanel(active);
                renderPending(pendingTasks);
                renderDecided(decidedTasks);
            }
        });
    }

    function renderErrorState(message) {
        var container = $("#error-state");
        container.innerHTML = "";
        container.appendChild(PF.buildStatePanel({
            tone: "danger",
            iconHtml: ERROR_ICON,
            title: "Unable to load the approval queue",
            text: message,
            action: {
                label: "Retry",
                onClick: function () {
                    loadRequestsCache().then(loadTasks);
                }
            }
        }));
    }

    function showState(state) {
        $("#loading-state").style.display = state === "loading" ? "" : "none";
        $("#error-state").style.display = state === "error" ? "" : "none";
        var content = $("#approval-content");
        if (content) content.style.display = state === "content" ? "" : "none";
    }

    function buildOverviewMetric(metric) {
        var card = document.createElement("div");
        card.className = "approval-overview-card";

        var label = document.createElement("div");
        label.className = "approval-overview-label";
        label.textContent = metric.label;

        var value = document.createElement("div");
        value.className = "approval-overview-value";
        value.textContent = metric.value;

        var note = document.createElement("div");
        note.className = "approval-overview-note";
        note.textContent = metric.note;

        card.appendChild(label);
        card.appendChild(value);
        card.appendChild(note);
        return card;
    }

    function buildMetricBlock(label, value) {
        var block = document.createElement("div");
        block.className = "approval-metric-block";

        var labelEl = document.createElement("div");
        labelEl.className = "approval-meta-label";
        labelEl.textContent = label;

        var valueEl = document.createElement("div");
        valueEl.className = "approval-meta-value";
        valueEl.textContent = value;

        block.appendChild(labelEl);
        block.appendChild(valueEl);
        return block;
    }

    function buildContextCard(label, text) {
        var card = document.createElement("div");
        card.className = "approval-context-card";

        var title = document.createElement("div");
        title.className = "approval-context-label";
        title.textContent = label;

        var body = document.createElement("p");
        body.className = "approval-context-text";
        body.textContent = text;

        card.appendChild(title);
        card.appendChild(body);
        return card;
    }

    function buildReviewLoadingBlock() {
        var block = document.createElement("div");
        block.className = "approval-review-loading";
        block.innerHTML =
            '<div class="skeleton skeleton-line"></div>' +
            '<div class="skeleton skeleton-line"></div>' +
            '<div class="skeleton skeleton-line"></div>' +
            '<div class="skeleton skeleton-rect"></div>';
        return block;
    }

    function buildInlineMessage(className, text) {
        var el = document.createElement("div");
        el.className = className;
        el.textContent = text;
        return el;
    }

    function requestValue(req) {
        return req && req.totalCents > 0 ? PF.formatCurrency(req.totalCents) : "Pending";
    }

    function countDistinctRequestIds(tasks) {
        var seen = {};
        var total = 0;
        for (var i = 0; i < tasks.length; i++) {
            if (!seen[tasks[i].requestId]) {
                seen[tasks[i].requestId] = true;
                total += 1;
            }
        }
        return total;
    }

    function countDistinctApprovers(tasks) {
        var seen = {};
        var total = 0;
        for (var i = 0; i < tasks.length; i++) {
            if (tasks[i].approverId && !seen[tasks[i].approverId]) {
                seen[tasks[i].approverId] = true;
                total += 1;
            }
        }
        return total;
    }

    function countDecisions(tasks, decision) {
        var total = 0;
        for (var i = 0; i < tasks.length; i++) {
            if (tasks[i].decision === decision) total += 1;
        }
        return total;
    }

    function shortId(id) {
        return (id || "").substring(0, 8);
    }

    function pluralize(count, singular) {
        return count + " " + singular + (count === 1 ? "" : "s");
    }

    function makeBadge(cssClass, text) {
        var badge = document.createElement("span");
        badge.className = "badge " + cssClass;
        badge.textContent = text;
        return badge;
    }
})();
