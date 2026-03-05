/**
 * groove_http.js — Max/MSP `js` object for HTTP communication with the AI Groove Writer service.
 *
 * Outlets:
 *   0: JSON response from service (as a string for `dict.parse`)
 *   1: Status messages (bang on success, error strings on failure)
 *
 * Messages:
 *   generate <json_string>  — POST to /generate
 *   refine <json_string>    — POST to /refine
 *   surprise <json_string>  — POST to /surprise
 *   config <json_string>    — POST to /config
 *   config_status           — GET /config/status
 *   shutdown_service        — POST to /shutdown
 *   health                  — GET /health
 *   presets                 — GET /presets
 *   usage                   — GET /usage
 *   port <number>           — set service port (default 8787)
 *   host <string>           — set service host (default 127.0.0.1)
 *
 * Canonical reference: Docs/Architecture.md, Docs/M4L_Build_Guide.md
 */

autowatch = 1;
inlets = 1;
outlets = 2;

// Configuration
var service_host = "127.0.0.1";
var service_port = 8787;

// --- Public messages ---

function host(h) {
  service_host = h;
  post("groove_http: host set to " + h + "\n");
}

function port(p) {
  service_port = p;
  post("groove_http: port set to " + p + "\n");
}

function health() {
  _get("/health");
}

function presets() {
  _get("/presets");
}

function usage() {
  _get("/usage");
}

function generate() {
  // Collect all arguments into a single JSON string
  var args = arrayfromargs(arguments);
  var json_str = args.join(" ");

  if (!json_str || json_str.length === 0) {
    outlet(1, "error: generate requires a JSON request string");
    return;
  }

  // Log the request to Max console for debugging
  post("groove_http: sending to /generate:\n");
  post(json_str + "\n");

  _post("/generate", json_str);
}

function surprise() {
  var args = arrayfromargs(arguments);
  var json_str = args.join(" ");

  if (!json_str || json_str.length === 0) {
    outlet(1, "error: surprise requires a JSON request string");
    return;
  }

  post("groove_http: sending to /surprise:\n");
  post(json_str + "\n");

  _post("/surprise", json_str);
}

function config() {
  var args = arrayfromargs(arguments);
  var json_str = args.join(" ");
  if (!json_str || json_str.length === 0) {
    outlet(1, "error: config requires a JSON request string");
    return;
  }
  _post("/config", json_str);
}

function config_status() {
  _get("/config/status");
}

function shutdown_service() {
  _post("/shutdown", "{}");
}

function refine() {
  var args = arrayfromargs(arguments);
  var json_str = args.join(" ");
  if (!json_str || json_str.length === 0) {
    outlet(1, "error: refine requires a JSON request string");
    return;
  }
  post("groove_http: sending to /refine:\n");
  post(json_str + "\n");
  _post("/refine", json_str);
}

// --- Internal helpers ---

function _base_url() {
  return "http://" + service_host + ":" + service_port;
}

function _get(path) {
  var url = _base_url() + path;
  var req = new XMLHttpRequest();

  req.open("GET", url);
  req.onreadystatechange = function () {
    if (req.readyState === 4) {
      _handle_response(req);
    }
  };

  try {
    outlet(1, "requesting " + path + "...");
    req.send();
  } catch (e) {
    outlet(1, "error: " + e.message);
  }
}

function _post(path, body) {
  var url = _base_url() + path;
  var req = new XMLHttpRequest();

  req.open("POST", url);
  req.setRequestHeader("Content-Type", "application/json");
  req.onreadystatechange = function () {
    if (req.readyState === 4) {
      _handle_response(req);
    }
  };

  try {
    outlet(1, "requesting " + path + "...");
    req.send(body);
  } catch (e) {
    outlet(1, "error: connection failed — is the service running?");
  }
}

function _handle_response(req) {
  if (req.status >= 200 && req.status < 300) {
    // Success — send JSON string to outlet 0, no bang on outlet 1
    // (response_router handles status messaging)
    outlet(0, req.responseText);
  } else if (req.status === 0) {
    outlet(1, "error: cannot connect to service at " + _base_url());
  } else {
    // Extract error details from response
    var err_msg = "HTTP " + req.status;
    try {
      var parsed = JSON.parse(req.responseText);
      if (parsed.detail) {
        // FastAPI 422 returns detail as an array — stringify it
        err_msg += ": " + JSON.stringify(parsed.detail);
      } else if (parsed.error) {
        err_msg += ": " + parsed.error;
      }
    } catch (e) {
      err_msg += ": " + req.responseText;
    }
    post("groove_http error: " + err_msg + "\n");
    outlet(1, "error: " + err_msg);
  }
}
