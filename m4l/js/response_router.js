/**
 * response_router.js — Max/MSP `js` object for routing all service responses.
 *
 * Handles three response types from groove_http.js:
 *   - /generate responses → routes plan, summary, status
 *   - /presets responses  → populates umenu dropdown, stores preset IDs
 *   - /health responses   → sends status message
 *
 * Outlets:
 *   0: Plan JSON string (for post_process.js)
 *   1: Summary text string (for summary display — prepend "set" before textedit)
 *   2: Status message string (for status display — prepend "set" before textedit)
 *   3: umenu messages (clear, append — wire directly to umenu)
 *   4: preset_id string (when user selects from umenu via "select" message)
 *
 * Messages:
 *   anything      — parse JSON response and route to outlets
 *   select <int>  — look up preset_id by umenu index, output on outlet 4
 *
 * Canonical reference: Docs/JSON_Contract.md (GenerateResponse schema)
 */

autowatch = 1;
inlets = 1;
outlets = 5;

var preset_ids = [];

function anything() {
    var str = arrayfromargs(messagename, arguments).join(" ");

    // Find the start of JSON (object or array)
    var obj_idx = str.indexOf("{");
    var arr_idx = str.indexOf("[");
    var start = -1;
    if (obj_idx >= 0 && arr_idx >= 0) {
        start = Math.min(obj_idx, arr_idx);
    } else if (obj_idx >= 0) {
        start = obj_idx;
    } else if (arr_idx >= 0) {
        start = arr_idx;
    }
    if (start > 0) str = str.substring(start);

    try {
        var resp = JSON.parse(str);
    } catch (e) {
        outlet(2, "error: failed to parse response — " + e.message);
        return;
    }

    // Array → presets response
    if (Array.isArray(resp)) {
        _handle_presets(resp);
        return;
    }

    // Object with "plan" → generate response
    if (resp.plan) {
        _handle_generate(resp);
        return;
    }

    // Object with "ok" but no plan → health response
    if (resp.ok !== undefined) {
        outlet(2, resp.ok ? "service healthy" : "service error");
        return;
    }

    outlet(2, "unknown response type");
}

/**
 * Called when umenu selection changes — receives the selected index.
 * Wire: umenu outlet → [prepend select] → response_router inlet
 */
function select(idx) {
    idx = Math.floor(idx);
    if (idx >= 0 && idx < preset_ids.length) {
        outlet(4, preset_ids[idx]);
    }
}

// --- Internal handlers ---

function _handle_generate(resp) {
    if (!resp.ok) {
        outlet(2, "error: " + (resp.error || "unknown error from service"));
        return;
    }

    var note_count = resp.plan.notes ? resp.plan.notes.length : 0;
    // Output rightmost first (Max convention)
    outlet(2, "ok — " + note_count + " notes received");
    outlet(1, resp.summary || "");
    outlet(0, JSON.stringify(resp.plan));
}

function _handle_presets(arr) {
    preset_ids = [];
    outlet(3, "clear");
    for (var i = 0; i < arr.length; i++) {
        preset_ids.push(arr[i].id);
        outlet(3, "append", arr[i].name);
    }
    outlet(2, "loaded " + arr.length + " presets");
}
