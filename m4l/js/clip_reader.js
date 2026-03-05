/**
 * clip_reader.js — Max/MSP `js` object that reads notes from the highlighted
 * Ableton clip and outputs them in the AI Groove Writer JSON format.
 *
 * Use this to capture a MIDI pattern you like as a reference example
 * for the LLM, or to read back generated patterns for refinement.
 *
 * Outlets:
 *   0: Notes JSON string (array of note objects matching MidiPlan.notes format)
 *   1: Status messages
 *   2: Clip name string (for display while reference is active)
 *
 * Messages:
 *   read       — read all notes from the highlighted clip
 *   bang       — same as read
 *
 * Output format:
 *   [
 *     {"pitch": 36, "start_beats": 0.0, "dur_beats": 0.25, "vel": 110, "mute": 0},
 *     ...
 *   ]
 *
 * Wire outlet 0 → [prepend set_json reference_pattern] → request_builder.js
 * to include as a reference in the generate request.
 *
 * Canonical reference: Docs/Architecture.md
 */

autowatch = 1;
inlets = 1;
outlets = 3;

function bang() {
  read();
}

function read() {
  try {
    var clip = _get_highlighted_clip();
    if (!clip) return;

    var clip_length = clip.get("length");
    if (!clip_length || Number(clip_length[0]) <= 0) {
      outlet(1, "error: clip has no length");
      outlet(0, "[]");
      return;
    }

    var length = Number(clip_length[0]);

    // get_notes_extended returns: notes count [pitch time duration velocity mute] ...
    var raw = clip.call("get_notes_extended", 0, 128, 0.0, length);

    if (!raw || raw.length === 0) {
      outlet(1, "clip is empty");
      outlet(0, "[]");
      return;
    }

    var notes = [];
    // Parse the raw note data from Live API
    // Format: "notes" count pitch1 time1 dur1 vel1 mute1 pitch2 ...
    var i = 0;

    // Skip "notes" keyword if present
    if (String(raw[0]) === "notes") {
      i = 1;
    }

    // Next is the count
    var count = 0;
    if (i < raw.length) {
      count = Number(raw[i]);
      i++;
    }

    // Then groups of 5: pitch, time, duration, velocity, mute
    for (var n = 0; n < count && i + 4 < raw.length; n++) {
      var pitch = Number(raw[i]);
      var start = Number(raw[i + 1]);
      var dur = Number(raw[i + 2]);
      var vel = Number(raw[i + 3]);
      var mute = Number(raw[i + 4]);
      i += 5;

      notes.push({
        pitch: pitch,
        start_beats: parseFloat(start.toFixed(4)),
        dur_beats: parseFloat(dur.toFixed(4)),
        vel: vel,
        mute: mute,
      });
    }

    // Sort by start time
    notes.sort(function (a, b) {
      return a.start_beats - b.start_beats;
    });

    outlet(1, "read " + notes.length + " notes from clip");
    outlet(0, JSON.stringify(notes));

    // Output clip name on outlet 2
    var clip_name = "";
    try {
      var raw_name = clip.get("name");
      if (raw_name) clip_name = String(raw_name);
    } catch (e) {}
    outlet(2, clip_name || "unnamed clip");
  } catch (e) {
    outlet(1, "error: " + e.message);
    outlet(0, "[]");
  }
}

function _get_highlighted_clip() {
  var slot_api = new LiveAPI("live_set view highlighted_clip_slot");
  if (!slot_api || !slot_api.id || slot_api.id === 0) {
    outlet(1, "error: no clip slot highlighted");
    return null;
  }

  var has_clip = slot_api.get("has_clip");
  if (!has_clip || has_clip[0] === 0) {
    outlet(1, "error: no clip in selected slot");
    return null;
  }

  var clip_api = new LiveAPI("live_set view highlighted_clip_slot clip");
  if (!clip_api || !clip_api.id || clip_api.id === 0) {
    outlet(1, "error: could not access clip");
    return null;
  }

  return clip_api;
}
