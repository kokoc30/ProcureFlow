/**
 * ProcureFlow - manufacturing procurement intake form logic.
 *
 * Loads reference data (users, departments) into dropdowns,
 * manages the dynamic requested-items list, validates, and
 * submits via PF.api.createRequest().
 *
 * Load order: ui.js -> caseUtils.js -> api.js -> requestForm.js
 */

(function () {
    "use strict";

    var $ = PF.$;
    var $$ = PF.$$;
    var toast = PF.toast;
    var setLoading = PF.setLoading;
    var api = PF.api;

    // Cached DOM references (set in init)
    var form;
    var formFeedback;
    var requesterSelect;
    var departmentSelect;
    var costCenterInput;
    var itemsList;
    var submitBtn;

    // Reference data caches
    var users = [];
    var departments = [];

    // AI intake panel controller (set during init)
    var intakePanel = null;

    /* ==================================================================
       Initialisation
       ================================================================== */

    document.addEventListener("DOMContentLoaded", init);

    async function init() {
        form = $("#request-form");
        formFeedback = $("#request-form-feedback");
        requesterSelect = $("#requester-id");
        departmentSelect = $("#department");
        costCenterInput = $("#cost-center");
        itemsList = $("#items-list");
        submitBtn = $("#submit-btn");

        // Bind events
        form.addEventListener("submit", handleSubmit);
        departmentSelect.addEventListener("change", onDepartmentChange);
        requesterSelect.addEventListener("change", onRequesterChange);
        $("#add-item-btn").addEventListener("click", function () {
            addItemRow();
        });

        // Seed initial item row and load reference data
        addItemRow();
        await loadReferenceData();

        // Initialize AI intake panel
        if (PF.aiCards && PF.aiCards.renderIntakePanel) {
            intakePanel = PF.aiCards.renderIntakePanel(
                document.getElementById("intake-ai-panel"),
                collectFormData
            );
        }
    }

    /**
     * Collect current form data for AI intake preview.
     * Used as callback by the AI panel's "Analyze Draft" button.
     */
    function collectFormData() {
        return {
            title: $("#title").value.trim(),
            department: departmentSelect.value,
            requestedItems: collectItems(),
            justification: $("#justification").value.trim() || null,
            costCenter: costCenterInput.value || null,
            deliveryDate: $("#delivery-date").value || null,
        };
    }

    /* ==================================================================
       Reference data
       ================================================================== */

    async function loadReferenceData() {
        setReferenceLoading(true);
        PF.clearFeedback(formFeedback);

        try {
            var results = await Promise.all([
                api.getMockUsers(),
                api.getMockDepartments(),
            ]);
            users = results[0] || [];
            departments = results[1] || [];
            populateDropdowns();

            if (users.length === 0 || departments.length === 0) {
                PF.setFeedback(formFeedback, {
                    tone: "warning",
                    title: "Reference data is incomplete",
                    message: "Request owners or department routing data are missing. Retry before submitting a new request.",
                    action: {
                        label: "Retry",
                        onClick: function () {
                            loadReferenceData();
                        }
                    }
                });
            }
        } catch (err) {
            users = [];
            departments = [];
            resetReferenceSelects();
            costCenterInput.value = "";

            PF.setFeedback(formFeedback, {
                tone: "error",
                title: "Reference data unavailable",
                message: "Request owners and department routing data could not be loaded. Retry to continue with a new request.",
                action: {
                    label: "Retry",
                    onClick: function () {
                        loadReferenceData();
                    }
                }
            });
            toast("Failed to load requester and department data: " + err.message, "error");
        } finally {
            setReferenceLoading(false);
        }
    }

    function populateDropdowns() {
        resetReferenceSelects();

        for (var i = 0; i < users.length; i++) {
            var u = users[i];
            var opt = document.createElement("option");
            opt.value = u.id;
            opt.textContent = u.name + " (" + u.department + ")";
            requesterSelect.appendChild(opt);
        }

        for (var j = 0; j < departments.length; j++) {
            var d = departments[j];
            var dOpt = document.createElement("option");
            dOpt.value = d.name;
            dOpt.dataset.costCenter = d.costCenter || "";
            dOpt.textContent = d.name;
            departmentSelect.appendChild(dOpt);
        }
    }

    function resetReferenceSelects() {
        requesterSelect.innerHTML = '<option value="">Select requester</option>';
        departmentSelect.innerHTML = '<option value="">Select department</option>';
    }

    function setReferenceLoading(isLoading) {
        requesterSelect.disabled = isLoading;
        departmentSelect.disabled = isLoading;

        if (isLoading) {
            requesterSelect.innerHTML = '<option value="">Loading request owners...</option>';
            departmentSelect.innerHTML = '<option value="">Loading departments...</option>';
        }
    }

    /* ==================================================================
       Dropdown change handlers
       ================================================================== */

    function onRequesterChange() {
        var userId = requesterSelect.value;
        if (!userId) return;

        var user = findUser(userId);
        if (user && user.department) {
            departmentSelect.value = user.department;
            onDepartmentChange();
        }
    }

    function onDepartmentChange() {
        var selected = departmentSelect.options[departmentSelect.selectedIndex];
        costCenterInput.value = selected && selected.dataset.costCenter
            ? selected.dataset.costCenter
            : "";
    }

    function findUser(id) {
        for (var i = 0; i < users.length; i++) {
            if (users[i].id === id) return users[i];
        }
        return null;
    }

    /* ==================================================================
       Dynamic items list
       ================================================================== */

    function addItemRow() {
        var row = document.createElement("div");
        row.className = "item-row";

        var number = document.createElement("span");
        number.className = "item-number";
        updateItemNumbers();

        var input = document.createElement("input");
        input.type = "text";
        input.className = "form-input";
        input.placeholder = "e.g. 2 etch chamber o-ring seal kits, 1 lot 300mm monitor wafers";
        input.name = "requested_item";
        input.setAttribute("aria-label", "Material, part, or service line item");

        var removeBtn = document.createElement("button");
        removeBtn.type = "button";
        removeBtn.className = "btn btn-ghost btn-sm item-remove";
        removeBtn.textContent = "Remove";
        removeBtn.addEventListener("click", function () {
            if (itemsList.querySelectorAll(".item-row").length > 1) {
                row.remove();
                updateItemNumbers();
                updateRemoveButtons();
            }
        });

        row.appendChild(number);
        row.appendChild(input);
        row.appendChild(removeBtn);
        itemsList.appendChild(row);

        updateItemNumbers();
        updateRemoveButtons();
        input.focus();
    }

    function updateItemNumbers() {
        var rows = itemsList.querySelectorAll(".item-row");
        for (var i = 0; i < rows.length; i++) {
            var num = rows[i].querySelector(".item-number");
            if (num) num.textContent = (i + 1) + ".";
        }
    }

    function updateRemoveButtons() {
        var rows = itemsList.querySelectorAll(".item-row");
        var buttons = itemsList.querySelectorAll(".item-remove");
        for (var i = 0; i < buttons.length; i++) {
            // Hide remove button when only one row remains
            buttons[i].style.visibility = rows.length <= 1 ? "hidden" : "visible";
        }
    }

    function collectItems() {
        var inputs = itemsList.querySelectorAll("input[name='requested_item']");
        var items = [];
        var seen = {};
        var hadDuplicates = false;

        for (var i = 0; i < inputs.length; i++) {
            var val = inputs[i].value.trim();
            if (!val) continue;

            var key = val.toLowerCase();
            if (seen[key]) {
                hadDuplicates = true;
                continue;
            }
            seen[key] = true;
            items.push(val);
        }

        if (hadDuplicates) {
            toast("Duplicate line items were removed.", "warning");
        }

        return items;
    }

    /* ==================================================================
       Validation
       ================================================================== */

    function clearErrors() {
        var invalids = $$(".is-invalid");
        for (var i = 0; i < invalids.length; i++) {
            invalids[i].classList.remove("is-invalid");
        }
        var errors = $$(".form-error");
        for (var j = 0; j < errors.length; j++) {
            errors[j].textContent = "";
        }
    }

    function showFieldError(fieldId, errorId, message) {
        var field = $("#" + fieldId);
        var errorEl = $("#" + errorId);
        if (field) field.classList.add("is-invalid");
        if (errorEl) errorEl.textContent = message;
    }

    function validate() {
        clearErrors();
        var valid = true;

        if (!requesterSelect.value) {
            showFieldError("requester-id", "requester-id-error", "Please select a request owner.");
            valid = false;
        }

        if (!departmentSelect.value) {
            showFieldError("department", "department-error", "Please select an owning department.");
            valid = false;
        }

        var title = $("#title").value.trim();
        if (!title) {
            showFieldError("title", "title-error", "Please enter a request title.");
            valid = false;
        }

        var items = collectItems();
        if (items.length === 0) {
            $("#items-error").textContent = "Please add at least one material, part, or service line.";
            valid = false;
        }

        if (!valid) {
            PF.setFeedback(formFeedback, {
                tone: "warning",
                title: "Review required fields",
                message: "Fill in the highlighted fields before submitting the request."
            });
        } else {
            PF.clearFeedback(formFeedback);
        }

        return valid;
    }

    /* ==================================================================
       Backend error mapping
       ================================================================== */

    /**
     * Map backend field names to form field/error element IDs.
     */
    var FIELD_MAP = {
        requester_id: ["requester-id", "requester-id-error"],
        department:   ["department", "department-error"],
        cost_center:  ["cost-center", null],
        title:        ["title", "title-error"],
        requested_items: [null, "items-error"],
    };

    /**
     * Surface backend validation errors inline on the form.
     * Handles both Pydantic 422 arrays and plain string details.
     */
    function surfaceBackendErrors(err) {
        clearErrors();

        var detail = err.data && err.data.detail;

        // Pydantic 422: detail is an array of {loc, msg, type}
        if (Array.isArray(detail)) {
            for (var i = 0; i < detail.length; i++) {
                var item = detail[i];
                var loc = item.loc || [];
                // loc is typically ["body", "field_name"]
                var fieldName = loc.length > 1 ? loc[loc.length - 1] : null;
                var mapping = fieldName ? FIELD_MAP[fieldName] : null;

                if (mapping) {
                    var msg = item.msg || "Invalid value";
                    // Clean Pydantic prefix "Value error, ..."
                    msg = msg.replace(/^Value error,\s*/i, "");
                    if (mapping[0] && mapping[1]) {
                        showFieldError(mapping[0], mapping[1], msg);
                    } else if (mapping[1]) {
                        $("#" + mapping[1]).textContent = msg;
                    }
                }
            }
            // Toast the first error
            var firstMsg = detail[0] && detail[0].msg
                ? detail[0].msg.replace(/^Value error,\s*/i, "")
                : "Validation failed";
            PF.setFeedback(formFeedback, {
                tone: "error",
                title: "Request could not be submitted",
                message: firstMsg
            });
            toast(firstMsg, "error");
            return;
        }

        // Plain string detail (e.g. "Requester not found", "Invalid cost_center")
        var message = (typeof detail === "string") ? detail : (err.message || "Request failed");
        PF.setFeedback(formFeedback, {
            tone: "error",
            title: "Request could not be submitted",
            message: message
        });
        toast(message, "error");

        // Try to map known backend messages to fields
        if (/requester/i.test(message)) {
            showFieldError("requester-id", "requester-id-error", message);
        } else if (/cost.center/i.test(message)) {
            showFieldError("cost-center", null, message);
        }
    }

    /* ==================================================================
       Submit
       ================================================================== */

    async function handleSubmit(e) {
        e.preventDefault();

        if (!validate()) return;

        var payload = {
            requesterId: requesterSelect.value,
            department: departmentSelect.value,
            costCenter: costCenterInput.value || null,
            title: $("#title").value.trim(),
            description: $("#description").value.trim(),
            requestedItems: collectItems(),
            justification: $("#justification").value.trim() || null,
            deliveryDate: $("#delivery-date").value || null,
        };

        setLoading(submitBtn, true);

        try {
            var result = await api.createRequest(payload);
            var detailUrl = "/static/pages/request_detail.html?id=" + result.id;

            toast("Request created successfully.", "success");
            PF.setFeedback(formFeedback, {
                tone: "success",
                title: "Request submitted",
                message: "The intake was created successfully. Continue to the request workspace for workflow review and next steps.",
                action: {
                    label: "Open Request Detail",
                    className: "btn btn-primary btn-sm",
                    onClick: function () {
                        window.location.href = detailUrl;
                    }
                }
            });

            // Run intake analysis and show AI results before redirect
            if (intakePanel) {
                try {
                    var intakeResult = await api.runIntake(result.id);
                    intakePanel.showRunIntakeResult(intakeResult.analysis, result.id);
                } catch (_) {
                    // Non-critical: still allow navigation
                }
            }

            // Disable form to prevent re-submission
            disableForm();

            // Convert submit button to a navigation link
            setLoading(submitBtn, false);
            submitBtn.textContent = "View Request Details \u2192";
            submitBtn.type = "button";
            submitBtn.onclick = function () {
                window.location.href = detailUrl;
            };

            // If no intake panel, redirect after short delay
            if (!intakePanel) {
                setTimeout(function () {
                    window.location.href = detailUrl;
                }, 800);
            }
        } catch (err) {
            surfaceBackendErrors(err);
            setLoading(submitBtn, false);
        }
    }

    /**
     * Disable all form inputs after successful submission.
     */
    function disableForm() {
        form.classList.add("form-submitted");
        var inputs = form.querySelectorAll("input, select, textarea, button[type='button']");
        for (var i = 0; i < inputs.length; i++) {
            inputs[i].disabled = true;
        }
    }
})();
