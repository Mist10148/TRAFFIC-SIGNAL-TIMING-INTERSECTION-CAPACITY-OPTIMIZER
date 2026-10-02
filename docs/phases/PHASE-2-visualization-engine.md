# Phase 2: Visualization Engine

**Goal:** turn a `TimingResult` into timeline data (for the GUI canvas) and a text diagram (for the monospace view and clipboard), all in `core/`.
**Prerequisites:** Phase 1 complete.
**Output:** `core/visualizer.py`, `tests/test_visualizer.py`.
**Read first:** [PRD](../PRD.md) section 11 (expected timeline) and the example output below.

---

## Timeline rules
- Phases run **sequentially** in model order (single ring). Phase `k` starts after phases `0..k-1` have finished their green plus lost time.
- Each phase row, left to right: `red_before` (if greater than 0), green, Y/R (lost time), `red_after` (if greater than 0).
- `red_before = sum(green_j + lost_time for j < k)`
- `red_after = cycle - (red_before + green_k + lost_time)`
- Because greens sum to `Te` (decision D4) and `n * li = L`, `red_after` is never negative. Lost time per phase is a whole number (validated in Phase 1), so no rounding is needed.

## Text format (must match exactly)

```
--- VISUAL PHASE DIAGRAM (75-Second Cycle) ---
NS        : [=== G (39s) ===][Y/R: 4s][----- R (32s) -----]
EW        : [----- R (43s) -----][=== G (28s) ===][Y/R: 4s]
```

- Header: `--- VISUAL PHASE DIAGRAM ({cycle}-Second Cycle) ---`
- Row label: phase code left-aligned in a column as wide as the longest code plus one space, then `: `.
- Green block: `[=== G ({g}s) ===]`
- Yellow/all-red block: `[Y/R: {l}s]`
- Red block: `[----- R ({r}s) -----]`

---

## Tasks

### 2.1 Branch
`git checkout -b phase-2-visualization-engine`

### 2.2 Data structures (`core/visualizer.py`)
1. `Segment` frozen dataclass: `kind: str` (`"R"`, `"G"` or `"YR"`), `start: int`, `duration: int` (seconds from cycle start).
2. `TimelineRow` frozen dataclass: `code: str`, `label: str`, `segments: tuple[Segment, ...]`.
3. `Timeline` frozen dataclass: `cycle: int`, `lost_time_per_phase: int`, `rows: tuple[TimelineRow, ...]`.

### 2.3 Build the timeline
Write `build_timeline(result: TimingResult, lost_time: float) -> Timeline`:
1. Raise `ValueError("Timeline requires a non-oversaturated result")` if `result.oversaturated`. The UI never calls it in that case; the test pins the behavior.
2. `yr = int(lost_time)`.
3. Loop over `result.phases` with a running `start = 0`.
4. For each phase create segments in order: red-before (only if duration > 0), green, Y/R, red-after (only if duration > 0). Every segment has an absolute `start`.
5. After the loop, assert for every row that the sum of segment durations equals `result.cycle` (use a plain `if` and `raise AssertionError`, not `assert`, so it survives `-O`).
6. Return `Timeline`.

### 2.4 Render text
Write `render_text(timeline: Timeline) -> str`:
1. Build the header line.
2. Compute `width = max(len(row.code) for row in rows) + 1`.
3. For each row concatenate `f"{row.code:<{width}}: "` and one block per segment using the formats above.
4. Join with `"\n"`. No trailing newline.

### 2.5 Summary text for clipboard
Write `render_report(result: TimingResult, timeline: Timeline, saturation_flow: float, lost_time: float) -> str` that returns a plain-text report with these sections in order:
1. `INPUTS`: model name, saturation flow, lost time per phase, one line per active phase with its volume.
2. `CALCULATED VARIABLES`: each `Yi` (4 decimals), total `Y` (4 decimals), `L`, active phase count.
3. `OUTPUT`: raw `Co` (2 decimals), cycle `C`, `Te`, each phase green.
4. `WARNINGS`: only if present.
5. The text diagram from `render_text`.

Use small helper functions per section and join the pieces with `"\n"`; do not use a long triple-quoted template.

### 2.6 Helpers for the GUI canvas
Add `scale_segments(row: TimelineRow, pixel_width: int, cycle: int) -> list[tuple[str, int, int]]` returning `(kind, x, width)` for each segment, where `x` and `width` are pixels. Rules:
1. `x = round(start / cycle * pixel_width)`.
2. `width = round((start + duration) / cycle * pixel_width) - x` so neighbors never overlap or leave gaps.
3. Minimum visible width is 2 px for any segment with duration greater than 0.

### 2.7 Tests (`tests/test_visualizer.py`)
1. Case 1 (NS 850, EW 600) `render_text` equals the exact two-row output shown at the top of this file.
2. 3-phase case 2 (greens 58, 22, 33, cycle 125): rows start with `MajThru`, `MajLeft`, `MinStem`; label column width is 8; the first row has no red-before block and the last has no red-after block.
3. For every acceptance case, each row's segment durations sum to the cycle and segments are contiguous (`next.start == prev.start + prev.duration`).
4. The single-active-phase case: one row, red segments absent.
5. `build_timeline` on an oversaturated result raises `ValueError`.
6. `scale_segments` for a 600 px canvas: total of widths equals 600, no overlaps, every nonzero segment has width of at least 2.
7. `render_report` contains the sections in the right order and the line `Cycle Length: 75 s` for case 1.

### 2.8 Verify
1. `pytest --cov=core`; coverage on `core/visualizer.py` must be 95 percent or more.
2. Manually print case 1 through 5 from a scratch script (kept outside the repo) and compare with the PRD.

### 2.9 Commit and merge
`git commit -m "Phase 2: timeline builder, text renderer and report"`, merge into `main`.

---

## Checklist
- [x] Text output for case 1 matches the spec character for character
- [x] Every row sums to the cycle for all acceptance cases
- [x] `build_timeline` rejects oversaturated results
- [x] Pixel scaling has no gaps or overlaps
- [x] `render_report` sections complete and ordered
- [x] Coverage 95 percent or more on `visualizer.py`
- [x] No GUI imports, single-line comments only

## Definition of done
Given any valid `TimingResult`, the app can get both drawable timeline data and a ready-to-print text diagram without touching the GUI.
