/**
 * ProcureFlow – shared API client with domain methods.
 *
 * Wraps PF.api() (from ui.js) with automatic camelCase ↔ snake_case
 * key conversion.  Every page script should call these helpers instead
 * of using raw fetch().
 *
 * Load order: ui.js → caseUtils.js → api.js → page script.
 */

(function () {
    "use strict";

    var rawApi = window.PF.api; // base fetch wrapper from ui.js

    /* ==================================================================
       Base helpers with automatic key conversion
       ================================================================== */

    /**
     * Send an API request with automatic key conversion.
     * Outgoing bodies are converted camelCase → snake_case.
     * Incoming JSON responses are converted snake_case → camelCase.
     *
     * @param {"GET"|"POST"|"PUT"|"PATCH"|"DELETE"} method
     * @param {string} path  – relative to /api/v1
     * @param {object} [body]
     * @returns {Promise<object|null>}
     */
    async function apiCall(method, path, body) {
        var snakeBody = body ? PF.decamelizeKeys(body) : undefined;
        var data = await rawApi(method, path, snakeBody);
        return data !== null && typeof data === "object"
            ? PF.camelizeKeys(data)
            : data;
    }

    function get(path) {
        return apiCall("GET", path);
    }

    function post(path, body) {
        return apiCall("POST", path, body);
    }

    function put(path, body) {
        return apiCall("PUT", path, body);
    }

    function patch(path, body) {
        return apiCall("PATCH", path, body);
    }

    /* ==================================================================
       Query-string helper
       ================================================================== */

    /**
     * Build a query string from a plain object, skipping null/undefined.
     * Keys are converted to snake_case for the backend.
     * @param {object} params
     * @returns {string}  e.g. "?status=draft&requester_id=abc"
     */
    function buildQuery(params) {
        if (!params) return "";
        var parts = [];
        var keys = Object.keys(params);
        for (var i = 0; i < keys.length; i++) {
            var val = params[keys[i]];
            if (val !== null && val !== undefined && val !== "") {
                parts.push(
                    encodeURIComponent(PF.toSnake(keys[i])) +
                    "=" +
                    encodeURIComponent(val)
                );
            }
        }
        return parts.length ? "?" + parts.join("&") : "";
    }

    /* ==================================================================
       Domain methods – Requests
       ================================================================== */

    function createRequest(data) {
        return post("/requests", data);
    }

    function listRequests(params) {
        return get("/requests" + buildQuery(params));
    }

    function getRequest(id) {
        return get("/requests/" + id);
    }

    /* ==================================================================
       Domain methods – Clarifications
       ================================================================== */

    function listClarifications(requestId) {
        return get("/requests/" + requestId + "/clarifications");
    }

    function answerClarification(clarificationId, data) {
        return post(
            "/clarifications/" + clarificationId + "/answer",
            data
        );
    }

    /* ==================================================================
       Domain methods – Policy
       ================================================================== */

    function evaluatePolicy(requestId) {
        return post("/policy/" + requestId + "/evaluate");
    }

    /* ==================================================================
       Domain methods – Catalog
       ================================================================== */

    function listCatalog() {
        return get("/catalog");
    }

    function matchCatalog(data) {
        return post("/catalog/match", data);
    }

    /* ==================================================================
       Domain methods – Purchase Orders
       ================================================================== */

    function generatePo(requestId) {
        return post("/po/generate", { requestId: requestId });
    }

    function getPo(poId) {
        return get("/po/" + poId);
    }

    /* ==================================================================
       Domain methods – Approvals
       ================================================================== */

    function startApproval(requestId) {
        return post("/approvals/start", { requestId: requestId });
    }

    function recordDecision(taskId, data) {
        return post("/approvals/" + taskId + "/decide", data);
    }

    function listApprovalTasks(params) {
        return get("/approvals" + buildQuery(params));
    }

    /* ==================================================================
       Domain methods – Agents
       ================================================================== */

    function runIntake(requestId) {
        return post("/agents/run-intake/" + requestId);
    }

    function agentStatus() {
        return get("/agents/status");
    }

    function intakePreview(body) {
        return post("/agents/intake-preview", body);
    }

    function intakeAnalysis(requestId) {
        return post("/agents/intake-analysis/" + requestId);
    }

    function policyExplanation(requestId) {
        return post("/agents/policy-explanation/" + requestId);
    }

    function catalogExplanation(body) {
        return post("/agents/catalog-explanation", body);
    }

    function approvalNotification(requestId, body) {
        return post("/agents/approval-notification/" + requestId, body || {});
    }

    /* ==================================================================
       Domain methods – Audit
       ================================================================== */

    function getAuditEvents(requestId) {
        return get("/audit/" + requestId);
    }

    /* ==================================================================
       Domain methods – Reference data
       ================================================================== */

    function getMockUsers() {
        return get("/users");
    }

    function getMockDepartments() {
        return get("/departments");
    }

    /* ==================================================================
       Expose on PF namespace
       ================================================================== */

    window.PF.api = {
        // Low-level helpers (with auto key conversion)
        get: get,
        post: post,
        put: put,
        patch: patch,

        // Requests
        createRequest: createRequest,
        listRequests: listRequests,
        getRequest: getRequest,

        // Clarifications
        listClarifications: listClarifications,
        answerClarification: answerClarification,

        // Policy
        evaluatePolicy: evaluatePolicy,

        // Catalog
        listCatalog: listCatalog,
        matchCatalog: matchCatalog,

        // Purchase Orders
        generatePo: generatePo,
        getPo: getPo,

        // Approvals
        startApproval: startApproval,
        recordDecision: recordDecision,
        listApprovalTasks: listApprovalTasks,

        // Agents
        runIntake: runIntake,
        agentStatus: agentStatus,
        intakePreview: intakePreview,
        intakeAnalysis: intakeAnalysis,
        policyExplanation: policyExplanation,
        catalogExplanation: catalogExplanation,
        approvalNotification: approvalNotification,

        // Audit
        getAuditEvents: getAuditEvents,

        // Reference data
        getMockUsers: getMockUsers,
        getMockDepartments: getMockDepartments,
    };
})();
