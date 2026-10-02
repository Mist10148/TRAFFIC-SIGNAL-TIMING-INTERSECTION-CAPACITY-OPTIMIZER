# Phase 5: Results and Timeline View

**Goal:** the Results screen: summary cards, per-phase table, graphical timeline, text timeline, copy-to-clipboard and navigation back into the loop.
**Prerequisites:** Phase 2 (visualizer), Phase 4 (the input form produces `app.result`).
**Output:** `ui/widgets/stat_card.py`, `ui/widgets/phase_table.py`, `ui/widgets/timeline_canvas.py`, `ui/screens/results.py`.
**Read first:** [PRD](../PRD.md) sections 7 (FR-09 to FR-12, FR-15) and 10.2.

---

## Tasks

### 5.1 Branch
`git checkout -b phase-5-results-and-timeline-view`

### 5.2 `StatCard` (`ui/widgets/stat_card.py`)
1. A `surface` card with a small muted caption (11 pt, uppercase), a large value (32 pt bold, mono), and a unit/subtitle line (12 pt, muted).
2. `StatCard(parent, caption, value, subtitle, accent=None)`; optional `accent` colors the value and draws a 3 px top bar.
3. `update(value, subtitle)` for reuse.

### 5.3 `PhaseTable` (`ui/widgets/phase_table.py`)
1. Build from `CTkLabel`s in a grid (CustomTkinter has no table), with a header row in `surface_alt`.
2. Columns: Phase (code plus label), Volume (veh/hr), Flow ratio `Yi` (4 decimals), Green (s), Share of `Te` (percent, 1 decimal).
3. A footer row: totals (volume sum, `Y`, sum of greens `= Te`, 100.0 percent).
4. Numbers are right-aligned in the mono font; rows alternate `surface` and `surface_alt` at low contrast.
5. A small colored dot before each phase code uses a fixed 8-color cycle derived from the signal tokens plus the accent so rows match the legend elsewhere.

### 5.4 `TimelineCanvas` (`ui/widgets/timeline_canvas.py`)
1. Wraps a `tk.Canvas` (borderless, background `surface`). Colors come from `theme.color(...)` resolved for the current appearance mode; on appearance change, redraw.
2. `draw(timeline: Timeline)`:
   1. Row height 34, row gap 10, label column 90 px on the left (phase code, mono 12 pt), plot area from x = 100 to canvas width minus 16.
   2. For each row call `scale_segments(row, plot_width, timeline.cycle)` (Phase 2.6) and draw rounded-ish rectangles: `G` in `signal_green`, `YR` in `signal_amber`, `R` in `signal_red` at 35 percent opacity (blend with the surface color since Tk has no alpha).
   3. Inside segments wide enough (at least 36 px) draw the text: `G 39s`, `Y/R 4s`, `R 32s`. Narrower segments get no text but a tooltip.
   4. Time axis below the rows: ticks every 5 s for cycles up to 60, every 10 s up to 150, every 25 s above; labels in muted 10 pt; a final tick at the cycle length.
   5. Vertical dashed lines at each phase start.
3. Redraw on `<Configure>` with a 50 ms debounce so resizing stays smooth. Canvas height is `rows * 44 + 48`.
4. Hover tooltip: a small floating label with `{code}: {kind name} {duration}s (t = {start} to {end}s)`, built from `<Motion>` and a hit-test over the scaled segments.
5. Legend row above the canvas: green square "Green", amber square "Yellow / All-Red", red square "Red".

### 5.5 `ResultsScreen` layout (`ui/screens/results.py`)
Top to bottom inside one scrollable frame:
1. Header: breadcrumb "Model / Inputs / Results", title "{model.name} results", subtitle "Saturation flow {S} veh/hr/lane, lost time {li} s per phase".
2. Warnings: a `warning` Banner for each entry in `result.warnings` (hidden when empty).
3. Row of four `StatCard`s (equal columns, wrap to 2 x 2 under 1000 px):
   - "Optimal cycle length (Co)": `{cycle} s`, subtitle `Webster raw: {raw_cycle:.2f} s, rounded up to 5 s` (accent: `accent`)
   - "Total effective green (Te)": `{Te} s`, subtitle `Cycle minus {L} s lost time`
   - "Total flow ratio (Y)": `{Y:.4f}`, subtitle `{n} active phases`, with the `YMeter` embedded below the value
   - "Total lost time (L)": `{L} s`, subtitle `{n} phases x {li} s`
4. Card "Phase green times": `PhaseTable`.
5. Card "Phase timeline": legend, `TimelineCanvas`.
6. Card "Text diagram": read-only mono `CTkTextbox` containing `render_text(timeline)`, horizontal scroll enabled (wrap off), height sized to the row count.
7. Card "Formulas used": a compact list showing each formula with the substituted numbers, for example `Co = (1.5 x 8 + 5) / (1 - 0.7632) = 71.78 s`, `Te = 75 - 8 = 67 s`, `g(NS) = (0.4474 / 0.7632) x 67 = 39.28 -> 39 s`. Build these strings in a small helper `formula_lines(result, lost_time)` inside `ui/screens/results.py`. This helps students check the hand calculation.
8. Action bar (sticky bottom or at the end): "Copy results" (primary), "Edit inputs" (secondary), "New calculation" (text).

### 5.6 Behaviors
1. `on_show()`: read `app.result` and `app.timing_input`; if either is `None`, call `app.show("inputs")` and return. Otherwise `build_timeline(result, timing_input.lost_time)`, then refresh every widget.
2. **Copy results:** `render_report(...)` text goes to the clipboard through `self.clipboard_clear()` and `self.clipboard_append(...)`. The button label changes to "Copied" for 1.5 s, then back (use `after`).
3. **Edit inputs:** `app.show("inputs")`. The form restores `app.form_values` (FR-12). The loop is now: edit, Calculate, see the new results.
4. **New calculation:** `app.reset()`.
5. Keyboard: `Ctrl+C` while nothing is selected in the text box copies the report; `Esc` goes back to inputs.
6. When the appearance mode changes, redraw the canvas and re-resolve colors.

### 5.7 Verify against the PRD cases
For each acceptance case in PRD section 11 (use "Fill example" then Calculate):
1. Stat cards show: case 1 cycle `75 s`, `Te 67 s`, `Y 0.7632`, `L 8 s`; case 2 `125 s`, `113 s`, `0.8158`, `12 s`; case 3 `225 s`, `209 s`, `0.8684`, `16 s`; case 4 `175 s`, `163 s`, `0.8684`, `12 s`; case 5 `115 s`, `99 s`, `0.7368`, `16 s`.
2. Table greens match the case and total `Te`.
3. Canvas rows each span exactly the full width with no gaps.
4. Text box matches the Phase 2 format character for character.
5. Cases 3 and 4 (cycle above 150 s) show the impractical-cycle warning banner.
6. Pasting the copied text into Notepad shows the five report sections in order.
7. Resize from 960 to 1600 px and toggle Light/Dark: the canvas re-renders crisply, text stays readable.

### 5.8 Commit and merge
`git commit -m "Phase 5: results screen, phase table and timeline canvas"`, merge into `main`.

---

## Checklist
- [x] Four stat cards with correct values and subtitles
- [x] Phase table totals match `Y` and `Te`
- [ ] Canvas timeline scales, redraws on resize and theme change, has axis and tooltip
- [x] Text diagram matches the spec exactly
- [x] Formula substitution lines are correct
- [x] Copy results works and confirms visually
- [x] Edit inputs keeps values; New calculation clears them
- [x] Warnings display without blocking the results
- [ ] All items in 5.7 verified

## Definition of done
From model selection to a full, readable result and back into the edit loop, the whole app flow works for all five models.
