/**
 * note_writer.js — Max/MSP `js` object for writing MIDI notes into Ableton Live clips.
 *
 * Uses the Live Object Model (LOM) via the Max `LiveAPI` object.
 *
 * Outlets:
 *   0: Status messages (strings)
 *
 * Messages:
 *   write <json_string>    — Parse a MidiPlan JSON and write notes to the highlighted clip
 *   clear                  — Remove all notes from the highlighted clip
 *
 * Canonical reference: Docs/Architecture.md, Docs/M4L_Build_Guide.md
 */

autowatch = 1;
inlets = 1;
outlets = 1;

// --- Public messages ---

function write() {
    var args = arrayfromargs(arguments);
    var json_str = args.join(" ");

    if (!json_str || json_str.length === 0) {
        outlet(0, "error: write requires a MidiPlan JSON string");
        return;
    }

    var plan;
    try {
        plan = JSON.parse(json_str);
    } catch (e) {
        outlet(0, "error: invalid JSON — " + e.message);
        return;
    }

    if (!plan.notes || !Array.isArray(plan.notes)) {
        outlet(0, "error: MidiPlan has no 'notes' array");
        return;
    }

    var clip = _get_highlighted_clip();
    if (!clip) return;

    _write_notes_to_clip(clip, plan);
}

function clear() {
    var clip = _get_highlighted_clip();
    if (!clip) return;

    _clear_clip_notes(clip);
    outlet(0, "cleared");
}

// --- Live API helpers ---

function _get_highlighted_clip() {
    // Navigate: live_set → view → highlighted_clip_slot → clip
    var slot_api = new LiveAPI("live_set view highlighted_clip_slot");

    if (!slot_api || !slot_api.id || slot_api.id === 0) {
        outlet(0, "error: no clip slot highlighted — click a clip slot in Ableton");
        return null;
    }

    // Check if the slot has a clip
    var has_clip = slot_api.get("has_clip");
    if (!has_clip || has_clip[0] === 0) {
        // Create a clip — we need the clip length
        // Default to 4 bars of 4/4 = 16 beats if we can't determine
        outlet(0, "info: no clip in slot, creating one...");

        // Get song tempo for reference
        var song_api = new LiveAPI("live_set");
        var tempo = song_api.get("tempo");

        // Create clip (length in beats)
        // We'll create it with a default length; the caller should ensure the clip exists
        slot_api.call("create_clip", 16.0);

        has_clip = slot_api.get("has_clip");
        if (!has_clip || has_clip[0] === 0) {
            outlet(0, "error: failed to create clip in slot");
            return null;
        }
    }

    var clip_api = new LiveAPI("live_set view highlighted_clip_slot clip");
    if (!clip_api || !clip_api.id || clip_api.id === 0) {
        outlet(0, "error: could not access clip");
        return null;
    }

    return clip_api;
}

function _clear_clip_notes(clip_api) {
    // remove_notes_extended(from_pitch, pitch_span, from_time, time_span)
    // Remove all notes: pitch 0-127, time 0 to clip end
    var clip_length = clip_api.get("length");
    if (clip_length && clip_length[0] > 0) {
        clip_api.call("remove_notes_extended", 0, 128, 0.0, clip_length[0]);
    }
}

function _write_notes_to_clip(clip_api, plan) {
    var notes = plan.notes;
    var note_count = notes.length;

    if (note_count === 0) {
        outlet(0, "warning: MidiPlan has 0 notes, nothing written");
        return;
    }

    // Calculate expected clip length from plan
    var expected_length = plan.bars * plan.time_sig_num * (4.0 / plan.time_sig_den);

    // Ensure clip is long enough
    var current_length = clip_api.get("length");
    if (current_length && current_length[0] < expected_length) {
        // Can't resize MIDI clips directly in all cases, but we try
        try {
            clip_api.set("loop_end", expected_length);
        } catch (e) {
            post("note_writer: could not resize clip: " + e.message + "\n");
        }
    }

    // Clear existing notes first
    _clear_clip_notes(clip_api);

    // Write notes using the notes API
    // add_new_notes format (Live 11+/12):
    //   clip.add_new_notes({ notes: [{...}, ...] })
    //
    // For Max js, we use the call-based approach:
    //   begin_add_notes()
    //   add_note(pitch, start, duration, velocity, mute)  — called for each note
    //   finish_add_notes()

    // Approach: Use remove_notes_extended + add_new_notes (Live 12 API)
    // Fallback: Use the legacy begin/add/finish pattern

    try {
        // Live 12 approach: build notes dict
        var notes_dict = { notes: [] };
        for (var i = 0; i < note_count; i++) {
            var n = notes[i];
            notes_dict.notes.push({
                pitch: n.pitch,
                start_time: n.start_beats,
                duration: n.dur_beats,
                velocity: n.vel / 127.0,  // Live API uses 0.0-1.0 velocity
                mute: n.mute === 1
            });
        }

        // Try the newer API
        clip_api.call("add_new_notes", JSON.stringify(notes_dict));
        outlet(0, "wrote " + note_count + " notes to clip");
    } catch (e) {
        // Fallback to legacy approach
        post("note_writer: add_new_notes failed, trying legacy approach: " + e.message + "\n");
        try {
            clip_api.call("select_all_notes");
            clip_api.call("replace_selected_notes");
            clip_api.call("notes", note_count);

            for (var j = 0; j < note_count; j++) {
                var note = notes[j];
                clip_api.call("note",
                    note.pitch,
                    note.start_beats.toFixed(4),
                    note.dur_beats.toFixed(4),
                    note.vel,
                    note.mute
                );
            }

            clip_api.call("done");
            outlet(0, "wrote " + note_count + " notes to clip (legacy)");
        } catch (e2) {
            outlet(0, "error: failed to write notes — " + e2.message);
        }
    }
}
