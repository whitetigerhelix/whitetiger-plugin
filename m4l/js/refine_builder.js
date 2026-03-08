/**
 * refine_builder.js — Builds the /refine request JSON from current clip notes + prompt text.
 *
 * Outlets:
 *   0: Refine request JSON string (for [prepend refine] → groove_http)
 *   1: Status messages
 *
 * Messages:
 *   notes <json_string>    — set the current clip notes (from clip_reader outlet 0)
 *   instruction <text>     — set the edit instruction (from prompt textedit)
 *   mode <string>          — set the mode (drums/bass/melody/chords)
 *   bars <number>          — set bar count
 *   bpm <number>           — set BPM
 *   key <string>           — set key (optional)
 *   scale <string>         — set scale (optional)
 *   preset_id <string>     — set preset_id (optional)
 *   bang                   — build and output the refine request JSON
 *
 * Canonical reference: Docs/Architecture.md
 */

autowatch = 1;
inlets = 1;
outlets = 2;

var _notes = [];
var _instruction = "";
var _mode = "drums";
var _bars = 8;
var _bpm = 130;
var _key = null;
var _scale = null;
var _preset_id = null;

function notes() {
  var args = arrayfromargs(arguments);
  var json_str = args.join(" ");
  try {
    _notes = JSON.parse(json_str);
    outlet(1, "loaded " + _notes.length + " notes for refine");
  } catch (e) {
    outlet(1, "error: invalid notes JSON");
    _notes = [];
  }
}

function instruction() {
  var args = arrayfromargs(arguments);
  _instruction = args.join(" ");
}

function mode(m) {
  _mode = String(m);
}

function bars(b) {
  _bars = Number(b) || 8;
}

function bpm(b) {
  _bpm = Number(b) || 130;
}

function key(k) {
  _key = String(k);
}

function scale(s) {
  _scale = String(s);
}

function preset_id(p) {
  _preset_id = String(p);
}

function bang() {
  if (_notes.length === 0) {
    outlet(1, "error: no notes loaded — read clip first");
    return;
  }
  if (!_instruction || _instruction.length === 0) {
    outlet(1, "error: no instruction — type what to change in prompt");
    return;
  }

  var req = {
    current_notes: _notes,
    instruction: _instruction,
    mode: _mode,
    clip: {
      bars: _bars,
      time_sig_num: 4,
      time_sig_den: 4,
      bpm: _bpm,
    },
  };

  if (_preset_id) req.preset_id = _preset_id;
  if (_key) req.key = _key;
  if (_scale) req.scale = _scale;

  var json = JSON.stringify(req);
  post("refine_builder: " + json.substring(0, 200) + "...\n");
  outlet(0, json);
}
