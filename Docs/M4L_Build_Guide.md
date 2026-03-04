# M4L Build Guide — AI Groove Writer Device

Step-by-step instructions for building the Max for Live MIDI device. Since `.amxd` files require the Max visual editor, this guide walks you through creating and wiring the device manually.

> **Prerequisites:** Ableton Live 12.3.5+ with Max for Live, the Python service running (`cd service && .venv/Scripts/python.exe -m uvicorn app:app --host 127.0.0.1 --port 8787`)

---

## 1. Create the Device

1. In Ableton, drag a blank **Max MIDI Effect** onto a MIDI track
2. Click the wrench icon to open the Max editor
3. Save the device as `AI Groove Writer.amxd` in the `m4l/patches/` folder

---

## 2. Add the JS Objects

You need three `js` objects, each pointing to a file in `m4l/js/`:

### groove_http (HTTP client)

1. Create a `js` object: type `js groove_http.js` in a new object box
2. This object has **2 outlets**:
   - Outlet 0 (left): JSON response string
   - Outlet 1 (right): Status messages (bang on success, error strings on failure)

### note_writer (clip writer)

1. Create a `js` object: type `js note_writer.js`
2. This object has **1 outlet**:
   - Outlet 0: Status messages

### post_process (swing / humanize / jitter)

1. Create a `js` object: type `js post_process.js`
2. This object has **2 outlets**:
   - Outlet 0 (left): Processed MidiPlan JSON string
   - Outlet 1 (right): Status messages

> **Tip:** If Max can't find the JS files, set the search path: Options → File Preferences → add the `m4l/js/` folder.

---

## 3. UI Controls

Add the following UI elements in the Max editor. Suggested layout (top to bottom):

### Row 1: Prompt & Preset
| Element | Max Object | Notes |
|---|---|---|
| Prompt | `textedit` | Multi-line text input for user prompt |
| Preset | `umenu` | Dropdown — populate from `/presets` endpoint |
| Generate button | `live.button` or `button` | Triggers the generate flow |

### Row 2: Controls (Knobs)
| Element | Max Object | Range | Default |
|---|---|---|---|
| Density | `live.dial` | 0.0–1.0 | 0.75 |
| Complexity | `live.dial` | 0.0–1.0 | 0.65 |
| Swing | `live.dial` | 0.0–1.0 | 0.35 |
| Humanize (ms) | `live.dial` | 0–25 | 8 |
| Vel Jitter | `live.dial` | 0–15 | 6 |

### Row 3: Info Display
| Element | Max Object | Notes |
|---|---|---|
| Status | `comment` or `textedit` (read-only) | Shows "generating...", "wrote 24 notes", errors |
| Usage info | `comment` | Optional — shows token count / cost |

### Row 4: Utility
| Element | Max Object | Notes |
|---|---|---|
| Seed | `live.numbox` | Integer, default 12345 |
| BPM display | `live.numbox` | Read from Live's tempo |
| Health check | `button` + `comment` | Ping the service |

---

## 4. Wiring Diagram

Here's how to connect everything. Read this as a signal flow from top to bottom:

```
┌──────────────┐
│  [Generate]  │  (button click)
│   button     │
└──────┬───────┘
       │ bang
       ▼
┌──────────────────────────────────────────────┐
│  [Build Request]                              │
│  Collect prompt, preset_id, clip info,        │
│  controls, seed into a JSON string            │
│  Use: dict → dict.serialize or sprintf/join   │
└──────┬───────────────────────────────────────┘
       │ JSON string
       ▼
┌──────────────────────────────────────────────┐
│  js groove_http.js                            │
│  inlet: "generate <json>"                     │
│  outlet 0: response JSON ──────────┐          │
│  outlet 1: status messages ──────┐ │          │
└──────────────────────────────────┼─┼──────────┘
                                   │ │
              ┌────────────────────┘ │
              ▼                      ▼
     [Status display]         ┌─────────────────┐
                              │  Parse response  │
                              │  Extract "plan"  │
                              │  from JSON       │
                              │  (use dict)      │
                              └────────┬─────────┘
                                       │ plan JSON
                                       ▼
                              ┌──────────────────────────────────┐
                              │  js post_process.js               │
                              │  inlet: "process <json> ..."      │
                              │  (also receives swing, humanize,  │
                              │   vel_jitter, bpm, seed values)   │
                              │  outlet 0: processed JSON ──┐     │
                              │  outlet 1: status ──────┐   │     │
                              └─────────────────────────┼───┼─────┘
                                                        │   │
                                     ┌──────────────────┘   │
                                     ▼                      ▼
                              [Status display]    ┌──────────────────┐
                                                  │  js note_writer  │
                                                  │  inlet: "write   │
                                                  │    <json>"       │
                                                  │  outlet 0:       │
                                                  │    status ───┐   │
                                                  └──────────────┼───┘
                                                                 │
                                                                 ▼
                                                         [Status display]
```

---

## 5. Building the Request JSON

Before sending to `groove_http`, you need to build a JSON object matching the `GenerateRequest` schema. Use Max's `dict` object:

```
dict → set prompt "atmospheric breaks with ghost snares"
dict → set preset_id "breaks_atmos_130"
dict → set mode "drums"
dict → set clip::bars 8
dict → set clip::time_sig_num 4
dict → set clip::time_sig_den 4
dict → set clip::bpm 130.0
dict → set controls::density 0.75
dict → set controls::complexity 0.65
dict → set controls::swing 0.35
dict → set controls::humanize_ms 8
dict → set controls::velocity_jitter 6
dict → set seed 42
dict → set drum_map "gm"
```

Then use `dict.serialize` to get the JSON string, and send it to `groove_http` as `generate <json_string>`.

---

## 6. Reading Clip Info from Live

To auto-fill BPM and time signature from the current Live set:

```max
[live.object "live_set"] → get tempo    → [BPM display]
[live.object "live_set"] → get signature_numerator   → [time_sig_num]
[live.object "live_set"] → get signature_denominator → [time_sig_den]
```

For clip bar count, you can either:
- Let the user set it manually (numbox)
- Read from highlighted clip: `[live.object "live_set view highlighted_clip_slot clip"] → get length` (returns beats, divide by time_sig_num for bars)

---

## 7. Populating the Preset Dropdown

On device load (use `loadbang`):

1. Send `presets` message to `groove_http`
2. Parse the response JSON array
3. For each preset, add to `umenu`: `append <preset_name>`
4. Store the preset IDs in a `coll` object mapped to umenu indices

---

## 8. Extracting the Plan from Response

The `/generate` response looks like:
```json
{
  "ok": true,
  "summary": "24 notes, 8 bars | azure:gpt-4o | 450+800 tokens | $0.0091",
  "plan": { "version": 1, "mode": "drums", "bars": 8, ... , "notes": [...] },
  "error": null
}
```

Use a `dict` object to parse the response:
1. `dict.parse <response_json>`
2. Check `dict.get ok` — if false, display `dict.get error` in status
3. If ok, `dict.get plan` → serialize the plan sub-dict → send to `post_process`
4. Display `dict.get summary` in the status area

---

## 9. Testing Each Piece

### Test groove_http
1. Start the Python service (mock mode): `SERVICE_MOCK=1 .venv/Scripts/python.exe -m uvicorn app:app --port 8787`
2. In Max, send `health` to `groove_http` — should get `{"ok": true}` on outlet 0
3. Send `presets` — should get a JSON array of 5 presets
4. Send `generate {"prompt":"test","preset_id":"breaks_atmos_130","clip":{"bars":4,"bpm":130}}` — should get a full response

### Test note_writer
1. Highlight an empty clip slot in Ableton
2. Send a hardcoded MidiPlan JSON to `note_writer` with `write` message:
   ```
   write {"version":1,"mode":"drums","bars":1,"time_sig_num":4,"time_sig_den":4,"notes":[{"pitch":36,"start_beats":0,"dur_beats":0.5,"vel":100,"mute":0},{"pitch":42,"start_beats":0.5,"dur_beats":0.25,"vel":80,"mute":0}]}
   ```
3. You should see notes appear in the clip

### Test post_process
1. Send a MidiPlan JSON to `post_process` with `process` message
2. Check that outlet 0 produces modified JSON
3. Vary swing/humanize/vel_jitter parameters and verify notes change

---

## 10. Complete Signal Flow Summary

```
User clicks [Generate]
  → Build request JSON from UI controls
  → groove_http.generate(json)
  → HTTP POST to Python service
  → Service builds LLM prompt, calls GPT-4o (or returns mock)
  → Service validates/clamps response
  → Returns GenerateResponse JSON
  → groove_http outlet 0 → parse response
  → Extract plan → post_process.process(plan, swing, humanize, vel_jitter, bpm, seed)
  → post_process outlet 0 → note_writer.write(processed_plan)
  → Notes written to Ableton clip
  → Status messages displayed throughout
```

---

## 11. Preset Defaults → Control Dials

When the user selects a preset from the umenu, the control dials should update to that preset's defaults. This uses `response_router.js` outlet 5 and `preset_defaults_unpacker.js`.

### Add the unpacker JS object

1. Create a `js` object: type `js preset_defaults_unpacker.js`
2. This object has **5 outlets**, one per control:
   - Outlet 0: density (float, 0–1)
   - Outlet 1: complexity (float, 0–1)
   - Outlet 2: swing (float, 0–1)
   - Outlet 3: humanize_ms (float, 0–25)
   - Outlet 4: velocity_jitter (int, 0–15)

### Wiring

```
response_router.js outlet 5
         │
         │ JSON string: {"density":0.75,"complexity":0.65,...}
         ▼
  js preset_defaults_unpacker.js
    │       │       │       │       │
    │out0   │out1   │out2   │out3   │out4
    ▼       ▼       ▼       ▼       ▼
 Density Complx  Swing   Hum ms  Vjit
 dial    dial    dial    dial    dial
```

Each outlet sends a number directly to the corresponding `live.dial`. The dial updates its display and also fires its output, which flows through the existing `set controls:density $1` (etc.) messages into `request_builder`, keeping the request in sync automatically.

> **Note:** `response_router.js` now has **6 outlets** (was 5). After saving the JS file, you may need to close and reopen the device (or delete and re-create the `js response_router.js` object) for Max to pick up the new outlet count.

---

## 12. Variation & Randomize Seed Buttons

These buttons let users quickly iterate on grooves. No new JS files needed — `request_builder.js` already supports `set variation <N>` and `set seed <N>`.

### Next Variation button

Increments the variation counter by 1. Uses `[i]` to break the feedback loop — the Variation numbox stores its value silently in `[i]`'s right inlet, and the button bang triggers `[i]`'s left inlet to read it.

```
[Next Var button]
       │ bang
       ▼
     [i]  ←─── right inlet: Variation numbox output (stores silently)
       │ outputs stored value on bang
       ▼
     [+ 1]
       │
       ▼
   Variation numbox        ← sets display AND fires output
       │
       ├──→ [i] right inlet (stores new value for next click)
       │
       ▼
   [set variation $1]
       │
       ▼
   request_builder
```

**Critical:** The Variation numbox output must go to `[i]`'s **right** inlet (silent store), NOT to `[+ 1]` or `[i]`'s left inlet. This prevents a feedback loop where each increment triggers another.

### Randomize Seed button

Picks a random seed (0–99999) and sets it:

```
[Rand Seed button]
       │ bang
       ▼
 [random 100000]                 ← generates 0–99999
       │
       ▼
   Seed numbox                   ← updates display, fires output
       │
       ▼
   [set seed $1]
       │
       ▼
   request_builder
```

### Optional: Auto-generate after button press

If you want Generate to fire automatically after changing seed or variation, wire `delay 50` → `request_builder` bang inlet (NOT `prepend generate` — that bypasses JSON serialization and causes HTTP 422). This is optional — you may prefer to click Generate manually after adjusting seed/variation.

---

## Tips

- **File paths:** If Max can't find `groove_http.js` etc., add `m4l/js/` to Max's search path (Options → File Preferences)
- **Debugging:** Use `post()` in JS files to print to the Max console (View → Max Console)
- **Live API access:** The `js` objects use `LiveAPI` which only works when the device is in a Live set, not in standalone Max
- **Save often:** Save the `.amxd` device frequently. Max can crash during development.
- **Presentation mode:** Design the user-facing layout in Presentation Mode (View → Presentation). Lock the patcher when done.
