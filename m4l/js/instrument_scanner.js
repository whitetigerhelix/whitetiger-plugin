/**
 * instrument_scanner.js — Max/MSP `js` object that scans the current track's
 * instrument (Drum Rack or Instrument Rack) and outputs instrument context JSON.
 *
 * Outlets:
 *   0: instrument context JSON string (array of pad/instrument objects)
 *   1: Status messages
 *
 * Messages:
 *   scan       — scan the track containing this device
 *   bang       — same as scan
 *
 * Output format (Drum Rack):
 *   [
 *     {"pitch": 36, "name": "Kick 808", "sample": "808_Kick.wav"},
 *     {"pitch": 38, "name": "Snare Vinyl", "sample": "Vinyl_Snare.aif"},
 *     ...
 *   ]
 *
 * Output format (non-Drum Rack or no instrument):
 *   [] (empty array)
 *
 * Wire outlet 0 → [prepend set_json instrument_context] → request_builder.js
 *
 * Canonical reference: Docs/Architecture.md
 */

autowatch = 1;
inlets = 1;
outlets = 2;

function bang() {
  scan();
}

function scan() {
  var context = [];

  try {
    // Get the track this device lives on
    var track_api = new LiveAPI("this_device canonical_parent");
    if (!track_api || !track_api.id || track_api.id === 0) {
      outlet(1, "no track found");
      outlet(0, "[]");
      return;
    }

    // Look through devices on this track for a Drum Rack
    var device_count = track_api.getcount("devices");
    var drum_rack = null;

    for (var i = 0; i < device_count; i++) {
      var dev_api = new LiveAPI("this_device canonical_parent devices " + i);
      if (!dev_api || !dev_api.id || dev_api.id === 0) continue;

      var dev_class = dev_api.get("class_name");
      if (dev_class && String(dev_class) === "DrumGroupDevice") {
        drum_rack = dev_api;
        break;
      }
    }

    if (!drum_rack) {
      outlet(1, "no Drum Rack found on track");
      outlet(0, "[]");
      return;
    }

    // Scan drum pads
    var pad_count = drum_rack.getcount("drum_pads");
    for (var p = 0; p < pad_count; p++) {
      var pad_api = new LiveAPI(drum_rack.path + " drum_pads " + p);
      if (!pad_api || !pad_api.id || pad_api.id === 0) continue;

      var note = pad_api.get("note");
      var pad_name = pad_api.get("name");

      if (!note || Number(note) < 0) continue;

      var pitch = Number(note);
      var name = String(pad_name || "Pad " + pitch);

      // Try to get sample name from the first chain's first device
      var sample = "";
      try {
        var chain_count = pad_api.getcount("chains");
        if (chain_count > 0) {
          var chain_api = new LiveAPI(pad_api.path + " chains 0");
          if (chain_api && chain_api.id) {
            // Chain name often reflects the sample/sound
            var chain_name = chain_api.get("name");
            if (chain_name && String(chain_name).length > 0) {
              name = String(chain_name);
            }

            // Try to find a Simpler device and get sample path
            var chain_dev_count = chain_api.getcount("devices");
            for (var d = 0; d < chain_dev_count; d++) {
              var inner_dev = new LiveAPI(chain_api.path + " devices " + d);
              if (!inner_dev || !inner_dev.id) continue;
              var inner_class = inner_dev.get("class_name");
              if (String(inner_class) === "OriginalSimpler") {
                try {
                  var sample_api = new LiveAPI(inner_dev.path + " sample");
                  if (sample_api && sample_api.id) {
                    var file_path = sample_api.get("file_path");
                    if (file_path && String(file_path).length > 0) {
                      // Extract just the filename
                      var full = String(file_path);
                      var slash = full.lastIndexOf("/");
                      var bslash = full.lastIndexOf("\\");
                      var last_sep = Math.max(slash, bslash);
                      sample =
                        last_sep >= 0 ? full.substring(last_sep + 1) : full;
                    }
                  }
                } catch (e) {
                  // Sample API may not be available
                }
              }
            }
          }
        }
      } catch (e) {
        // Chain traversal failed, continue with what we have
      }

      // Only include pads that have content (chains)
      var has_chains = false;
      try {
        has_chains = pad_api.getcount("chains") > 0;
      } catch (e) {}

      if (has_chains) {
        var entry = { pitch: pitch, name: name };
        if (sample.length > 0) {
          entry.sample = sample;
        }
        context.push(entry);
      }
    }

    outlet(1, "scanned " + context.length + " pads");
    outlet(0, JSON.stringify(context));
  } catch (e) {
    outlet(1, "error: " + e.message);
    outlet(0, "[]");
  }
}
