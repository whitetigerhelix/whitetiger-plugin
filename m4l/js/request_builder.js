/**
 * request_builder.js — Max/MSP `js` object for building the /generate request JSON.
 *
 * Replaces dict + dict.serialize with proper JSON serialization.
 * Accepts the same "set <key> <value>" messages as a Max dict.
 * Nested keys use colon syntax (e.g., "set controls:density 0.75").
 *
 * Outlets:
 *   0: JSON request string (for prepend generate → groove_http)
 *
 * Messages:
 *   set <key_path> <value>  — store a value (e.g., "set controls:density 0.75")
 *   set_json <key_path> <json_string> — store parsed JSON value (arrays/objects)
 *   remove <key_path>               — remove a field (e.g., "remove reference_pattern")
 *   bang                    — serialize and output the request as JSON
 *   clear                   — reset stored values
 *
 * Canonical reference: Docs/JSON_Contract.md (GenerateRequest schema)
 */

autowatch = 1;
inlets = 1;
outlets = 1;

var _REQUIRED_FIELDS = ["preset_id", "mode", "drum_map"];

var request = {};

function clear() {
  request = {};
  post("request_builder: cleared\n");
}

function remove() {
  var args = arrayfromargs(arguments);
  if (args.length < 1) return;
  var key_path = String(args[0]);
  var keys = key_path.split(":");
  var obj = request;
  for (var i = 0; i < keys.length - 1; i++) {
    if (typeof obj[keys[i]] !== "object" || obj[keys[i]] === null) return;
    obj = obj[keys[i]];
  }
  delete obj[keys[keys.length - 1]];
  post("request_builder: removed " + key_path + "\n");
}

function set() {
  var args = arrayfromargs(arguments);
  if (args.length < 2) return;

  var key_path = String(args[0]);
  var value;

  if (args.length === 2) {
    // Single value — try number, fall back to string
    var raw = args[1];
    var num = Number(raw);
    value = String(raw) !== "" && !isNaN(num) ? num : String(raw);
  } else {
    // Multiple values — join as string (e.g., multi-word prompt)
    value = args.slice(1).join(" ");
  }

  // Handle nested keys (colon-separated → nested objects)
  var keys = key_path.split(":");
  var obj = request;
  for (var i = 0; i < keys.length - 1; i++) {
    if (typeof obj[keys[i]] !== "object" || obj[keys[i]] === null) {
      obj[keys[i]] = {};
    }
    obj = obj[keys[i]];
  }
  obj[keys[keys.length - 1]] = value;
}

function set_json() {
  var args = arrayfromargs(arguments);
  if (args.length < 2) return;

  var key_path = String(args[0]);
  var raw_json = args.slice(1).join(" ");
  var value;

  try {
    value = JSON.parse(raw_json);
  } catch (e) {
    var msg =
      "request_builder: invalid JSON for set_json " + key_path + ": " + e;
    post(msg + "\n");
    error(msg + "\n");
    return;
  }

  var keys = key_path.split(":");
  var obj = request;
  for (var i = 0; i < keys.length - 1; i++) {
    if (typeof obj[keys[i]] !== "object" || obj[keys[i]] === null) {
      obj[keys[i]] = {};
    }
    obj = obj[keys[i]];
  }
  obj[keys[keys.length - 1]] = value;
}

function bang() {
  // Check required fields before sending
  var missing = [];
  for (var i = 0; i < _REQUIRED_FIELDS.length; i++) {
    if (request[_REQUIRED_FIELDS[i]] === undefined) {
      missing.push(_REQUIRED_FIELDS[i]);
    }
  }
  if (missing.length > 0) {
    var msg = "request_builder: missing required fields: " + missing.join(", ");
    post(msg + "\n");
    error(msg + "\n");
    return;
  }

  var json = JSON.stringify(request);
  post("request_builder: " + json + "\n");
  outlet(0, json);
}
