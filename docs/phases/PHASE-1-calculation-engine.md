# Phase 1: Calculation Engine

**Goal:** a pure-Python Webster's method engine with validation, fully unit tested, with zero GUI code.
**Prerequisites:** Phase 0 complete.
**Output:** `core/models.py`, `core/validation.py`, `core/calculator.py`, `tests/test_calculator.py`, `tests/test_validation.py`.
**Read first:** [PRD](../PRD.md) sections 4 (formulas), 5 (models), 6 (decisions D1 to D7), 11 (test cases).

Rule for this phase: nothing in `core/` may import `tkinter`, `customtkinter` or anything from `ui/`.

---

## Tasks

### 1.1 Branch
`git checkout -b phase-1-calculation-engine`

### 1.2 Define the data models (`core/models.py`)
1. Add constants at the top:
   ```python
   MAX_SATURATION_FLOW = 2400
   MIN_LOST_TIME = 1
   MAX_LOST_TIME = 12
   MAX_VOLUME = 5000
   CYCLE_STEP = 5
   PRACTICAL_CYCLE_LIMIT = 150
   MIN_GREEN_WARNING = 5
   ```
2. Create frozen dataclass `PhaseDef` with fields `code: str`, `label: str`, `hint: str`.
   - `code` is the short name used in the timeline (`NS`, `MajThru`, `NBL`, ...).
   - `label` is the full text shown beside the input field.
   - `hint` is a one-line help text.
3. Create frozen dataclass `PhaseModel` with fields `key: str`, `name: str`, `description: str`, `phases: tuple[PhaseDef, ...]`. Add a property `phase_count` returning `len(phases)`.
4. Create the registry `MODELS: dict[str, PhaseModel]` with keys `"2"`, `"3"`, `"4"`, `"6"`, `"8"`. Fill the phases exactly as in PRD section 5.2:
   - `"2"`: `NS`, `EW`
   - `"3"`: `MajThru`, `MajLeft`, `MinStem`
   - `"4"`: `NSL`, `NST`, `EWL`, `EWT`
   - `"6"`: `NBL`, `SBL`, `ArtThru`, `MinEB`, `MinWB`
   - `"8"`: `NBL`, `NBT`, `SBL`, `SBT`, `EBL`, `EBT`, `WBL`, `WBT`
5. Create dataclass `TimingInput`: `model_key: str`, `saturation_flow: float`, `lost_time: int`, `volumes: dict[str, float]` (keyed by phase code).
6. Create dataclass `PhaseResult`: `code`, `label`, `volume`, `flow_ratio`, `green` (int), `green_share` (float, `green / Te`).
7. Create dataclass `TimingResult`:
   - `model: PhaseModel`
   - `oversaturated: bool`
   - `total_flow_ratio: float`
   - `total_lost_time: int`
   - `active_count: int`
   - `raw_cycle: float | None`
   - `cycle: int | None`
   - `effective_green: int | None`
   - `phases: list[PhaseResult]` (active phases only, in model order)
   - `warnings: list[str]`
   - `message: str` (empty unless oversaturated)

### 1.3 Pure formula functions (`core/calculator.py`)
Write each as a small function with type hints and no side effects.

1. `flow_ratio(volume: float, saturation_flow: float) -> float` returns `volume / saturation_flow`.
2. `total_lost_time(active_count: int, lost_time: int) -> int` returns `active_count * lost_time`.
3. `webster_cycle(total_lost: int, total_flow_ratio: float) -> float` returns `(1.5 * total_lost + 5) / (1 - total_flow_ratio)`. Do not guard `Y >= 1.0` here; the caller decides.
4. `round_cycle(raw_cycle: float) -> int` returns `math.ceil(raw_cycle / CYCLE_STEP) * CYCLE_STEP`. Guard against float noise: use `math.ceil(round(raw_cycle / CYCLE_STEP, 9))`.
5. `apportion_greens(ratios: list[float], effective_green: int) -> list[int]` implements largest-remainder rounding (decision D4):
   1. `total = sum(ratios)`.
   2. `exact = [r / total * effective_green for r in ratios]`.
   3. `greens = [math.floor(x) for x in exact]`.
   4. `leftover = effective_green - sum(greens)`.
   5. Sort indexes by `exact[i] - greens[i]` descending; add 1 to the first `leftover` indexes. Break ties by lower index first.
   6. Return `greens`. Invariant: `sum(greens) == effective_green`.

### 1.4 The orchestrator (`core/calculator.py`)
Write `compute_timing(data: TimingInput) -> TimingResult`:
1. Look up `model = MODELS[data.model_key]`.
2. Build the active list: phases from `model.phases` where `data.volumes[code] > 0`, keeping model order.
3. Compute `ratios = [flow_ratio(v, data.saturation_flow) ...]` for active phases; `Y = sum(ratios)`; `L = total_lost_time(len(active), data.lost_time)`.
4. If `Y >= 1.0`: return a `TimingResult` with `oversaturated=True`, `raw_cycle=None`, `cycle=None`, `effective_green=None`, phases filled with `green=0`, and `message` = `"Oversaturated: total flow ratio Y = {Y:.4f} is 1.0 or higher. Demand exceeds capacity, so Webster's cycle cannot be computed."`.
5. Otherwise compute `raw = webster_cycle(L, Y)`, `cycle = round_cycle(raw)`, `te = cycle - int(L)`.
   - `lost_time` is validated as a whole number (task 1.5), so `L` is always whole and `Te` is an exact integer.
6. `greens = apportion_greens(ratios, te)`; build `PhaseResult` list with `green_share = green / te`.
7. Add warnings:
   - `cycle > PRACTICAL_CYCLE_LIMIT`: `"Cycle of {cycle} s is impractically long. Y is close to 1.0; consider more lanes or a different phasing."`
   - any `green < MIN_GREEN_WARNING`: `"Phase {code} has only {green} s of green, below the {MIN_GREEN_WARNING} s minimum."`
8. Return the result. `compute_timing` must never raise for validated input.

### 1.5 Validation (`core/validation.py`)
1. Dataclass `FieldError`: `field: str` (`"saturation_flow"`, `"lost_time"` or a phase code), `message: str`.
2. `parse_number(text: str) -> float | None`: strip whitespace; accept `.` decimals; also accept a single `,` as decimal separator by replacing it with `.`; return `None` for empty or non-numeric; reject `nan` and `inf`.
3. `validate_inputs(model_key: str, raw: dict[str, str]) -> tuple[TimingInput | None, list[FieldError]]`:
   1. `raw` keys: `saturation_flow`, `lost_time`, plus each phase code of the model.
   2. For each field produce the first applicable error message:
      - empty: `"Required"`
      - not a number: `"Enter a number"`
      - `saturation_flow`: `<= 0` -> `"Must be greater than 0"`; `> 2400` -> `"Must be 2400 or less"`
      - `lost_time`: not a whole number (for example `3.5`) -> `"Must be a whole number of seconds"`; `< 1` -> `"Must be at least 1 s"`; `> 12` -> `"Must be 12 s or less"`
      - volume: `< 0` -> `"Cannot be negative"`; `> 5000` -> `"Must be 5000 or less"`
   3. If all fields parse and every volume is 0, add one error with `field="volumes"` and `"At least one volume must be greater than 0"`.
   4. Return `(None, errors)` if any error, otherwise `(TimingInput(...), [])`. Collect all errors in one pass so the UI can highlight every bad field at once.

### 1.6 Tests (`tests/test_calculator.py`)
Write pytest tests with `pytest.approx` for floats:
1. `flow_ratio`: `850/1900 == approx(0.447368)`.
2. `total_lost_time`: `(3, 4) == 12`.
3. `webster_cycle`: `(8, 0.763158) == approx(71.78, abs=0.01)`.
4. `round_cycle`: `71.78 -> 75`, `75.0 -> 75`, `75.0000000001 -> 75`, `75.01 -> 80`.
5. `apportion_greens`: sum equals `effective_green` for 200 random ratio lists (seeded); a tie case such as `[1, 1, 1]` with `te=10` gives `[4, 3, 3]`.
6. The six acceptance cases from PRD section 11 via `@pytest.mark.parametrize`, asserting `Y`, `L`, raw cycle, cycle, `Te` and the green list, and for case 6 `oversaturated is True` and `cycle is None`.
7. Inactive phases: case 4 returns exactly 3 phases and `L == 12`.
8. Warnings: a Y of 0.99 case returns the impractical cycle warning; a tiny-volume phase returns the minimum green warning.
9. Exactly `Y == 1.0` is oversaturated.

### 1.7 Tests (`tests/test_validation.py`)
1. Valid input returns a `TimingInput` and no errors.
2. Empty, text, `nan`, `inf`, negative and too-large values each return the exact messages from 1.5.
3. Comma decimal `"1,5"` parses to `1.5`.
4. All-zero volumes returns the `volumes` error.
5. Several bad fields at once return several `FieldError`s.

### 1.8 Verify
1. `pytest --cov=core --cov-report=term-missing`
2. Coverage of `core/calculator.py` and `core/validation.py` must be 95 percent or more.
3. Run `python -c "from core.calculator import compute_timing"`; it must import without side effects.
4. Search `core/` for `tkinter` or `customtkinter`: no matches.

### 1.9 Commit and merge
`git commit -m "Phase 1: Webster calculation engine and input validation"`, then merge into `main`.

---

## Checklist
- [x] Models and the `MODELS` registry match PRD section 5.2
- [x] Formula functions implemented and individually tested
- [x] Largest-remainder rounding guarantees `sum(greens) == Te`
- [x] Oversaturation returns a result object, not an exception
- [x] Validation collects all errors in one pass
- [x] All six acceptance cases pass
- [x] Coverage 95 percent or more on both modules
- [x] No GUI imports in `core/`
- [x] Comments are single-line only, no docstring blocks

## Definition of done
`compute_timing` returns correct, rounded, self-consistent results for every phase model, and every failure path is a value, not a crash.
