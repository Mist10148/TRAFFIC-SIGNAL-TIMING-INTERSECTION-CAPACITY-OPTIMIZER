# Product Requirements Document (PRD)

**Product:** FLOW, Flexible Lane Optimization via Webster's method
**Full name:** Traffic Signal Timing and Intersection Capacity Optimizer
**Course:** ENGG 1035, Civil Engineering (Transportation Engineering)
**Target submission:** October 16, 2026
**Platform:** Desktop app, Python 3.11+ with CustomTkinter
**Status:** Planning (docs first, no code yet)

---

## 1. Overview

FLOW is a desktop application that computes optimal fixed-time traffic signal timing for a signalized intersection using Webster's method. The user picks a phase model (2, 3, 4, 6 or 8 phase), enters the saturation flow rate, the lost time per phase and the demand volumes, and the app returns:

- flow ratio per phase and for the whole intersection,
- total lost time,
- Webster's optimal cycle length (rounded up to the next 5 seconds),
- total effective green time,
- green time per phase,
- an oversaturation warning when demand exceeds capacity (Y >= 1.0),
- a phase timeline diagram (Green, Yellow/All-Red, Red) across the full cycle.

The earlier prototype was a console script. This version is a polished, app-like GUI. The calculation and visualization logic stays UI-independent so it can be tested without a window.

## 2. Goals and non-goals

### Goals
1. Correct Webster calculations for all five phase models.
2. A sleek, modern, app-like interface (dark and light themes).
3. Friendly input handling with a visible retry loop: bad input never crashes the app and never loses what the user already typed.
4. Clear results: cycle, effective green, per-phase greens, and a readable timeline.
5. Clean, testable code: a pure `core/` package and a thin `ui/` package.

### Non-goals (v1)
- Actuated or adaptive signal control.
- Pedestrian phases, minimum-green checks beyond a warning, coordination between intersections.
- Saving or loading projects from disk (export of results as text is in scope, project files are not).
- Per-lane geometry. Saturation flow is entered once and applied to every phase (see section 6, decision D5).

## 3. Target users

| User | Need |
|---|---|
| ENGG 1035 student | Check hand calculations, understand how each formula feeds the next. |
| Instructor or grader | Run the sample scenarios and see correct, well-presented output. |
| Casual transportation learner | Try different demand levels and see how the cycle responds. |

## 4. Governing formulas

| Quantity | Formula | Notes |
|---|---|---|
| Phase flow ratio | `Yi = Vi / Si` | `Vi` demand (veh/hr), `Si` saturation flow (veh/hr) |
| Total flow ratio | `Y = Y1 + Y2 + ... + Yn` | Sum over all active phases |
| Total lost time | `L = n x li` | `n` active phases, `li` = amber + all-red per phase (s) |
| Optimal cycle | `Co = (1.5 L + 5) / (1 - Y)` | Valid only when `Y < 1.0` |
| Practical cycle | `C = ceil(Co / 5) x 5` | Round up to the next 5 s |
| Effective green | `Te = C - L` | Usable green per cycle |
| Phase green | `gi = (Yi / Y) x Te` | Rounded to whole seconds, see D4 |

The app displays the **practical cycle** `C` as "Optimal Cycle Length (Co)" and also shows the raw Webster value `Co` in the detail view.

## 5. Phase models and input fields

### 5.1 Global inputs (all models)
| Field | Variable | Unit | Rule |
|---|---|---|---|
| Saturation flow rate | `S` | veh/hr/lane | number, `0 < S <= 2400` |
| Lost time per phase (amber + all-red) | `li` | seconds | whole number, `1 <= li <= 12` (signals run on whole seconds, so `L` is always whole) |

### 5.2 Per-model volume fields
All volumes are in veh/hr, number, `0 <= V <= 5000`. At least one volume per model must be greater than 0.

| Model | Description | Phase code : label |
|---|---|---|
| 2-Phase | Standard 4-way or simple T | `NS` : North-South Thru and Right, `EW` : East-West Thru and Right |
| 3-Phase | T-intersection with major left turn | `MajThru` : Major Street Thru and Right, `MajLeft` : Major Street Protected Left, `MinStem` : Minor Street (Stem) All Movements |
| 4-Phase | Protected lefts or split phasing | `NSL` : NS Protected Left, `NST` : NS Thru and Right, `EWL` : EW Protected Left, `EWT` : EW Thru and Right |
| 6-Phase | Major arterial with protected lefts, minor street permitted | `NBL` : Arterial NB Protected Left, `SBL` : Arterial SB Protected Left, `ArtThru` : Arterial NB and SB Thru and Right, `MinEB` : Minor EB All Movements, `MinWB` : Minor WB All Movements |
| 8-Phase | NEMA dual-ring, complex 4-way | `NBL`, `NBT`, `SBL`, `SBT`, `EBL`, `EBT`, `WBL`, `WBT` (Protected Left and Thru and Right for each approach) |

The 6-phase model has five volume fields (as in the proposal). Its name refers to the six-phase NEMA layout, but the calculation uses the five demand movements the user supplies.

### 5.3 Active phases
A phase whose volume is `0` is **inactive**. Inactive phases are dropped from the cycle: they get no green, no lost time (`n` counts only active phases) and no timeline row. This is what lets the proposal's Scenario 4 (6-phase) and Scenario 5 (8-phase), which supply only some movements, produce `L = 12 s` and `L = 16 s` as written. The results screen states how many phases are active.

## 6. Decisions and issues found in the source material

**D1. Sample cases 2 to 5 do not match the formulas.** Using Webster's formula exactly as written in the proposal, only Scenario 1 matches. The sample cycle lengths for Scenarios 2 to 5 (100, 120, 110, 85 s) are not reproducible, and the sample flow ratios are rounded to two decimals. Recomputed values are in section 11 and are the ones the tests use. The proposal's sample numbers are treated as illustrative only.

| Scenario | Sample cycle | Webster (rounded sample Y) | Webster (exact Y) |
|---|---|---|---|
| 1, 2-phase | 75 s | 17 / 0.23 = 73.9 -> 75 s | 71.8 -> 75 s (match) |
| 2, 3-phase | 100 s | 23 / 0.18 = 127.8 -> 130 s | 124.9 -> 125 s |
| 3, 4-phase | 120 s | 29 / 0.12 = 241.7 -> 245 s | 220.4 -> 225 s |
| 4, 6-phase | 110 s | 23 / 0.14 = 164.3 -> 165 s | 174.8 -> 175 s |
| 5, 8-phase | 85 s | 29 / 0.26 = 111.5 -> 115 s | 110.2 -> 115 s |

**D2. Lost time:** `L = n x li` with `n` the number of active phases (4 phases at 4 s = 16 s). Matches the proposal.

**D3. Cycle rounding:** round **up** to the next 5 s, as in the example engine code. If the practical cycle exceeds **150 s**, the app shows a non-blocking "impractical cycle" warning (Y is close to 1.0, consider adding lanes or phases). The value itself is not capped.

**D4. Green rounding:** plain `round()` per phase can make the greens plus lost time differ from the cycle, which breaks the timeline (negative red time). The app uses **largest-remainder rounding**: floor every `gi`, then give the leftover whole seconds to the phases with the largest fractional parts, so that `sum(gi) == Te` exactly.

**D5. Saturation flow "per lane":** the proposal has no lane count. v1 treats `S` as the saturation flow applying to each phase's critical movement. An optional "lanes per phase" input is a stretch goal (section 13).

**D6. Oversaturation:** when `Y >= 1.0`, Webster's formula is invalid. The app shows the warning, does not compute cycle or greens, keeps the user on the input form with their values intact, and highlights the phases with the largest flow ratios so the user can lower the demand and retry.

**D7. Minimum green:** if any computed green is below **5 s**, show a non-blocking warning. No change to the numbers in v1.

## 7. Functional requirements

| ID | Requirement |
|---|---|
| FR-01 | The user can choose a phase model: 2, 3, 4, 6 or 8 phase. |
| FR-02 | The input form shows the global inputs plus the volume fields of the chosen model, with labels, units and hints. |
| FR-03 | Switching model replaces the volume fields; global inputs are kept. |
| FR-04 | Every field is validated on Calculate (and non-numeric characters are flagged on edit). Errors appear inline next to the field and as a summary banner. |
| FR-05 | Invalid input never closes the app or clears the form. The user fixes the field and presses Calculate again (retry loop). |
| FR-06 | The app computes `Yi`, `Y`, `L` for the active phases. |
| FR-07 | If `Y >= 1.0` the app shows the Oversaturation Warning and stops (D6). |
| FR-08 | Otherwise the app computes raw `Co`, practical cycle `C`, `Te` and each `gi` (D3, D4). |
| FR-09 | The results screen shows input echo, calculated variables, outputs and the phase timeline. |
| FR-10 | The timeline is shown as a graphical bar view and as the monospace text view; both come from the same data. |
| FR-11 | The user can copy the full results as plain text. |
| FR-12 | "Edit inputs" returns to the form with values kept. "New calculation" returns to model selection with a cleared form. |
| FR-13 | Light and dark appearance, switchable from the sidebar; defaults to the system setting. |
| FR-14 | A Y-meter (0 to 1.0) visualizes how close the intersection is to capacity. |
| FR-15 | Warnings (impractical cycle, short green) are shown without blocking the results. |

## 8. Non-functional requirements

| ID | Requirement |
|---|---|
| NFR-01 | Python 3.11+, only third-party dependency at runtime is `customtkinter`. |
| NFR-02 | A calculation completes in under 50 ms; the UI never freezes. |
| NFR-03 | `core/` has no import of `tkinter` or `customtkinter`. |
| NFR-04 | Minimum window 960 x 640, default 1120 x 720; layout adapts when resized. |
| NFR-05 | Text contrast meets WCAG AA in both themes. Signal colors are never the only carrier of meaning (G, Y/R, R letters are always printed). |
| NFR-06 | Unit tests cover calculator, validation and visualizer, at least 90 percent line coverage on `core/`. |
| NFR-07 | Runs on Windows 10/11; builds to a single `.exe` with PyInstaller. |

## 9. User flow

```
[Launch]
   -> [Model Select]  (2 / 3 / 4 / 6 / 8 phase cards)
   -> [Input Form]    (global inputs + model volumes)
   -> Calculate
        invalid input    -> inline errors + banner -> user edits -> Calculate again   (retry loop)
        Y >= 1.0         -> Oversaturation warning, stay on form -> user edits -> Calculate again
        valid, Y < 1.0   -> [Results]  (cards, table, timeline)
   -> [Results]
        Edit inputs      -> back to Input Form, values kept
        New calculation  -> back to Model Select
        Copy results     -> clipboard
```

The original proposal flowchart has no loop. The retry loops above are the required addition ("dapat may looping/try again").

## 10. GUI requirements

### 10.1 Look and feel
- Framework: CustomTkinter, single window, left sidebar plus content area, card-based layout, rounded corners (12 px cards, 8 px inputs).
- Dark first, with a light theme. Tokens live in one place (`ui/theme.py`).
- Typography: a clean sans-serif UI font (Segoe UI Variable / Segoe UI fallback) and a monospace font (Cascadia Mono / Consolas fallback) for the text timeline and numeric readouts.

| Token | Dark | Light |
|---|---|---|
| `bg` | `#0E1116` | `#F4F6F9` |
| `surface` | `#161B22` | `#FFFFFF` |
| `surface_alt` | `#1F2630` | `#EAEEF3` |
| `border` | `#2A3340` | `#D5DCE5` |
| `text` | `#E6EDF3` | `#1B2430` |
| `text_muted` | `#8B98A9` | `#5C6B7F` |
| `accent` | `#2DD4BF` | `#0F9F8E` |
| `signal_green` | `#22C55E` | `#16A34A` |
| `signal_amber` | `#F59E0B` | `#D97706` |
| `signal_red` | `#EF4444` | `#DC2626` |

### 10.2 Screens
1. **Model Select**: five cards (2, 3, 4, 6, 8 phase), each with a name, a one-line description and a tiny phase diagram icon drawn on a canvas.
2. **Input Form**: left column global inputs, right column the model's volume fields in a two-column grid; live "Y so far" meter updates as valid numbers are typed; primary button "Calculate", secondary "Reset".
3. **Results**: four stat cards (Cycle `C`, Effective Green `Te`, Total Flow Ratio `Y`, Total Lost Time `L`), a per-phase table (phase, volume, `Yi`, green, share of `Te`), the graphical timeline, the text timeline in a monospace box, buttons "Copy results", "Edit inputs", "New calculation".
4. **Oversaturation state**: an error banner on the Input Form with the actual `Y`, a short explanation and the top contributing phases.

### 10.3 Components (`ui/widgets/`)
`StatCard`, `LabeledEntry` (label, unit, hint, inline error), `Banner` (info, warning, error), `PhaseTable`, `TimelineCanvas`, `YMeter`, `ModelCard`.

## 11. Acceptance test cases (recomputed)

All cases use `S = 1900` veh/hr/lane and `li = 4 s`. Values below are from the exact formulas with largest-remainder rounding. Flow ratios are shown to 4 decimals.

| # | Model | Volumes (veh/hr) | `Y` | `L` | Raw `Co` | `C` | `Te` | Greens (s) |
|---|---|---|---|---|---|---|---|---|
| 1 | 2-phase | NS 850, EW 600 | 0.7632 | 8 | 71.78 | 75 | 67 | NS 39, EW 28 |
| 2 | 3-phase | MajThru 800, MajLeft 300, MinStem 450 | 0.8158 | 12 | 124.86 | 125 | 113 | 58, 22, 33 |
| 3 | 4-phase | NSL 200, NST 700, EWL 150, EWT 600 | 0.8684 | 16 | 220.40 | 225 | 209 | 25, 89, 19, 76 |
| 4 | 6-phase | NBL 250, SBL 0, ArtThru 900, MinEB 500, MinWB 0 | 0.8684 | 12 (3 active) | 174.80 | 175 | 163 | NBL 25, ArtThru 89, MinEB 49 |
| 5 | 8-phase | NBL 150, SBT 600, EBL 150, WBT 500, others 0 | 0.7368 | 16 (4 active) | 110.20 | 115 | 99 | 11, 42, 11, 35 |
| 6 | 2-phase | NS 1200, EW 800 | 1.0526 | n/a | n/a | n/a | n/a | Oversaturation warning, no timing |

Edge cases the tests must cover: all volumes 0 (error), a single active phase, `Y` just below 1.0 (for example 0.99, cycle above 150 s triggers the impractical warning), non-numeric text, negative values, empty fields, decimal inputs, very large inputs, `Y` exactly 1.0.

Expected text timeline for case 1:

```
--- VISUAL PHASE DIAGRAM (75-Second Cycle) ---
NS        : [=== G (39s) ===][Y/R: 4s][----- R (32s) -----]
EW        : [----- R (43s) -----][=== G (28s) ===][Y/R: 4s]
```

## 12. Architecture

```
main.py                      entry point, launches FlowApp
core/
  models.py                  PhaseDef, PhaseModel, MODELS registry, TimingInput, PhaseResult, TimingResult
  validation.py              parse_number, validate_inputs -> list[FieldError]
  calculator.py              flow_ratio, total_lost_time, webster_cycle, round_cycle, apportion_greens, compute_timing
  visualizer.py              build_timeline -> list[TimelineRow], render_text -> str
ui/
  theme.py                   color tokens, fonts, spacing, apply_theme
  app.py                     FlowApp (CTk), screen switching, shared state
  screens/
    model_select.py          ModelSelectScreen
    input_form.py            InputFormScreen
    results.py               ResultsScreen
  widgets/                   StatCard, LabeledEntry, Banner, PhaseTable, TimelineCanvas, YMeter, ModelCard
tests/
  test_calculator.py  test_validation.py  test_visualizer.py
docs/
  PRD.md  phases/PHASE-*.md
```

Data flow: `InputFormScreen` collects strings -> `validation.validate_inputs` -> `calculator.compute_timing` -> `TimingResult` -> `ResultsScreen`, which calls `visualizer.build_timeline` / `render_text`. `core/` only exchanges plain dataclasses and strings.

## 13. Stretch goals (only after all phases are done)
- Lanes-per-phase input (`Si = S x lanes`).
- Minimum-green enforcement with re-apportioning.
- Export results as PDF or PNG of the timeline.
- Compare two scenarios side by side.
- Delay and level-of-service estimate.

## 14. Code conventions
- Comments: single-line `#` comments only, and only where the code is not obvious. No decorative banners, no divider lines, no commented-out code.
- No multi-line string comments. Triple-quoted strings only where truly required (for example a multi-line text template that is real output).
- Short docstring is not needed; use clear names instead.
- `snake_case` for functions and variables, `PascalCase` for classes, `UPPER_CASE` for constants.
- Type hints on every function signature in `core/`.
- One screen or widget per file. No logic in `main.py` beyond starting the app.
- `core/` never imports from `ui/`.

## 15. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Sample numbers in the proposal disagree with the formula | D1: recomputed table, explained in the README and in the presentation. |
| Rounded greens break the timeline | D4: largest-remainder rounding plus a test that `sum(g) == Te`. |
| CustomTkinter scaling issues on high-DPI displays | Use CTk scaling, test at 100 percent and 150 percent. |
| Timeline too wide for long cycles (for example 225 s) | Canvas scales proportionally; text view wraps in a horizontally scrollable box. |
| Time before submission | Phases are ordered so the engine and a basic GUI are done first; polish and stretch goals are last. |

## 16. Definition of done
1. All acceptance cases in section 11 pass as automated tests.
2. All screens in section 10.2 work in both themes with no crashes on invalid input.
3. Retry loops (invalid input, oversaturation) verified by hand.
4. README is accurate: install, run, usage, screenshots.
5. A one-file Windows build runs on a clean machine.
