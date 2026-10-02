# FLOW: Traffic Signal Timing and Intersection Capacity Optimizer

**F**lexible **L**ane **O**ptimization via **W**ebster's method

A Python desktop app (CustomTkinter) that calculates optimal fixed-time signal timing for signalized intersections. Pick a phase model, enter your traffic data, and FLOW returns the optimal cycle length, effective green time, green time per phase, an oversaturation check, and a visual phase timeline.

> Course project for ENGG 1035 (Civil Engineering, Transportation Engineering). Submission: October 16, 2026.

**Status:** Phases 0 to 2 done (project setup, calculation engine, visualization engine). The GUI is next; follow the phase files in [docs/phases](docs/phases).

---

## Features

- Five phase models: 2-Phase, 3-Phase, 4-Phase, 6-Phase and 8-Phase
- Webster's method: flow ratios, total lost time, optimal cycle, effective green, green allocation
- Oversaturation warning when total flow ratio `Y >= 1.0`
- Phase timeline showing Green, Yellow/All-Red and Red for every phase across the cycle (graphical and text)
- Input validation with inline errors and a retry loop, so mistakes never crash the app or wipe your inputs
- Dark and light themes, app-style sidebar layout
- One-click copy of the full results

## Formulas

| Quantity | Formula |
|---|---|
| Phase flow ratio | `Yi = Vi / Si` |
| Total flow ratio | `Y = Y1 + Y2 + ... + Yn` |
| Total lost time | `L = n x li` |
| Webster optimal cycle | `Co = (1.5 L + 5) / (1 - Y)` |
| Total effective green | `Te = Co - L` |
| Phase green | `gi = (Yi / Y) x Te` |

`Vi` is the demand volume (veh/hr), `Si` the saturation flow rate (veh/hr), `n` the number of active phases and `li` the lost time per phase (amber + all-red, in seconds). The cycle is rounded **up** to the next 5 seconds, and phase greens are rounded to whole seconds so they always add up to `Te`.

## Supported phase models

| Model | Use case | Volume inputs |
|---|---|---|
| 2-Phase | Standard 4-way or simple T | NS Thru/Right, EW Thru/Right |
| 3-Phase | T-intersection with major left turn | Major Thru/Right, Major Protected Left, Minor Stem (all) |
| 4-Phase | Protected lefts or split phasing | NS Left, NS Thru/Right, EW Left, EW Thru/Right |
| 6-Phase | Major arterial with protected lefts | NB Left, SB Left, Arterial Thru/Right, Minor EB, Minor WB |
| 8-Phase | NEMA dual-ring, complex 4-way | Left and Thru/Right for NB, SB, EB and WB |

A phase with a volume of `0` is treated as inactive and left out of the cycle.

## Example

Input: 2-Phase, saturation flow 1900 veh/hr/lane, lost time 4 s, NS 850 veh/hr, EW 600 veh/hr.

```
--- VISUAL PHASE DIAGRAM (75-Second Cycle) ---
NS        : [=== G (39s) ===][Y/R: 4s][----- R (32s) -----]
EW        : [----- R (43s) -----][=== G (28s) ===][Y/R: 4s]
```

Y = 0.7632, L = 8 s, raw Co = 71.78 s, cycle = 75 s, Te = 67 s.

More cases, including the ones recomputed from the proposal, are in [docs/PRD.md](docs/PRD.md#11-acceptance-test-cases-recomputed).

## Getting started

Requirements: Python 3.11+ on Windows 10/11.

```bash
git clone <repo-url>
cd TRAFFIC-SIGNAL-TIMING-INTERSECTION-CAPACITY-OPTIMIZER
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Run the tests:

```bash
pip install -r requirements-dev.txt
pytest
```

## How to use

1. Choose a phase model on the first screen.
2. Enter the saturation flow rate and lost time per phase, then the traffic volume for each movement.
3. Press **Calculate**. If a field is invalid, it is highlighted with a message; fix it and press Calculate again.
4. If the app reports oversaturation (`Y >= 1.0`), lower the demand or change the phasing and try again.
5. Read the cycle, green times and timeline on the results screen. Use **Copy results**, **Edit inputs** or **New calculation**.

## Project structure

```
main.py                 app entry point
core/                   pure calculation logic, no GUI imports
  models.py             phase model definitions and result dataclasses
  validation.py         input parsing and validation
  calculator.py         Webster's method
  visualizer.py         timeline data and text diagram
ui/                     CustomTkinter interface
  theme.py              colors, fonts, spacing
  app.py                main window and screen switching
  screens/              model select, input form, results
  widgets/              reusable components
tests/                  pytest suites
docs/                   PRD and phase task files
```

## Documentation

- [Product Requirements Document](docs/PRD.md)
- Phase task files (follow in order):
  1. [Phase 0: Project setup](docs/phases/PHASE-0-setup.md)
  2. [Phase 1: Calculation engine](docs/phases/PHASE-1-calculation-engine.md)
  3. [Phase 2: Visualization engine](docs/phases/PHASE-2-visualization-engine.md)
  4. [Phase 3: GUI shell and theme](docs/phases/PHASE-3-gui-shell-and-theme.md)
  5. [Phase 4: Input screens and validation](docs/phases/PHASE-4-input-screens-and-validation.md)
  6. [Phase 5: Results and timeline view](docs/phases/PHASE-5-results-and-timeline-view.md)
  7. [Phase 6: Testing and polish](docs/phases/PHASE-6-testing-and-polish.md)
  8. [Phase 7: Packaging and submission](docs/phases/PHASE-7-packaging-and-submission.md)

## Code conventions

- Single-line `#` comments only, and only where the code is not obvious
- No decorative comments, no commented-out code, no multi-line string comments
- `core/` never imports `ui/`, `tkinter` or `customtkinter`
- Type hints on every function in `core/`

## Notes on the proposal's sample numbers

Only the first sample scenario (2-phase) reproduces exactly from Webster's formula. Scenarios 2 to 5 in the proposal list cycle lengths that do not follow from the formulas, so this project uses recomputed values (see the PRD, decision D1). Both the tests and the app follow the formulas.
