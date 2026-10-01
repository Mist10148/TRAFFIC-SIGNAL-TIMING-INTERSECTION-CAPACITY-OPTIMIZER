# Phase 4: Input Screens and Validation

**Goal:** a complete Input Form: global inputs, dynamic per-model volume fields, live feedback, inline validation and the retry loops (invalid input, oversaturation).
**Prerequisites:** Phase 1 (validation and calculator), Phase 3 (shell and `Banner`).
**Output:** `ui/widgets/labeled_entry.py`, `ui/widgets/y_meter.py`, `ui/screens/input_form.py`, wiring in `ui/app.py`.
**Read first:** [PRD](../PRD.md) sections 5, 7 (FR-02 to FR-08, FR-12, FR-14, FR-15) and 9 (user flow).

---

## Tasks

### 4.1 Branch
`git checkout -b phase-4-input-screens-and-validation`

### 4.2 `LabeledEntry` widget (`ui/widgets/labeled_entry.py`)
1. Layout (vertical): label row (label text left, muted unit right), `CTkEntry` (height 38, radius 8), hint or error line below (11 pt).
2. Constructor: `LabeledEntry(parent, label, unit, hint, placeholder="0")`.
3. Methods:
   - `get() -> str` returns the raw text.
   - `set(text: str)` replaces the text.
   - `set_error(message: str)`: border and message in `signal_red`, message replaces the hint.
   - `clear_error()`: restore border and hint.
   - `bind_change(callback)`: fires on every key release.
4. On focus-in, select all text. On focus-out, if the text parses as a number, normalize it (strip spaces, `850.0` stays as typed, no auto-reformatting beyond trimming).
5. Typing a character that can never be part of a number (anything other than digits, one `.` or `,`, and a leading `-`) is flagged immediately with `"Numbers only"` but still allowed to be typed, so the user sees why Calculate will fail.

### 4.3 `YMeter` widget (`ui/widgets/y_meter.py`)
1. A horizontal bar, height 14, radius 7, track in `surface_alt`.
2. `set(value: float)` fills the bar from 0 to 1.0 (clamp the fill at 1.0). Color by value: below 0.70 `signal_green`, 0.70 to 0.85 `signal_amber`, 0.85 up to 1.0 amber-to-red tint (use `signal_red` at 0.95 and above), 1.0 or more `signal_red`.
3. Caption left: `Y = 0.7632`; caption right: `Capacity 100 percent` marker at the end. Add a small tick at 0.85 labeled "heavy".
4. `set_error()` shows `Y = --` with an empty bar when the inputs are not yet valid.

### 4.4 `InputFormScreen` layout (`ui/screens/input_form.py`)
1. Header: breadcrumb "Model / Inputs", title "{model.name} inputs", a "Change model" text button that calls `app.show("model")`.
2. Body is a scrollable frame with two cards side by side (stacked below 1000 px width):
   - **Card A, "Intersection parameters":** `LabeledEntry` for Saturation Flow Rate (unit `veh/hr/lane`, hint `Typical 1800 to 1900`, default placeholder `1900`) and Lost Time per Phase (unit `s`, hint `Amber + all-red, whole seconds`, placeholder `4`).
   - **Card B, "Traffic volumes":** one `LabeledEntry` per `PhaseDef` of the model in a 2-column grid, label = `PhaseDef.label`, unit `veh/hr`, hint = `PhaseDef.hint`.
3. Footer card: `YMeter`, a count line "{n} of {total} phases active", a `Banner` (hidden by default), and the buttons: primary "Calculate" (accent), secondary "Reset", text "Fill example".
4. Pressing Enter in any field triggers Calculate.
5. Tab order follows reading order: saturation flow, lost time, then volumes row by row, then buttons.

### 4.5 Build and rebuild fields
1. `build_fields(model)` creates the volume entries from `MODELS[model_key].phases` and stores them in `self.entries: dict[str, LabeledEntry]` keyed by `saturation_flow`, `lost_time` and each phase code.
2. `on_show()` (called by `app.show("inputs")`): if `app.model_key` changed since the last build, destroy the volume entries and rebuild; restore text from `app.form_values` for every key that still exists (global inputs survive a model change, FR-03).
3. Every change event writes the current text of all entries into `app.form_values`, so nothing is lost when navigating away.

### 4.6 Live feedback
1. On every change, try to parse all volume fields and the saturation flow with `parse_number`. If saturation flow is greater than 0 and at least one volume parses, compute `Y = sum(max(v, 0) / S)` over parseable volumes and call `YMeter.set(Y)`. Otherwise `YMeter.set_error()`.
2. Update the "{n} of {total} phases active" line from parseable volumes greater than 0.
3. This preview does not show errors; errors only appear on Calculate or on the "Numbers only" rule.

### 4.7 Calculate with the retry loop
Implement `on_calculate()`:
1. Clear all field errors and hide the banner.
2. Collect raw strings: `raw = {key: entry.get() for key, entry in self.entries.items()}`.
3. Call `validate_inputs(app.model_key, raw)`.
4. **Invalid path (retry loop 1):** if errors:
   - call `set_error(message)` on each offending entry (for the `volumes` error, mark all volume entries),
   - show an `error` banner: `"Please fix {k} field(s) to continue."`,
   - move focus to the first offending field,
   - return. Nothing else changes; every value the user typed stays.
5. Call `compute_timing(timing_input)`.
6. **Oversaturated path (retry loop 2):** if `result.oversaturated`:
   - show an `error` banner with `result.message` plus the top two phases by flow ratio: `"Largest demand: {code} ({Yi:.3f}), {code} ({Yi:.3f}). Reduce volumes or add capacity, then try again."`,
   - set the `YMeter` to the real `Y` (it shows full red),
   - outline the two largest-demand fields with `signal_amber`,
   - return without navigating.
7. **Success path:** store `app.timing_input` and `app.result`, show non-blocking warnings (impractical cycle, short green) as a `warning` banner only if `Y` is valid, then call `app.show("results")`. The warnings are repeated on the results screen (Phase 5).
8. Wrap the body of `on_calculate` in a narrow `try/except (ValueError, ZeroDivisionError)` that shows an `error` banner `"Unexpected input problem. Check the values and try again."`. This is a safety net only; validation should already catch everything.

### 4.8 Reset and Fill example
1. **Reset:** clear all entries, clear errors, hide banner, reset `YMeter`, clear `app.form_values`.
2. **Fill example:** fill saturation flow `1900`, lost time `4` and the matching acceptance-case volumes for the current model (PRD section 11):
   - 2-phase: `NS 850`, `EW 600`
   - 3-phase: `800`, `300`, `450`
   - 4-phase: `200`, `700`, `150`, `600`
   - 6-phase: `NBL 250`, `SBL 0`, `ArtThru 900`, `MinEB 500`, `MinWB 0`
   - 8-phase: `NBL 150`, `SBT 600`, `EBL 150`, `WBT 500`, all others `0`
   Keep these example dicts in `ui/screens/input_form.py` as `EXAMPLES` (UI convenience, not part of `core/`).

### 4.9 Sidebar and navigation rules
1. The "Inputs" sidebar button is enabled once a model is chosen.
2. After a successful calculation the "Results" button enables; editing any input afterward marks the old result as stale: disable "Results" until the next Calculate.

### 4.10 Manual test script (run all, record results in the PR description)
1. Empty form -> Calculate -> every field says "Required", banner counts fields, focus on the first field.
2. Type `abc` in NS -> "Numbers only" appears immediately -> Calculate -> "Enter a number".
3. Saturation flow `0`, `-5`, `5000` -> three different messages.
4. Lost time `3.5` -> "Must be a whole number of seconds"; `0` -> "Must be at least 1 s".
5. All volumes `0` -> single banner message, all volume fields marked.
6. 2-phase `NS 1200`, `EW 800` -> oversaturation banner, `Y = 1.0526`, both fields amber, no navigation; change `NS` to `850`, `EW` to `600`, Calculate -> goes to Results (retry loop works).
7. Switch model from 2-phase to 4-phase and back: saturation flow and lost time kept, volumes follow the model.
8. Comma decimal `1,5` accepted in a volume field.
9. Resize narrower than 1000 px: cards stack, no clipped fields.

### 4.11 Commit and merge
`git commit -m "Phase 4: input form, live Y meter and validation retry loops"`, merge into `main`.

---

## Checklist
- [ ] Global inputs plus per-model volumes render for all five models
- [ ] Global values survive model change; volumes rebuild per model
- [ ] Every validation message from Phase 1 appears next to the right field
- [ ] Invalid input never clears the form (retry loop 1)
- [ ] Oversaturation keeps the user on the form with values intact (retry loop 2)
- [ ] Live Y meter updates and changes color by threshold
- [ ] Enter key submits; Tab order is sensible
- [ ] Fill example, Reset and Change model work
- [ ] All items in 4.10 pass
- [ ] Single-line comments only; no color hex outside `theme.py`

## Definition of done
A user can enter data for any model, see precise errors, correct them and reach the results screen without the app ever crashing or discarding their input.
