/**
 * ProcureFlow - base UI helpers.
 * Framework-free, dependency-free utilities exposed on window.PF.
 */

(function () {
    "use strict";

    /* ==================================================================
       Health check
       ================================================================== */

    async function checkHealth() {
        try {
            var res = await fetch("/api/v1/health");
            if (!res.ok) return;
            await res.json();
        } catch (_) {
            // Ignore health-check failures because they are non-critical to the UI.
        }
    }

    document.addEventListener("DOMContentLoaded", checkHealth);

    /* ==================================================================
       DOM helpers
       ================================================================== */

    function $(selector, root) {
        return (root || document).querySelector(selector);
    }

    function $$(selector, root) {
        return Array.from((root || document).querySelectorAll(selector));
    }

    /* ==================================================================
       Toast notifications
       ================================================================== */

    function ensureToastContainer() {
        var container = document.getElementById("toast-container");
        if (!container) {
            container = document.createElement("div");
            container.id = "toast-container";
            container.setAttribute("aria-live", "polite");
            container.setAttribute("aria-atomic", "true");
            document.body.appendChild(container);
        }
        return container;
    }

    function toast(message, type, duration) {
        type = type || "info";
        duration = duration || 3500;

        var container = ensureToastContainer();
        var el = document.createElement("div");
        el.className = "toast toast-" + type;
        el.textContent = message;
        el.setAttribute("role", "alert");
        container.appendChild(el);

        setTimeout(function () {
            el.classList.add("toast-exit");
            el.addEventListener("animationend", function () {
                el.remove();
            });
        }, duration);
    }

    /* ==================================================================
       Inline state feedback
       ================================================================== */

    function resolveTarget(target) {
        if (!target) return null;
        if (typeof target === "string") return $(target);
        return target;
    }

    function clearFeedback(target) {
        var container = resolveTarget(target);
        if (!container) return;
        container.innerHTML = "";
    }

    function buildActionControl(action) {
        if (!action || !action.label) return null;

        var control = el(action.href ? "a" : "button", {
            className: action.className || "btn btn-secondary btn-sm",
            text: action.label
        });

        if (action.href) {
            control.href = action.href;
        } else {
            control.type = action.type || "button";
        }

        if (typeof action.onClick === "function") {
            control.addEventListener("click", action.onClick);
        }

        return control;
    }

    function setFeedback(target, options) {
        var container = resolveTarget(target);
        if (!container) return null;

        clearFeedback(container);

        if (!options || (!options.title && !options.message)) {
            return null;
        }

        var tone = options.tone || "info";
        var banner = el("div", {
            className: "state-banner state-banner-" + tone
        });
        banner.setAttribute("role", tone === "error" ? "alert" : "status");
        banner.setAttribute("aria-live", tone === "error" ? "assertive" : "polite");

        var body = el("div", "state-banner-body");

        if (options.title) {
            body.appendChild(el("div", {
                className: "state-banner-title",
                text: options.title
            }));
        }

        if (options.message) {
            body.appendChild(el("div", {
                className: "state-banner-message",
                text: options.message
            }));
        }

        banner.appendChild(body);

        if (options.action) {
            var actions = el("div", "state-banner-actions");
            var actionControl = buildActionControl(options.action);
            if (actionControl) {
                actions.appendChild(actionControl);
                banner.appendChild(actions);
            }
        }

        container.appendChild(banner);
        return banner;
    }

    function buildStatePanel(options) {
        options = options || {};

        var panel = el("div", {
            className: "empty-state" +
                (options.tone ? " empty-state-tone-" + options.tone : "") +
                (options.compact ? " empty-state-compact" : "")
        });

        if (options.icon || options.iconHtml) {
            var icon = el("div", "empty-state-icon");
            if (options.iconHtml) {
                icon.innerHTML = options.iconHtml;
            } else {
                icon.textContent = options.icon;
            }
            panel.appendChild(icon);
        }

        if (options.title) {
            panel.appendChild(el("div", {
                className: "empty-state-title",
                text: options.title
            }));
        }

        if (options.text) {
            panel.appendChild(el("p", {
                className: "empty-state-text",
                text: options.text
            }));
        }

        if (options.action) {
            var actionWrap = el("div", "empty-state-actions");
            var actionControl = buildActionControl(options.action);
            if (actionControl) {
                actionWrap.appendChild(actionControl);
                panel.appendChild(actionWrap);
            }
        }

        return panel;
    }

    /* ==================================================================
       Button loading state
       ================================================================== */

    function setLoading(button, isLoading) {
        if (isLoading) {
            button._originalText = button.textContent;
            button.classList.add("btn-loading");
            button.disabled = true;
        } else {
            button.classList.remove("btn-loading");
            button.disabled = false;
            if (button._originalText) {
                button.textContent = button._originalText;
                delete button._originalText;
            }
        }
    }

    /* ==================================================================
       Formatting
       ================================================================== */

    function formatCurrency(cents) {
        var dollars = (cents / 100).toFixed(2);
        return "$" + dollars.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
    }

    function formatDate(isoString) {
        if (!isoString) return "\u2014";
        var d = new Date(isoString);
        return d.toLocaleDateString("en-US", {
            month: "short",
            day: "numeric",
            year: "numeric",
        });
    }

    function formatDateTime(isoString) {
        if (!isoString) return "\u2014";
        var d = new Date(isoString);
        return d.toLocaleDateString("en-US", {
            month: "short",
            day: "numeric",
            year: "numeric",
            hour: "numeric",
            minute: "2-digit",
        });
    }

    /* ==================================================================
       Badge helper
       ================================================================== */

    function createBadge(status) {
        var el = document.createElement("span");
        var label = status.charAt(0).toUpperCase() + status.slice(1);
        el.className = "badge badge-" + status.toLowerCase();
        el.textContent = label;
        return el;
    }

    /* ==================================================================
       Shared status / role constants
       ================================================================== */

    var STATUS_MAP = {
        draft:            { css: "badge-draft",         label: "Draft" },
        clarification:    { css: "badge-clarification", label: "Needs Info" },
        policy_review:    { css: "badge-review",        label: "Policy Review" },
        pending_approval: { css: "badge-pending",       label: "In Approval" },
        approved:         { css: "badge-approved",      label: "Approved" },
        rejected:         { css: "badge-rejected",      label: "Rejected" }
    };

    var ROLE_LABELS = {
        manager: "Manager",
        dept_head: "Dept Head",
        procurement: "Procurement",
        finance: "Finance"
    };

    function statusBadge(status) {
        var info = STATUS_MAP[status] || { css: "badge-draft", label: status };
        var span = document.createElement("span");
        span.className = "badge " + info.css;
        span.textContent = info.label;
        return span;
    }

    /* ==================================================================
       API helper
       ================================================================== */

    var API_BASE = "/api/v1";

    async function api(method, path, body) {
        var url = API_BASE + path;
        var options = {
            method: method,
            headers: { "Content-Type": "application/json" },
        };
        if (body && method !== "GET") {
            options.body = JSON.stringify(body);
        }

        var res = await fetch(url, options);
        if (!res.ok) {
            var errorData;
            try {
                errorData = await res.json();
            } catch (e) {
                errorData = { detail: res.statusText };
            }
            var err = new Error(errorData.detail || "API request failed");
            err.status = res.status;
            err.data = errorData;
            throw err;
        }

        if (res.status === 204) return null;
        return res.json();
    }

    /* ==================================================================
       DOM creation helper
       ================================================================== */

    function el(tag, attrs, children) {
        var node = document.createElement(tag);
        if (typeof attrs === "string") {
            node.className = attrs;
        } else if (attrs) {
            for (var key in attrs) {
                if (key === "className" || key === "class") {
                    node.className = attrs[key];
                } else if (key === "text") {
                    node.textContent = attrs[key];
                } else if (key === "html") {
                    node.innerHTML = attrs[key];
                } else if (key === "style" && typeof attrs[key] === "object") {
                    for (var s in attrs[key]) { node.style[s] = attrs[key][s]; }
                } else {
                    node.setAttribute(key, attrs[key]);
                }
            }
        }
        if (typeof children === "string") {
            node.textContent = children;
        } else if (Array.isArray(children)) {
            for (var i = 0; i < children.length; i++) {
                if (children[i]) node.appendChild(children[i]);
            }
        } else if (children instanceof Node) {
            node.appendChild(children);
        }
        return node;
    }

    /* ==================================================================
       Show / hide helpers
       ================================================================== */

    function show(element) {
        if (element) element.style.display = "";
    }

    function hide(element) {
        if (element) element.style.display = "none";
    }

    function toggle(element, visible) {
        if (!element) return;
        if (typeof visible === "undefined") {
            visible = element.style.display === "none";
        }
        element.style.display = visible ? "" : "none";
    }

    /* ==================================================================
       Number formatting
       ================================================================== */

    function formatNumber(value) {
        if (value == null || isNaN(value)) return "\u2014";
        return Number(value).toLocaleString("en-US");
    }

    /* ==================================================================
       Debounce
       ================================================================== */

    function debounce(fn, delay) {
        var timer;
        return function () {
            var context = this;
            var args = arguments;
            clearTimeout(timer);
            timer = setTimeout(function () {
                fn.apply(context, args);
            }, delay || 300);
        };
    }

    /* ==================================================================
       HTML escaping
       ================================================================== */

    function escapeHtml(str) {
        if (!str) return "";
        var div = document.createElement("div");
        div.textContent = str;
        return div.innerHTML;
    }

    /* ==================================================================
       Public API
       ================================================================== */

    window.PF = {
        $: $,
        $$: $$,
        toast: toast,
        clearFeedback: clearFeedback,
        setFeedback: setFeedback,
        buildStatePanel: buildStatePanel,
        setLoading: setLoading,
        formatCurrency: formatCurrency,
        formatDate: formatDate,
        formatDateTime: formatDateTime,
        formatNumber: formatNumber,
        createBadge: createBadge,
        api: api,
        STATUS_MAP: STATUS_MAP,
        ROLE_LABELS: ROLE_LABELS,
        statusBadge: statusBadge,
        el: el,
        show: show,
        hide: hide,
        toggle: toggle,
        debounce: debounce,
        escapeHtml: escapeHtml,
    };
})();
