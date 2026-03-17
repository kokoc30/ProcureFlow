/**
 * ProcureFlow – snake_case / camelCase key conversion.
 * Extends window.PF (defined in ui.js – must load first).
 */

(function () {
    "use strict";

    /* ==================================================================
       Single-string converters
       ================================================================== */

    /**
     * Convert a snake_case string to camelCase.
     * @param {string} str
     * @returns {string}  e.g. "unit_price_cents" → "unitPriceCents"
     */
    function toCamel(str) {
        return str.replace(/_([a-z0-9])/g, function (_, ch) {
            return ch.toUpperCase();
        });
    }

    /**
     * Convert a camelCase string to snake_case.
     * @param {string} str
     * @returns {string}  e.g. "unitPriceCents" → "unit_price_cents"
     */
    function toSnake(str) {
        return str
            .replace(/([a-z0-9])([A-Z])/g, "$1_$2")
            .replace(/([A-Z])([A-Z][a-z])/g, "$1_$2")
            .toLowerCase();
    }

    /* ==================================================================
       Recursive key converters
       ================================================================== */

    /**
     * Recursively convert all object keys from snake_case to camelCase.
     * Arrays are traversed; primitives pass through unchanged.
     * @param {*} obj
     * @returns {*}
     */
    function camelizeKeys(obj) {
        if (Array.isArray(obj)) {
            return obj.map(camelizeKeys);
        }
        if (obj !== null && typeof obj === "object") {
            var out = {};
            var keys = Object.keys(obj);
            for (var i = 0; i < keys.length; i++) {
                out[toCamel(keys[i])] = camelizeKeys(obj[keys[i]]);
            }
            return out;
        }
        return obj;
    }

    /**
     * Recursively convert all object keys from camelCase to snake_case.
     * Arrays are traversed; primitives pass through unchanged.
     * @param {*} obj
     * @returns {*}
     */
    function decamelizeKeys(obj) {
        if (Array.isArray(obj)) {
            return obj.map(decamelizeKeys);
        }
        if (obj !== null && typeof obj === "object") {
            var out = {};
            var keys = Object.keys(obj);
            for (var i = 0; i < keys.length; i++) {
                out[toSnake(keys[i])] = decamelizeKeys(obj[keys[i]]);
            }
            return out;
        }
        return obj;
    }

    /* ==================================================================
       Extend PF namespace
       ================================================================== */

    window.PF.toCamel = toCamel;
    window.PF.toSnake = toSnake;
    window.PF.camelizeKeys = camelizeKeys;
    window.PF.decamelizeKeys = decamelizeKeys;
})();
