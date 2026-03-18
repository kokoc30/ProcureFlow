/**
 * ProcureFlow - Dashboard page logic.
 *
 * Loads all requests, renders stat cards, filter bar, and a sortable table.
 * Clicking a row navigates to the request detail page.
 *
 * Load order: ui.js -> caseUtils.js -> api.js -> dashboard.js
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

    var EMPTY_ICON =
        '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">' +
        '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>' +
        '<polyline points="14 2 14 8 20 8"></polyline>' +
        "</svg>";

    /* ==================================================================
       State
       ================================================================== */

    var usersCache = {};
    var allRequests = [];

    /* ==================================================================
       Init
       ================================================================== */

    document.addEventListener("DOMContentLoaded", function () {
        feedbackEl = $("#dashboard-feedback");
        refreshBtn = $("#refresh-btn");

        loadUsers().then(function () {
            loadRequests();
        });

        $("#filter-status").addEventListener("change", applyFilters);
        $("#filter-requester").addEventListener("change", applyFilters);

        if (refreshBtn) {
            refreshBtn.addEventListener("click", function () {
                loadRequests({
                    announceSuccess: true,
                    triggerButton: refreshBtn
                });
            });
        }
    });

    function loadUsers() {
        return api.getMockUsers().then(function (users) {
            if (Array.isArray(users)) {
                var select = $("#filter-requester");
                for (var i = 0; i < users.length; i++) {
                    usersCache[users[i].id] = users[i];
                    var opt = document.createElement("option");
                    opt.value = users[i].id;
                    opt.textContent = users[i].name;
                    select.appendChild(opt);
                }
            }
        }).catch(function () {
            // Non-critical - filter will still work without display names.
        });
    }

    function userName(id) {
        var u = usersCache[id];
        return u ? u.name : id || "\u2014";
    }

    /* ==================================================================
       Load requests
       ================================================================== */

    function loadRequests(options) {
        options = options || {};
        showState("loading");
        PF.clearFeedback(feedbackEl);

        if (options.triggerButton) {
            setLoading(options.triggerButton, true);
        }

        api.listRequests({ pageSize: 100 }).then(function (res) {
            allRequests = res.data || [];
            renderStats(allRequests);
            applyFilters();

            if (options.announceSuccess) {
                PF.setFeedback(feedbackEl, {
                    tone: "success",
                    title: "Dashboard refreshed",
                    message: "Request counts and workflow records are up to date."
                });
                PF.toast("Dashboard refreshed", "success");
            }
        }).catch(function (err) {
            var msg = "Failed to load operational requests.";
            if (err && err.data && err.data.detail) {
                msg = err.data.detail;
            }

            renderErrorState(msg);
            showState("error");
            PF.toast(msg, "error");
        }).finally(function () {
            if (options.triggerButton) {
                setLoading(options.triggerButton, false);
            }
        });
    }

    /* ==================================================================
       Filters
       ================================================================== */

    function applyFilters() {
        var statusVal = $("#filter-status").value;
        var requesterVal = $("#filter-requester").value;
        var hasActiveFilters = !!statusVal || !!requesterVal;

        var filtered = allRequests;

        if (statusVal) {
            filtered = filtered.filter(function (r) {
                return r.status === statusVal;
            });
        }

        if (requesterVal) {
            filtered = filtered.filter(function (r) {
                return r.requesterId === requesterVal;
            });
        }

        if (filtered.length === 0) {
            renderEmptyState(hasActiveFilters);
            showState("empty");
            return;
        }

        renderTable(filtered);
        showState("list");
    }

    function clearFilters() {
        $("#filter-status").value = "";
        $("#filter-requester").value = "";
        applyFilters();
        PF.clearFeedback(feedbackEl);
    }

    /* ==================================================================
       Render stat cards
       ================================================================== */

    function renderStats(requests) {
        var counts = { total: requests.length, review: 0, queue: 0, ready: 0 };

        for (var i = 0; i < requests.length; i++) {
            var status = requests[i].status;
            if (status === "approved") counts.ready += 1;
            else if (status === "pending_approval") counts.queue += 1;
            else if (status === "draft" || status === "clarification" || status === "policy_review") counts.review += 1;
        }

        $("#stat-total").textContent = counts.total;
        $("#stat-review").textContent = counts.review;
        $("#stat-queue").textContent = counts.queue;
        $("#stat-ready").textContent = counts.ready;
    }

    /* ==================================================================
       Render table
       ================================================================== */

    function renderTable(requests) {
        var tbody = $("#request-tbody");
        tbody.innerHTML = "";

        for (var i = 0; i < requests.length; i++) {
            var req = requests[i];
            var tr = document.createElement("tr");
            tr.className = "request-row";
            tr.setAttribute("tabindex", "0");
            tr.setAttribute("role", "link");
            tr.setAttribute("aria-label", "Open request: " + (req.title || "Untitled Request"));
            tr.dataset.requestId = req.id;

            var tdTitle = document.createElement("td");
            tdTitle.textContent = req.title || "Untitled Request";
            tr.appendChild(tdTitle);

            var tdStatus = document.createElement("td");
            tdStatus.appendChild(PF.statusBadge(req.status));
            tr.appendChild(tdStatus);

            var tdRequester = document.createElement("td");
            tdRequester.textContent = userName(req.requesterId);
            tr.appendChild(tdRequester);

            var tdDept = document.createElement("td");
            tdDept.textContent = req.department || "\u2014";
            tr.appendChild(tdDept);

            var tdAmount = document.createElement("td");
            tdAmount.textContent = req.totalCents > 0
                ? PF.formatCurrency(req.totalCents)
                : "\u2014";
            tr.appendChild(tdAmount);

            var tdCreated = document.createElement("td");
            tdCreated.textContent = PF.formatDate(req.createdAt);
            tr.appendChild(tdCreated);

            tr.addEventListener("click", handleRowClick);
            tr.addEventListener("keydown", handleRowKeydown);

            tbody.appendChild(tr);
        }
    }

    function handleRowClick(e) {
        var row = e.currentTarget;
        var id = row.dataset.requestId;
        if (id) {
            window.location.href = "/static/pages/request_detail.html?id=" + id;
        }
    }

    function handleRowKeydown(e) {
        if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            handleRowClick(e);
        }
    }

    /* ==================================================================
       State management
       ================================================================== */

    function renderErrorState(message) {
        var container = $("#error-state");
        container.innerHTML = "";
        container.appendChild(PF.buildStatePanel({
            tone: "danger",
            iconHtml: ERROR_ICON,
            title: "Unable to load dashboard data",
            text: message,
            action: {
                label: "Retry",
                onClick: function () {
                    loadRequests();
                }
            }
        }));
    }

    function renderEmptyState(hasActiveFilters) {
        var container = $("#empty-state");
        container.innerHTML = "";

        if (hasActiveFilters) {
            container.appendChild(PF.buildStatePanel({
                tone: "info",
                iconHtml: EMPTY_ICON,
                title: "No requests match these filters",
                text: "Adjust or clear the current workflow filters to bring matching requests back into view.",
                action: {
                    label: "Clear Filters",
                    onClick: clearFilters
                }
            }));
            return;
        }

        container.appendChild(PF.buildStatePanel({
            tone: "info",
            iconHtml: EMPTY_ICON,
            title: "No procurement requests yet",
            text: "New manufacturing requests will appear here once the intake form is submitted.",
            action: {
                label: "Start New Request",
                href: "/static/pages/request_form.html",
                className: "btn btn-primary btn-sm"
            }
        }));
    }

    function showState(state) {
        $("#loading-state").style.display = state === "loading" ? "" : "none";
        $("#error-state").style.display = state === "error" ? "" : "none";
        $("#empty-state").style.display = state === "empty" ? "" : "none";
        $("#request-list").style.display = state === "list" ? "" : "none";
    }
})();
