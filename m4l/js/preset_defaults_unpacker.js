/**
 * preset_defaults_unpacker.js — Max/MSP `js` object that unpacks preset defaults JSON
 * into individual outlet values for control dials.
 *
 * Receives a JSON string from response_router.js outlet 5 and outputs
 * each control value on a separate outlet, right-to-left (Max convention).
 *
 * Outlets:
 *   0: density       (float, 0–1)
 *   1: complexity    (float, 0–1)
 *   2: swing         (float, 0–1)
 *   3: humanize_ms   (float, 0–25)
 *   4: velocity_jitter (int, 0–15)
 *
 * Messages:
 *   anything  — parse JSON defaults string, output values on outlets
 *
 * Canonical reference: Docs/Architecture.md, Docs/JSON_Contract.md
 */

autowatch = 1;
inlets = 1;
outlets = 5;

function anything() {
    var str = arrayfromargs(messagename, arguments).join(" ");

    // Find start of JSON object
    var start = str.indexOf("{");
    if (start > 0) str = str.substring(start);

    var defaults;
    try {
        defaults = JSON.parse(str);
    } catch (e) {
        post("preset_defaults_unpacker: invalid JSON — " + e.message + "\n");
        return;
    }

    // Output right-to-left (Max convention: rightmost outlet fires first)
    if (defaults.velocity_jitter !== undefined) outlet(4, defaults.velocity_jitter);
    if (defaults.humanize_ms !== undefined)     outlet(3, defaults.humanize_ms);
    if (defaults.swing !== undefined)           outlet(2, defaults.swing);
    if (defaults.complexity !== undefined)      outlet(1, defaults.complexity);
    if (defaults.density !== undefined)         outlet(0, defaults.density);

    post("preset_defaults_unpacker: applied defaults\n");
}
