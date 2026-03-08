/**
 * response_router.js — Max/MSP `js` object for routing all service responses.
 *
 * Handles response types from groove_http.js:
 *   - /generate responses → routes plan, summary, status
 *   - /surprise responses → routes generated prompt + controls + status
 *   - /presets responses  → populates umenu dropdown, stores preset IDs
 *   - /health responses   → sends status message
 *
 * Outlets:
 *   0: Plan JSON string (for post_process.js)
 *   1: Summary text string (for summary display — prepend "set" before textedit)
 *   2: Status message string (for status display — prepend "set" before textedit)
 *   3: umenu messages (clear, append — wire directly to umenu)
 *   4: preset_id string (when user selects from umenu via "select" message)
 *   5: preset defaults JSON (density, complexity, swing, humanize_ms, velocity_jitter)
 *   6: Surprise prompt text (wire to prompt UI and request_builder)
 *   7: Surprise request JSON (wire to [prepend surprise] → groove_http)
 *   8: Busy indicator (1 = working, 0 = idle — wire to live.text or live.led)
 *   9: Mode umenu messages (clear, append — wire to mode umenu)
 *   10: Key umenu messages (clear, append — wire to key umenu)
 *   11: Scale umenu messages (clear, append — wire to scale umenu)
 *   12: Mode/key/scale selection value (format: "set mode drums" etc — wire to request_builder)
 *
 * Messages:
 *   anything      — parse JSON response and route to outlets
 *   select <int>  — look up preset_id by umenu index, output on outlet 4
 *   select_mode <int>  — look up mode_id by index
 *   select_key <int>   — look up key_id by index
 *   select_scale <int> — look up scale_id by index
 *   begin_generate — clear summary and set status to generating
 *   surprise [0-1] — emit SurpriseRequest JSON (preset_id + color)
 *
 * Canonical reference: Docs/JSON_Contract.md (GenerateResponse schema)
 */

autowatch = 1;
inlets = 1;
outlets = 13;

var preset_ids = [];
var preset_defaults = [];
var last_selected_idx = -1;
var mode_ids = [];
var key_ids = [];
var scale_ids = [];

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

  // Options response (has modes/keys/scales)
  if (resp.modes !== undefined && resp.keys !== undefined) {
    _handle_options(resp);
    return;
  }

  // GenerateResponse object (plan may be null on error)
  if (resp.surprise !== undefined) {
    _handle_surprise(resp);
    return;
  }

  // GenerateResponse object (plan may be null on error)
  if (
    resp.plan !== undefined ||
    resp.summary !== undefined ||
    resp.error !== undefined
  ) {
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
    // Only push defaults to dials when the preset actually changes,
    // not when the same index re-fires (e.g., during Generate flow)
    if (idx !== last_selected_idx) {
      outlet(5, JSON.stringify(preset_defaults[idx]));
      last_selected_idx = idx;
    }
    outlet(4, preset_ids[idx]);
  }
}

function begin_generate() {
  outlet(8, 1);
  outlet(1, " ");
  outlet(2, "generating...");
}

function surprise(color) {
  if (preset_ids.length === 0 || preset_defaults.length === 0) {
    outlet(2, "error: presets not loaded yet");
    return;
  }

  var idx = last_selected_idx >= 0 ? last_selected_idx : 0;
  var preset_id = preset_ids[idx];
  var width = 0.5;
  if (color !== undefined && color !== null && !isNaN(color)) {
    width = Math.max(0, Math.min(1, parseFloat(color)));
  }

  var req = {
    preset_id: preset_id,
    color: width,
  };

  // Preserve currently selected model override if present in request_builder path
  // by allowing caller to attach model through regular request flow if desired.

  outlet(8, 1);
  outlet(1, " ");
  outlet(2, "requesting surprise prompt...");
  outlet(7, JSON.stringify(req));
}

// --- Internal handlers ---

function _handle_generate(resp) {
  outlet(8, 0);
  if (!resp.ok) {
    outlet(1, " ");
    outlet(2, "error: " + (resp.error || "unknown error from service"));
    return;
  }

  var note_count = resp.plan.notes ? resp.plan.notes.length : 0;
  // Output rightmost first (Max convention)
  outlet(2, "done — " + note_count + " notes received");
  outlet(1, resp.summary || "");
  outlet(0, JSON.stringify(resp.plan));
}

function _handle_presets(arr) {
  preset_ids = [];
  preset_defaults = [];
  outlet(3, "clear");
  for (var i = 0; i < arr.length; i++) {
    preset_ids.push(arr[i].id);
    preset_defaults.push(arr[i].defaults || {});
    outlet(3, "append", arr[i].name);
  }
  outlet(8, 0);
  outlet(1, " ");
  outlet(2, "loaded " + arr.length + " presets");
}

function _handle_surprise(resp) {
  outlet(8, 0);
  if (!resp.ok || !resp.surprise) {
    outlet(2, "error: " + (resp.error || "failed to build surprise prompt"));
    return;
  }

  var surprise = resp.surprise;
  var prompt = surprise.prompt || "";
  var controls = surprise.controls || {};
  var sound = surprise.sound_suggestion || "";

  if (prompt) {
    outlet(6, prompt);
  }

  outlet(5, JSON.stringify(controls));

  var summary = resp.summary || "surprise prompt ready";
  if (sound) {
    summary += " | sound idea: " + sound;
  }
  outlet(1, summary);
  outlet(2, "surprise prompt ready");
}

function _handle_options(resp) {
  // Populate mode umenu (outlet 9)
  mode_ids = [];
  outlet(9, "clear");
  for (var i = 0; i < resp.modes.length; i++) {
    mode_ids.push(resp.modes[i].id);
    outlet(9, "append", resp.modes[i].name);
  }

  // Populate key umenu (outlet 10)
  key_ids = [];
  outlet(10, "clear");
  for (var i = 0; i < resp.keys.length; i++) {
    key_ids.push(resp.keys[i].id);
    outlet(10, "append", resp.keys[i].name);
  }

  // Populate scale umenu (outlet 11)
  scale_ids = [];
  outlet(11, "clear");
  for (var i = 0; i < resp.scales.length; i++) {
    scale_ids.push(resp.scales[i].id);
    outlet(11, "append", resp.scales[i].name);
  }

  outlet(
    2,
    "loaded options (" +
      resp.modes.length +
      " modes, " +
      resp.keys.length +
      " keys, " +
      resp.scales.length +
      " scales)",
  );
}

function select_mode(idx) {
  idx = Math.floor(idx);
  if (idx >= 0 && idx < mode_ids.length) {
    outlet(12, "set mode " + mode_ids[idx]);
  }
}

function select_key(idx) {
  idx = Math.floor(idx);
  if (idx >= 0 && idx < key_ids.length) {
    outlet(12, "set key " + key_ids[idx]);
  }
}

function select_scale(idx) {
  idx = Math.floor(idx);
  if (idx >= 0 && idx < scale_ids.length) {
    outlet(12, "set scale " + scale_ids[idx]);
  }
}
