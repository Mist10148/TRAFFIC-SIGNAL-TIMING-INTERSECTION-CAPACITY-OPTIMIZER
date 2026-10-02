# Phase 3: GUI Shell and Theme

**Goal:** the app frame: theme tokens, sidebar, screen switching and the Model Select screen. No calculations on screen yet.
**Prerequisites:** Phase 1 (needs `MODELS`). Phase 2 is not required.
**Output:** `ui/theme.py`, `ui/app.py`, `ui/screens/model_select.py`, `ui/widgets/model_card.py`, `ui/widgets/banner.py`.
**Read first:** [PRD](../PRD.md) section 10 (GUI requirements).

---

## Tasks

### 3.1 Branch
`git checkout -b phase-3-gui-shell-and-theme`

### 3.2 Theme tokens (`ui/theme.py`)
1. Define two dicts, `DARK` and `LIGHT`, with the keys and hex values from PRD section 10.1: `bg`, `surface`, `surface_alt`, `border`, `text`, `text_muted`, `accent`, `signal_green`, `signal_amber`, `signal_red`.
2. Add `RADIUS_CARD = 12`, `RADIUS_INPUT = 8`, spacing constants `PAD_S = 8`, `PAD_M = 16`, `PAD_L = 24`.
3. Add `font(size, weight="normal", mono=False)` returning a `ctk.CTkFont`. UI family `Segoe UI Variable` with fallback `Segoe UI`; mono family `Cascadia Mono` with fallback `Consolas`. Check availability with `tkinter.font.families()` once and cache the result.
4. Add `color(name)` returning a `(light, dark)` tuple, which is what CustomTkinter accepts for dual-theme colors: `(LIGHT[name], DARK[name])`. Every widget uses `color("...")`; no hex literals outside `theme.py`.

### 3.3 App window (`ui/app.py`)
1. `FlowApp(ctk.CTk)`: call `ctk.set_appearance_mode("system")` and `ctk.set_default_color_theme("blue")` before `super().__init__()`.
2. Title, geometry 1120 x 720, minsize 960 x 640 (from Phase 0). Center the window on the screen.
3. Grid layout: column 0 sidebar (fixed width 220, no expand), column 1 content (weight 1), one row (weight 1).
4. Shared state on the app object, typed: `self.model_key: str | None`, `self.form_values: dict[str, str]`, `self.result: TimingResult | None`, `self.timing_input: TimingInput | None`.

### 3.4 Sidebar
1. Top: app wordmark "FLOW" in 24 pt bold with the accent color, subtitle "Signal Timing Optimizer" in muted 11 pt.
2. Nav buttons (flat, left-aligned, 36 px high): "New calculation" (always enabled), "Inputs" (enabled only after a model is chosen), "Results" (enabled only after a successful calculation). The active screen's button uses `surface_alt` and the accent text color.
3. Bottom: an "Appearance" segmented control with `Light`, `Dark`, `System`. On change call `ctk.set_appearance_mode(...)`.
4. Footer: "ENGG 1035 | Webster's Method" in muted 10 pt.

### 3.5 Screen switching
1. In `FlowApp` create `self.screens: dict[str, ctk.CTkFrame]` containing `"model"`, `"inputs"`, `"results"` (inputs and results are stubs until Phases 4 and 5: a frame with a centered "Coming in Phase 4/5" label).
2. Add `show(name: str) -> None` that `grid_remove`s the current screen, `grid`s the target with `sticky="nsew"`, updates sidebar button states and calls the screen's optional `on_show()` method.
3. Add `reset()` clearing model, form values and result, then `show("model")`.

### 3.6 Reusable widgets
1. `ui/widgets/banner.py`: `Banner(parent, kind, text)` with `kind` in `"info"`, `"warning"`, `"error"`. Left color bar 4 px in the matching signal color, icon letter (`i`, `!`, `x`) in a circle, text label wrapping to the banner width, and `set(kind, text)`, `hide()` and `show()` methods.
2. `ui/widgets/model_card.py`: `ModelCard(parent, model, on_select)`. A `surface` card, 12 px radius, 1 px `border`, containing:
   - a 120 x 56 canvas with a tiny phase mini-diagram: one colored bar per phase (green, amber, red repeating) to hint at the model size,
   - the model name (`2-Phase`, ...) in 16 pt bold,
   - the description (from `PhaseModel.description`) in muted 12 pt, wrapping,
   - "{n} volume inputs" in the accent color.
   Hover raises the border to the accent color; click and Enter/Space key call `on_select(model.key)`.

### 3.7 Model Select screen (`ui/screens/model_select.py`)
1. `ModelSelectScreen(parent, app)`: title "Choose a phase model" (28 pt bold), subtitle "Pick the signal phasing that matches your intersection." (muted).
2. A responsive grid of `ModelCard`s built from `MODELS`: 3 columns at width 900 px or more, 2 columns below, re-laid out on `<Configure>` with a 100 ms debounce.
3. Selecting a card sets `app.model_key`, resets `form_values` only if the model changed, then calls `app.show("inputs")`.
4. Under the cards add an `info` Banner: "Phases with a volume of 0 are left out of the cycle."

### 3.8 Verify
1. `python main.py`: the sidebar and five cards render; clicking a card switches to the placeholder Inputs screen; "New calculation" returns.
2. Toggle Light, Dark, System: all text readable, no hard-coded colors left behind.
3. Resize from 960 to 1600 px wide: the card grid switches between 2 and 3 columns, nothing is cut off.
4. Run at Windows display scaling 100 percent and 150 percent; fonts and padding stay proportional.
5. `pytest` still passes (no GUI tests required in this phase).

### 3.9 Commit and merge
`git commit -m "Phase 3: GUI shell, theme and model selection"`, merge into `main`.

---

## Checklist
- [x] All colors come from `theme.py`
- [x] Both appearance modes verified by eye
- [x] Sidebar buttons enable and disable by app state
- [x] Model cards keyboard accessible (Tab, Enter, Space)
- [x] Responsive grid works at 960 to 1600 px
- [x] Selecting a model sets shared state and navigates
- [x] Single-line comments only, no hex literals outside `theme.py`

## Definition of done
The app looks like a finished product shell: you can launch it, switch theme, pick a model and navigate, even though inputs and results are not built yet.
