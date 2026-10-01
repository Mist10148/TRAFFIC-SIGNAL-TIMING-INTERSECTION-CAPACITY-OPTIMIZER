# Phase 6: Testing and Polish

**Goal:** prove correctness, harden edge cases, and make the app feel finished.
**Prerequisites:** Phases 1 to 5 merged.
**Output:** complete test suite, manual QA record, UI polish, README screenshots.
**Read first:** [PRD](../PRD.md) sections 8 (NFRs), 11 (cases and edge cases) and 16 (definition of done).

---

## Tasks

### 6.1 Branch
`git checkout -b phase-6-testing-and-polish`

### 6.2 Automated test audit
1. Run `pytest --cov=core --cov-report=term-missing`.
2. Required: overall `core/` coverage of 90 percent or more (NFR-06). For every uncovered line listed, either add a test or delete dead code.
3. Confirm test files exist: `test_calculator.py`, `test_validation.py`, `test_visualizer.py`.

### 6.3 Add an end-to-end engine test (`tests/test_pipeline.py`)
1. Parametrized over the six acceptance cases: raw strings -> `validate_inputs` -> `compute_timing` -> `build_timeline` -> `render_text`.
2. Assert the final cycle, `Te` and greens, and that every row sums to the cycle.
3. Case 6 asserts the pipeline stops at `oversaturated` and `build_timeline` is never called.

### 6.4 Property-style invariants (seeded random, no extra dependency)
In `tests/test_invariants.py` run 500 random valid inputs per model (seed 1035; saturation flow 1200 to 2200; lost time 2 to 6; volumes drawn so `Y < 0.95`):
1. `sum(greens) == Te`.
2. `cycle % 5 == 0` and `cycle >= raw_cycle`.
3. `cycle - raw_cycle < 5`.
4. Every green is at least 0.
5. Every timeline row sums to the cycle.
6. Increasing any one volume never decreases `Y` or the raw cycle.

### 6.5 Edge-case matrix (add to the tests, then verify by hand in the GUI)
| Case | Expected |
|---|---|
| All volumes 0 | Validation error, no calculation |
| Single active phase | One row, `Y = V / S`, green equals `Te` |
| `Y = 0.99` | Calculation works, cycle above 150 s, impractical warning |
| `Y = 1.0` exactly | Oversaturation |
| Volume `0.0001` | Accepted; tiny green triggers minimum-green warning |
| Volume with comma `1,5` | Parsed as 1.5 |
| Leading/trailing spaces | Trimmed |
| `1e3` | Accepted as 1000 (scientific notation parses) |
| `nan`, `inf`, `-inf` | "Enter a number" |
| Very long text (200 chars) | "Enter a number", no crash |
| Lost time `3.5` | "Must be a whole number of seconds" |

### 6.6 Manual QA pass (record pass/fail in `docs/QA.md`)
Create `docs/QA.md` as a table with columns: Test, Steps, Expected, Result, Date. Cover:
1. Full flow for each of the five models using "Fill example".
2. Both retry loops (invalid input, oversaturation) from Phase 4.10.
3. Appearance Light, Dark, System, and switching while on each screen.
4. Window sizes: 960 x 640, 1120 x 720, 1600 x 900, maximized.
5. Windows scaling 100, 125 and 150 percent.
6. Keyboard-only run: Tab through the form, Enter to calculate, Esc back.
7. Copy results then paste into Notepad.
8. Rapid repeated Calculate clicks (no duplicate screens, no crashes).
9. Closing from every screen exits cleanly.

### 6.7 UI polish pass
Work through this list and tick each item:
1. Consistent spacing: all cards use `PAD_M` inside and `PAD_L` between; no ad hoc numbers.
2. Alignment: labels, units and values on a shared grid; numbers right-aligned in the mono font.
3. Hover and pressed states on every button and card; cursor changes to a hand on clickable cards.
4. Focus ring visible on all inputs and buttons.
5. Empty states: Results screen without data redirects instead of showing blanks.
6. Smooth screen switch: no flash of the wrong screen; hide the window content until the first layout finishes.
7. Window icon: create a 256 px `.ico` (three stacked signal lights) in `assets/flow.ico` and set it with `iconbitmap`.
8. Text: no truncated labels at the minimum window size; long phase labels wrap.
9. Contrast: check muted text on `surface` in both themes for at least 4.5:1.
10. Error text is never color-only (message plus icon letter).

### 6.8 Performance and stability
1. Time `compute_timing` for a 8-phase case: below 5 ms.
2. Switching screens 50 times in a row does not grow memory noticeably (watch Task Manager).
3. Resize dragging stays smooth (debounced redraw).

### 6.9 Code hygiene check
1. Search the repo for `"""`: remove any that are not required output text.
2. Search for `# ===`, `# ---`, and commented-out code: remove.
3. Search `core/` for `tkinter` and `customtkinter`: none.
4. Search `ui/` for hex colors (`#[0-9A-Fa-f]{6}`) outside `theme.py`: none.
5. Run `python -m compileall core ui` to catch syntax issues.
6. Remove unused imports and unused variables.

### 6.10 Screenshots for the README
1. Capture, at 1120 x 720 in dark mode: Model Select, Input Form (filled with example), Results (top), Results (timeline). Add one light-mode Results shot.
2. Save in `docs/images/` as `model-select.png`, `inputs.png`, `results.png`, `timeline.png`, `results-light.png`.
3. Add a "Screenshots" section to the README with these images.

### 6.11 Fix, retest, commit
1. Fix every failure found; for each bug, add a regression test when it is in `core/`.
2. Re-run `pytest --cov=core` and re-run the QA table.
3. `git commit -m "Phase 6: tests, QA pass and UI polish"`, merge into `main`.

---

## Checklist
- [ ] `core/` coverage is 90 percent or more
- [ ] Pipeline and invariant tests pass
- [ ] Edge-case matrix passes in tests and by hand
- [ ] `docs/QA.md` filled with results
- [ ] Polish list 6.7 complete
- [ ] Hygiene searches in 6.9 clean
- [ ] Screenshots added to README
- [ ] No known crashes

## Definition of done
All automated tests pass, the manual QA table is all green, and nothing in the app looks unfinished.
