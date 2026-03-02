/**
 * groove_http.js — Max/MSP `js` object for HTTP communication with the AI Groove Writer service.
 *
 * Outlets:
 *   0: JSON response from service (as a string for `dict.parse`)
 *   1: Status messages (bang on success, error strings on failure)
 *
 * Messages:
 *   generate <json_string>  — POST to /generate
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

    _post("/generate", json_str);
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
        // Success — send JSON string to outlet 0
        outlet(0, req.responseText);
        outlet(1, "bang");
    } else if (req.status === 0) {
        outlet(1, "error: cannot connect to service at " + _base_url());
    } else {
        // Try to extract error message from response
        var err_msg = "HTTP " + req.status;
        try {
            var parsed = JSON.parse(req.responseText);
            if (parsed.detail) {
                err_msg += ": " + parsed.detail;
            } else if (parsed.error) {
                err_msg += ": " + parsed.error;
            }
        } catch (e) {
            err_msg += ": " + req.responseText;
        }
        outlet(1, "error: " + err_msg);
    }
}
