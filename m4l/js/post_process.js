/**
 * post_process.js — Max/MSP `js` object for swing, humanize, and velocity jitter.
 *
 * Post-processing is done in Max (NOT in the LLM) so it's instant, repeatable,
 * and controllable via knobs/sliders.
 *
 * Outlets:
 *   0: Processed MidiPlan JSON string (for note_writer)
 *   1: Status messages
 *
 * Messages:
 *   process <json_string> <swing> <humanize_ms> <vel_jitter> <bpm> <seed>
 *     — Apply post-processing chain to a MidiPlan
 *
 *   swing <0-1>         — Set swing amount (0 = straight, 1 = full triplet)
 *   humanize <0-25>     — Set humanize amount in ms
 *   velocity_jitter <0-15> — Set velocity jitter range
 *   bpm <40-240>        — Set BPM (for ms-to-beats conversion)
 *   seed <int>          — Set RNG seed
 *
 * Processing chain:
 *   1. Swing — off-beat 8ths get full delay, 16ths get half delay
 *   2. Humanize — seeded RNG timing jitter (ms → beats)
 *   3. Velocity jitter — seeded RNG +/- offset, clamped 1–127
 *
 * Canonical reference: Docs/Architecture.md (post-processing pipeline)
 */

autowatch = 1;
inlets = 1;
outlets = 2;

// Default parameters (can be set via messages)
var param_swing = 0.35;
var param_humanize_ms = 8;
var param_vel_jitter = 6;
var param_bpm = 130;
var param_seed = 12345;

// --- Parameter setters ---

function swing(val) {
    param_swing = Math.max(0, Math.min(1, val));
    outlet(1, "swing: " + param_swing);
}

function humanize(val) {
    param_humanize_ms = Math.max(0, Math.min(25, val));
    outlet(1, "humanize: " + param_humanize_ms + "ms");
}

function velocity_jitter(val) {
    param_vel_jitter = Math.max(0, Math.min(15, val));
    outlet(1, "vel_jitter: " + param_vel_jitter);
}

function bpm(val) {
    param_bpm = Math.max(40, Math.min(240, val));
    outlet(1, "bpm: " + param_bpm);
}

function seed(val) {
    param_seed = val;
    outlet(1, "seed: " + param_seed);
}

// --- Main processing ---

function process() {
    var args = arrayfromargs(arguments);

    // First argument is the JSON plan string
    // Remaining optional args override: swing, humanize_ms, vel_jitter, bpm, seed
    if (args.length === 0) {
        outlet(1, "error: process requires at least a JSON string argument");
        return;
    }

    // Find where the JSON ends and numeric args begin
    // The JSON string may contain spaces, so we need to find the full JSON first
    var full_str = args.join(" ");
    var json_end = _find_json_end(full_str);

    if (json_end < 0) {
        outlet(1, "error: could not find JSON object in input");
        return;
    }

    var json_str = full_str.substring(0, json_end + 1);
    var remaining = full_str.substring(json_end + 1).trim();

    var plan;
    try {
        plan = JSON.parse(json_str);
    } catch (e) {
        outlet(1, "error: invalid JSON — " + e.message);
        return;
    }

    // Parse optional override args
    if (remaining.length > 0) {
        var parts = remaining.split(/\s+/);
        if (parts.length >= 1 && !isNaN(parts[0])) param_swing = parseFloat(parts[0]);
        if (parts.length >= 2 && !isNaN(parts[1])) param_humanize_ms = parseFloat(parts[1]);
        if (parts.length >= 3 && !isNaN(parts[2])) param_vel_jitter = parseInt(parts[2]);
        if (parts.length >= 4 && !isNaN(parts[3])) param_bpm = parseFloat(parts[3]);
        if (parts.length >= 5 && !isNaN(parts[4])) param_seed = parseInt(parts[4]);
    }

    if (!plan.notes || !Array.isArray(plan.notes)) {
        outlet(1, "error: MidiPlan has no 'notes' array");
        return;
    }

    // Deep copy notes for processing
    var notes = [];
    for (var i = 0; i < plan.notes.length; i++) {
        var n = plan.notes[i];
        notes.push({
            pitch: n.pitch,
            start_beats: n.start_beats,
            dur_beats: n.dur_beats,
            vel: n.vel,
            mute: n.mute || 0
        });
    }

    // Initialize seeded RNG
    var rng = _seeded_rng(param_seed);

    // 1. Apply swing
    if (param_swing > 0) {
        notes = _apply_swing(notes, param_swing);
    }

    // 2. Apply humanize (timing jitter)
    if (param_humanize_ms > 0) {
        notes = _apply_humanize(notes, param_humanize_ms, param_bpm, rng);
    }

    // 3. Apply velocity jitter
    if (param_vel_jitter > 0) {
        notes = _apply_velocity_jitter(notes, param_vel_jitter, rng);
    }

    // Rebuild plan with processed notes
    plan.notes = notes;
    var result = JSON.stringify(plan);

    outlet(0, result);
    outlet(1, "processed " + notes.length + " notes (sw=" + param_swing +
           " hum=" + param_humanize_ms + "ms vj=" + param_vel_jitter + ")");
}

// --- Seeded RNG (xorshift32) ---

function _seeded_rng(s) {
    // Simple xorshift32 PRNG for repeatable results
    var state = s || 1;
    if (state === 0) state = 1;

    return {
        next: function () {
            state ^= state << 13;
            state ^= state >> 17;
            state ^= state << 5;
            // Return value in [0, 1)
            return (state >>> 0) / 4294967296;
        },
        // Return value in [-1, 1)
        next_signed: function () {
            return this.next() * 2 - 1;
        }
    };
}

// --- Swing ---

function _apply_swing(notes, amount) {
    // Swing delays off-beat positions:
    //   8th note off-beats (0.5, 1.5, 2.5, ...) get full swing delay
    //   16th note off-beats (0.25, 0.75, 1.25, ...) get half swing delay
    //
    // Max swing delay for 8ths: move up to 1/3 of an 8th note (triplet feel)
    var max_delay_8th = (0.5 / 3) * amount;  // in beats
    var max_delay_16th = max_delay_8th * 0.5;

    for (var i = 0; i < notes.length; i++) {
        var start = notes[i].start_beats;
        var pos_in_beat = start % 1.0;

        // Check if on an 8th-note off-beat (within tolerance)
        if (Math.abs(pos_in_beat - 0.5) < 0.01) {
            notes[i].start_beats += max_delay_8th;
        }
        // Check if on a 16th-note off-beat
        else if (Math.abs(pos_in_beat - 0.25) < 0.01 || Math.abs(pos_in_beat - 0.75) < 0.01) {
            notes[i].start_beats += max_delay_16th;
        }
    }

    return notes;
}

// --- Humanize (timing jitter) ---

function _apply_humanize(notes, humanize_ms, current_bpm, rng) {
    // Convert ms to beats: beats = ms * (bpm / 60000)
    var ms_to_beats = current_bpm / 60000.0;
    var max_jitter_beats = humanize_ms * ms_to_beats;

    for (var i = 0; i < notes.length; i++) {
        var jitter = rng.next_signed() * max_jitter_beats;
        notes[i].start_beats = Math.max(0, notes[i].start_beats + jitter);
    }

    return notes;
}

// --- Velocity jitter ---

function _apply_velocity_jitter(notes, jitter_range, rng) {
    for (var i = 0; i < notes.length; i++) {
        var offset = Math.round(rng.next_signed() * jitter_range);
        var new_vel = notes[i].vel + offset;
        // Clamp to 1–127
        notes[i].vel = Math.max(1, Math.min(127, new_vel));
    }

    return notes;
}

// --- JSON parsing helper ---

function _find_json_end(text) {
    var start = text.indexOf("{");
    if (start < 0) return -1;

    var depth = 0;
    var in_string = false;
    var escape_next = false;

    for (var i = start; i < text.length; i++) {
        var ch = text.charAt(i);

        if (escape_next) {
            escape_next = false;
            continue;
        }

        if (ch === "\\") {
            escape_next = true;
            continue;
        }

        if (ch === '"') {
            in_string = !in_string;
            continue;
        }

        if (in_string) continue;

        if (ch === "{") depth++;
        else if (ch === "}") {
            depth--;
            if (depth === 0) return i;
        }
    }

    return -1;
}
