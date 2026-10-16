from dataclasses import dataclass, field
from functools import lru_cache
import math
from pathlib import Path
import re
from tkinter import font as tkfont
import tkinter as tk
from typing import Callable

import customtkinter as ctk


# Models

MAX_SATURATION_FLOW = 2400
MIN_LOST_TIME = 1
MAX_LOST_TIME = 12
MAX_VOLUME = 5000
CYCLE_STEP = 5
PRACTICAL_CYCLE_LIMIT = 150
MIN_GREEN_WARNING = 5


@dataclass(frozen=True)
class PhaseDef:
    code: str
    label: str
    hint: str


@dataclass(frozen=True)
class PhaseModel:
    key: str
    name: str
    description: str
    phases: tuple[PhaseDef, ...]

    @property
    def phase_count(self) -> int:
        return len(self.phases)


def _phase(code: str, label: str, hint: str = "Vehicles per hour") -> PhaseDef:
    return PhaseDef(code, label, hint)


MODELS: dict[str, PhaseModel] = {
    "2": PhaseModel(
        key="2",
        name="2-Phase",
        description="Standard 4-way or simple T",
        phases=(
            _phase("NS", "North-South Thru and Right"),
            _phase("EW", "East-West Thru and Right"),
        ),
    ),
    "3": PhaseModel(
        key="3",
        name="3-Phase",
        description="T-intersection with major left turn",
        phases=(
            _phase("MajThru", "Major Street Thru and Right"),
            _phase("MajLeft", "Major Street Protected Left"),
            _phase("MinStem", "Minor Street (Stem) All Movements"),
        ),
    ),
    "4": PhaseModel(
        key="4",
        name="4-Phase",
        description="Protected lefts or split phasing",
        phases=(
            _phase("NSL", "NS Protected Left"),
            _phase("NST", "NS Thru and Right"),
            _phase("EWL", "EW Protected Left"),
            _phase("EWT", "EW Thru and Right"),
        ),
    ),
    "6": PhaseModel(
        key="6",
        name="6-Phase",
        description="Major arterial with protected lefts",
        phases=(
            _phase("NBL", "Arterial NB Protected Left"),
            _phase("SBL", "Arterial SB Protected Left"),
            _phase("ArtThru", "Arterial NB and SB Thru and Right"),
            _phase("MinEB", "Minor EB All Movements"),
            _phase("MinWB", "Minor WB All Movements"),
        ),
    ),
    "8": PhaseModel(
        key="8",
        name="8-Phase",
        description="NEMA dual-ring, complex 4-way",
        phases=(
            _phase("NBL", "Northbound Protected Left"),
            _phase("NBT", "Northbound Thru and Right"),
            _phase("SBL", "Southbound Protected Left"),
            _phase("SBT", "Southbound Thru and Right"),
            _phase("EBL", "Eastbound Protected Left"),
            _phase("EBT", "Eastbound Thru and Right"),
            _phase("WBL", "Westbound Protected Left"),
            _phase("WBT", "Westbound Thru and Right"),
        ),
    ),
}


@dataclass
class TimingInput:
    model_key: str
    saturation_flow: float
    lost_time: int
    # demand in veh/hr, keyed by phase code
    volumes: dict[str, float]


@dataclass
class PhaseResult:
    code: str
    label: str
    volume: float
    flow_ratio: float
    green: int
    # this phase's slice of the effective green (green / Te)
    green_share: float


@dataclass
class TimingResult:
    model: PhaseModel
    oversaturated: bool
    total_flow_ratio: float
    total_lost_time: int
    active_count: int
    raw_cycle: float | None = None
    cycle: int | None = None
    effective_green: int | None = None
    # active phases only, in model order
    phases: list[PhaseResult] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    # only filled when oversaturated
    message: str = ""


# Validation

@dataclass
class FieldError:
    # "saturation_flow", "lost_time", "volumes", or a phase code
    field: str
    message: str


def parse_number(text: str) -> float | None:
    cleaned = text.strip()
    # Some people type 1,5 instead of 1.5, so one comma counts as a decimal point.
    if cleaned.count(",") == 1:
        cleaned = cleaned.replace(",", ".")
    if not cleaned:
        return None
    try:
        value = float(cleaned)
    except ValueError:
        return None
    if math.isnan(value) or math.isinf(value):
        return None
    return value


def validate_inputs(
    model_key: str, raw: dict[str, str]
) -> tuple[TimingInput | None, list[FieldError]]:
    model = MODELS[model_key]
    errors: list[FieldError] = []

    saturation, message = _check_saturation(raw.get("saturation_flow", ""))
    if message:
        errors.append(FieldError("saturation_flow", message))

    lost_time, message = _check_lost_time(raw.get("lost_time", ""))
    if message:
        errors.append(FieldError("lost_time", message))

    volumes: dict[str, float] = {}
    for phase in model.phases:
        volume, message = _check_volume(raw.get(phase.code, ""))
        if message:
            errors.append(FieldError(phase.code, message))
        else:
            volumes[phase.code] = volume

    # Only worth saying if every volume itself was fine.
    all_volumes_ok = len(volumes) == model.phase_count
    if all_volumes_ok and all(v == 0 for v in volumes.values()):
        errors.append(FieldError("volumes", "At least one volume must be greater than 0"))

    if errors:
        return None, errors
    return TimingInput(model_key, saturation, lost_time, volumes), []


# Each checker returns (value, error message). The message is "" when the value is fine.

def _read_number(text: str) -> tuple[float, str]:
    if not text.strip():
        return 0.0, "Required"
    value = parse_number(text)
    if value is None:
        return 0.0, "Enter a number"
    return value, ""


def _check_saturation(text: str) -> tuple[float, str]:
    value, message = _read_number(text)
    if message:
        return value, message
    if value <= 0:
        return value, "Must be greater than 0"
    if value > MAX_SATURATION_FLOW:
        return value, f"Must be {MAX_SATURATION_FLOW} or less"
    return value, ""


def _check_lost_time(text: str) -> tuple[int, str]:
    value, message = _read_number(text)
    if message:
        return 0, message
    if value != int(value):
        return 0, "Must be a whole number of seconds"
    if value < MIN_LOST_TIME:
        return 0, f"Must be at least {MIN_LOST_TIME} s"
    if value > MAX_LOST_TIME:
        return 0, f"Must be {MAX_LOST_TIME} s or less"
    return int(value), ""


def _check_volume(text: str) -> tuple[float, str]:
    value, message = _read_number(text)
    if message:
        return value, message
    if value < 0:
        return value, "Cannot be negative"
    if value > MAX_VOLUME:
        return value, f"Must be {MAX_VOLUME} or less"
    return value, ""


# Calculator

def flow_ratio(volume: float, saturation_flow: float) -> float:
    return volume / saturation_flow


def total_lost_time(active_count: int, lost_time: int) -> int:
    return active_count * lost_time


def webster_cycle(total_lost: int, total_flow_ratio: float) -> float:
    # Only valid while Y < 1. The caller checks that before calling.
    return (1.5 * total_lost + 5) / (1 - total_flow_ratio)


def round_cycle(raw_cycle: float) -> int:
    # The inner round() keeps float noise (75.0000000001) from bumping us to 80.
    return math.ceil(round(raw_cycle / CYCLE_STEP, 9)) * CYCLE_STEP


def apportion_greens(ratios: list[float], effective_green: int) -> list[int]:
    # Largest-remainder rounding: floor everything, then hand the leftover
    # seconds to the phases that lost the most. This keeps the sum exact.
    total = sum(ratios)
    exact = [r / total * effective_green for r in ratios]
    greens = [math.floor(x) for x in exact]
    leftover = effective_green - sum(greens)

    by_remainder = sorted(range(len(ratios)), key=lambda i: exact[i] - greens[i], reverse=True)
    for i in by_remainder[:leftover]:
        greens[i] += 1
    return greens


def compute_timing(data: TimingInput) -> TimingResult:
    model = MODELS[data.model_key]

    # A phase with zero demand is dropped from the cycle entirely.
    active = [p for p in model.phases if data.volumes[p.code] > 0]
    ratios = [flow_ratio(data.volumes[p.code], data.saturation_flow) for p in active]
    total_y = sum(ratios)
    lost = total_lost_time(len(active), data.lost_time)

    if total_y >= 1.0:
        return _oversaturated_result(model, data, active, ratios, total_y, lost)

    raw = webster_cycle(lost, total_y)
    cycle = round_cycle(raw)
    effective = cycle - lost
    greens = apportion_greens(ratios, effective)

    phases = [
        PhaseResult(p.code, p.label, data.volumes[p.code], y, g, g / effective)
        for p, y, g in zip(active, ratios, greens)
    ]
    return TimingResult(
        model=model,
        oversaturated=False,
        total_flow_ratio=total_y,
        total_lost_time=lost,
        active_count=len(active),
        raw_cycle=raw,
        cycle=cycle,
        effective_green=effective,
        phases=phases,
        warnings=_build_warnings(cycle, phases),
    )


def _oversaturated_result(model, data, active, ratios, total_y, lost) -> TimingResult:
    phases = [
        PhaseResult(p.code, p.label, data.volumes[p.code], y, 0, 0.0)
        for p, y in zip(active, ratios)
    ]
    message = (
        f"Oversaturated: total flow ratio Y = {total_y:.4f} is 1.0 or higher. "
        "Demand exceeds capacity, so Webster's cycle cannot be computed."
    )
    return TimingResult(
        model=model,
        oversaturated=True,
        total_flow_ratio=total_y,
        total_lost_time=lost,
        active_count=len(active),
        phases=phases,
        message=message,
    )


def _build_warnings(cycle: int, phases: list[PhaseResult]) -> list[str]:
    warnings = []
    if cycle > PRACTICAL_CYCLE_LIMIT:
        warnings.append(
            f"Cycle of {cycle} s is impractically long. "
            "Y is close to 1.0; consider more lanes or a different phasing."
        )
    for p in phases:
        if p.green < MIN_GREEN_WARNING:
            warnings.append(
                f"Phase {p.code} has only {p.green} s of green, "
                f"below the {MIN_GREEN_WARNING} s minimum."
            )
    return warnings


# Narrative

# Total flow ratio above this leaves little spare capacity for a fixed-time plan.
NEAR_CAPACITY_Y = 0.85
COMFORTABLE_Y = 0.60


def _join(items: list[str]) -> str:
    if len(items) <= 2:
        return " and ".join(items)
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def _summary(result: TimingResult) -> str:
    return (
        f"The {result.model.name} plan needs a cycle length of {result.cycle} s, "
        f"which leaves {result.effective_green} s of effective green after "
        f"{result.total_lost_time} s of lost time. The total flow ratio is "
        f"Y = {result.total_flow_ratio:.4f}."
    )


def _description(result: TimingResult, saturation_flow: float, lost_time: float) -> str:
    codes = [p.code for p in result.phases]
    skipped = len(result.model.phases) - result.active_count
    text = (
        f"This is a {result.model.name} signal ({result.model.description}) "
        f"timed with Webster's method. It runs {result.active_count} active phases "
        f"({_join(codes)}), each with {lost_time:g} s of lost time (amber plus all-red) "
        f"and a saturation flow of {saturation_flow:g} veh/hr/lane."
    )
    if skipped:
        text += f" {skipped} phase(s) with zero demand were left out of the cycle."
    text += (
        " The cycle is rounded up to the next 5 s, and the effective green is "
        "shared between phases in proportion to their flow ratios."
    )
    return text


def _results(result: TimingResult) -> str:
    greens = [f"{p.code} {p.green} s" for p in result.phases]
    return (
        f"Webster's optimal cycle is {result.raw_cycle:.2f} s, rounded up to "
        f"{result.cycle} s. With {result.total_lost_time} s of lost time, the "
        f"effective green is {result.effective_green} s, split as {_join(greens)}."
    )


def _discussion(result: TimingResult) -> str:
    y = result.total_flow_ratio
    critical = max(result.phases, key=lambda p: p.flow_ratio)

    if y >= NEAR_CAPACITY_Y:
        load = (
            f"With Y = {y:.4f} the intersection is close to capacity, so there is "
            "little room for demand to grow before it becomes oversaturated."
        )
    elif y >= COMFORTABLE_Y:
        load = f"With Y = {y:.4f} the intersection is moderately loaded and still has spare capacity."
    else:
        load = f"With Y = {y:.4f} the intersection is lightly loaded and has plenty of spare capacity."

    parts = [
        load,
        f"Phase {critical.code} is the critical phase with the highest flow ratio "
        f"({critical.flow_ratio:.4f}), so it receives the longest green "
        f"({critical.green} s, {critical.green_share:.0%} of the effective green).",
    ]
    for warning in result.warnings:
        parts.append(f"Note: {warning}")
    return " ".join(parts)


def build_narrative(
    result: TimingResult, saturation_flow: float, lost_time: float
) -> list[tuple[str, str]]:
    return [
        ("Summary", _summary(result)),
        ("Description", _description(result, saturation_flow, lost_time)),
        ("Results", _results(result)),
        ("Discussion", _discussion(result)),
    ]


def render_narrative(sections: list[tuple[str, str]]) -> str:
    return "\n\n".join(f"{title.upper()}\n{text}" for title, text in sections)


# Visualizer

@dataclass(frozen=True)
class Segment:
    # "R" red, "G" green, "YR" yellow / all-red
    kind: str
    start: int
    duration: int


@dataclass(frozen=True)
class TimelineRow:
    code: str
    label: str
    segments: tuple[Segment, ...]


@dataclass(frozen=True)
class Timeline:
    cycle: int
    lost_time_per_phase: int
    rows: tuple[TimelineRow, ...]


def build_timeline(result: TimingResult, lost_time: float) -> Timeline:
    if result.oversaturated:
        raise ValueError("Timeline requires a non-oversaturated result")

    cycle = result.cycle
    yr = int(lost_time)
    rows = []
    # Phases run one after another, so each one starts when the previous
    # phase has finished its green and its lost time.
    start = 0
    for phase in result.phases:
        end_of_phase = start + phase.green + yr
        segments = [
            Segment("R", 0, start),
            Segment("G", start, phase.green),
            Segment("YR", start + phase.green, yr),
            Segment("R", end_of_phase, cycle - end_of_phase),
        ]
        # Red before/after only exist when they actually last some time.
        kept = tuple(s for s in segments if s.kind != "R" or s.duration > 0)
        _check_row(phase.code, kept, cycle)
        rows.append(TimelineRow(phase.code, phase.label, kept))
        start = end_of_phase

    return Timeline(cycle, yr, tuple(rows))


def _check_row(code: str, segments: tuple[Segment, ...], cycle: int) -> None:
    # Explicit raise instead of assert so the check survives python -O.
    expected_start = 0
    for seg in segments:
        if seg.start != expected_start:
            raise AssertionError(f"Phase {code} has a gap or overlap at {seg.start} s")
        expected_start += seg.duration
    if expected_start != cycle:
        raise AssertionError(f"Phase {code} adds up to {expected_start} s, not {cycle} s")


def _inputs_section(result: TimingResult, saturation_flow: float, lost_time: float) -> list[str]:
    lines = [
        "INPUTS",
        f"Model: {result.model.name}",
        f"Saturation Flow: {saturation_flow:g} veh/hr",
        f"Lost Time per Phase: {lost_time:g} s",
    ]
    lines += [f"Volume {p.code}: {p.volume:g} veh/hr" for p in result.phases]
    return lines


def _variables_section(result: TimingResult) -> list[str]:
    lines = ["CALCULATED VARIABLES"]
    lines += [f"Flow Ratio {p.code}: {p.flow_ratio:.4f}" for p in result.phases]
    lines += [
        f"Total Flow Ratio (Y): {result.total_flow_ratio:.4f}",
        f"Total Lost Time (L): {result.total_lost_time} s",
        f"Active Phases: {result.active_count}",
    ]
    return lines


def _output_section(result: TimingResult) -> list[str]:
    lines = [
        "OUTPUT",
        f"Webster Cycle (Co): {result.raw_cycle:.2f} s",
        f"Cycle Length: {result.cycle} s",
        f"Effective Green (Te): {result.effective_green} s",
    ]
    lines += [f"Green {p.code}: {p.green} s" for p in result.phases]
    return lines


def render_report(result: TimingResult, saturation_flow: float, lost_time: float) -> str:
    sections = [
        _inputs_section(result, saturation_flow, lost_time),
        _variables_section(result),
        _output_section(result),
    ]
    if result.warnings:
        sections.append(["WARNINGS"] + [f"- {w}" for w in result.warnings])
    text = "\n\n".join("\n".join(lines) for lines in sections)
    narrative = render_narrative(build_narrative(result, saturation_flow, lost_time))
    return f"{text}\n\n{narrative}"


def scale_segments(row: TimelineRow, pixel_width: int, cycle: int) -> list[tuple[str, int, int]]:
    scaled = []
    for seg in row.segments:
        x = round(seg.start / cycle * pixel_width)
        # Measuring the width from the rounded edges means neighbours always
        # meet exactly: no gaps, no overlaps.
        width = round((seg.start + seg.duration) / cycle * pixel_width) - x
        if seg.duration > 0:
            width = max(width, 2)
        scaled.append((seg.kind, x, width))
    return scaled


# Theme

LIGHT = {
    "bg": "#FAF9F5",
    "surface": "#FFFFFF",
    "surface_alt": "#F0EEE6",
    "border": "#E3DFD3",
    "text": "#29261F",
    "text_muted": "#6B665B",
    "accent": "#A8492A",
    "accent_hover": "#8F3C20",
    "on_accent": "#FFFFFF",
    "signal_green": "#2E7D4F",
    "signal_amber": "#C98A1B",
    "signal_red": "#C2453D",
    "error_bg": "#FBEAE6",
    "warning_bg": "#FBF1DB",
    "info_bg": "#EEF1F6",
}

DARK = {
    "bg": "#1F1E1D",
    "surface": "#2A2926",
    "surface_alt": "#34322E",
    "border": "#403D38",
    "text": "#F0EEE6",
    "text_muted": "#A8A294",
    "accent": "#E4896A",
    "accent_hover": "#EE9C80",
    "on_accent": "#1F1E1D",
    "signal_green": "#5BB57A",
    "signal_amber": "#E0A93B",
    "signal_red": "#EA7C74",
    "error_bg": "#3D2623",
    "warning_bg": "#3A3022",
    "info_bg": "#26292E",
}

RADIUS_CARD = 12
RADIUS_INPUT = 8

PAD_S = 8
PAD_M = 16
PAD_L = 24

SANS_FAMILIES = ("Segoe UI Variable", "Segoe UI", "Arial")
SERIF_FAMILIES = ("Georgia", "Cambria", "Times New Roman")
MONO_FAMILIES = ("Cascadia Mono", "Consolas", "Courier New")


def color(name: str) -> tuple[str, str]:
    # CustomTkinter takes (light, dark) and switches by itself with the 
    return (LIGHT[name], DARK[name])


def resolve(name: str) -> str:
    # Plain tk widgets (like Canvas) can't take a (light, dark) pair,
    # so they ask for the hex of whichever mode is on screen right now.
    tokens = DARK if ctk.get_appearance_mode() == "Dark" else LIGHT
    return tokens[name]


@lru_cache(maxsize=1)
def _installed_families() -> frozenset[str]:
    return frozenset(tkfont.families())


def _pick_family(candidates: tuple[str, ...]) -> str:
    installed = _installed_families()
    for name in candidates:
        if name in installed:
            return name
    return candidates[-1]


@lru_cache(maxsize=None)
def font(size: int, weight: str = "normal", serif: bool = False, mono: bool = False) -> ctk.CTkFont:
    if mono:
        family = _pick_family(MONO_FAMILIES)
    elif serif:
        family = _pick_family(SERIF_FAMILIES)
    else:
        family = _pick_family(SANS_FAMILIES)
    return ctk.CTkFont(family=family, size=size, weight=weight)


# Widgets: Card

class Card(ctk.CTkFrame):
    # A bordered surface with a serif title. Put your own content in row 1 and below.
    def __init__(self, parent, title: str) -> None:
        super().__init__(
            parent, corner_radius=RADIUS_CARD, border_width=1, height=0,
            fg_color=color("surface"), border_color=color("border"),
        )
        self.columnconfigure(0, weight=1)
        ctk.CTkLabel(
            self, text=title, anchor="w",
            font=font(18, serif=True), text_color=color("text"),
        ).grid(row=0, column=0, sticky="ew", padx=PAD_M, pady=PAD_M)


# Widgets: Banner

# kind -> (background token, bar and icon token, icon letter)
KINDS = {
    "info": ("info_bg", "text_muted", "i"),
    "warning": ("warning_bg", "signal_amber", "!"),
    "error": ("error_bg", "signal_red", "x"),
}


# Space taken by the bar, icon and padding to the left and right of the text.
BANNER_TEXT_INSET = 80


class Banner(ctk.CTkFrame):
    def __init__(self, parent, kind: str, text: str) -> None:
        # height=0 lets the banner shrink to its text instead of the 200 px default.
        super().__init__(parent, corner_radius=RADIUS_INPUT, height=0)
        self.columnconfigure(2, weight=1)

        self.bar = ctk.CTkFrame(self, width=4, height=1, corner_radius=0)
        self.bar.grid(row=0, column=0, sticky="ns")

        self.icon = ctk.CTkLabel(
            self, text="", width=22, height=22, corner_radius=11,
            font=font(12, "bold"), text_color=color("on_accent"),
        )
        self.icon.grid(row=0, column=1, padx=(PAD_M, PAD_S), pady=PAD_M, sticky="n")

        self.message = ctk.CTkLabel(
            self, text="", anchor="w", justify="left",
            font=font(13), text_color=color("text"),
        )
        self.message.grid(row=0, column=2, padx=(0, PAD_M), pady=PAD_M, sticky="ew")
        # Wrap against the banner's own width. Using the label's width would feed
        # back on itself, since wrapping changes the label's size.
        self.bind("<Configure>", self._wrap_to_width)

        self.set(kind, text)

    def set(self, kind: str, text: str) -> None:
        background, accent, letter = KINDS[kind]
        self.configure(fg_color=color(background))
        self.bar.configure(fg_color=color(accent))
        self.icon.configure(text=letter, fg_color=color(accent))
        self.message.configure(text=text)

    def show(self) -> None:
        self.grid()

    def hide(self) -> None:
        self.grid_remove()

    def _wrap_to_width(self, event) -> None:
        self.message.configure(wraplength=max(event.width - BANNER_TEXT_INSET, 100))


# Widgets: LabeledEntry

# Digits with at most one . or , and an optional minus at the front.
NUMBER_SHAPE = re.compile(r"^-?[0-9]*[.,]?[0-9]*$")
ENTRY_HEIGHT = 38


class LabeledEntry(ctk.CTkFrame):
    def __init__(self, parent, label: str, unit: str, hint: str, placeholder: str = "0") -> None:
        super().__init__(parent, fg_color="transparent", height=0)
        self.hint = hint
        self.columnconfigure(0, weight=1)

        top = ctk.CTkFrame(self, fg_color="transparent", height=0)
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(0, weight=1)
        ctk.CTkLabel(
            top, text=label, anchor="w",
            font=font(13), text_color=color("text"),
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            top, text=unit, anchor="e",
            font=font(11), text_color=color("text_muted"),
        ).grid(row=0, column=1, sticky="e")

        self.entry = ctk.CTkEntry(
            self, height=ENTRY_HEIGHT, corner_radius=RADIUS_INPUT, border_width=1,
            placeholder_text=placeholder, font=font(13),
            fg_color=color("surface"), border_color=color("border"),
            text_color=color("text"), placeholder_text_color=color("text_muted"),
        )
        self.entry.grid(row=1, column=0, sticky="ew", pady=(4, 2))

        self.note = ctk.CTkLabel(
            self, text=hint, anchor="w", justify="left",
            font=font(11), text_color=color("text_muted"),
        )
        self.note.grid(row=2, column=0, sticky="ew")
        # Wrap against the whole field width, not the label itself, to avoid a resize loop.
        self.bind("<Configure>", lambda e: self.note.configure(wraplength=max(e.width - 8, 80)))

        self.status = "normal"
        self.entry.bind("<FocusIn>", self._on_focus_in)
        self.entry.bind("<FocusOut>", self._on_focus_out)
        self.entry.bind("<KeyRelease>", self._check_shape, add="+")

    def get(self) -> str:
        return self.entry.get()

    def set(self, text: str) -> None:
        self.entry.delete(0, "end")
        self.entry.insert(0, text)

    def focus(self) -> None:
        self.entry.focus_set()

    def bind_change(self, callback: Callable[[], None]) -> None:
        self.entry.bind("<KeyRelease>", lambda _: callback(), add="+")

    def bind_enter(self, callback: Callable[[], None]) -> None:
        self.entry.bind("<Return>", lambda _: callback())

    def set_error(self, message: str) -> None:
        self.status = "error"
        self._paint_border(focused=False)
        self.note.configure(text=message, text_color=color("signal_red"))

    def set_highlight(self) -> None:
        # A softer amber outline: "this one is part of the problem", not "this is invalid".
        self.status = "highlight"
        self._paint_border(focused=False)

    def clear_error(self) -> None:
        self.status = "normal"
        self._paint_border(focused=False)
        self.note.configure(text=self.hint, text_color=color("text_muted"))

    def _paint_border(self, focused: bool) -> None:
        # Errors keep their color while focused, so the focus ring never hides a problem.
        colors = {"error": "signal_red", "highlight": "signal_amber"}
        if self.status in colors:
            token = colors[self.status]
        else:
            token = "accent" if focused else "border"
        self.entry.configure(border_color=color(token), border_width=2 if focused else 1)

    def _on_focus_in(self, _event) -> None:
        self.entry.select_range(0, "end")
        self._paint_border(focused=True)

    def _on_focus_out(self, _event) -> None:
        self._paint_border(focused=False)
        self._trim()

    def _trim(self) -> None:
        text = self.entry.get()
        # Only trim stray spaces; never rewrite what the user typed.
        if parse_number(text) is not None and text != text.strip():
            self.set(text.strip())

    def _check_shape(self, _event) -> None:
        # Editing means they're fixing it, so drop the old message first.
        self.clear_error()
        self._paint_border(focused=True)
        text = self.entry.get().strip()
        if not NUMBER_SHAPE.match(text):
            self.set_error("Numbers only")
            self._paint_border(focused=True)


# Widgets: YMeter

HEAVY_MARK = 0.85
TRACK_HEIGHT = 14


class YMeter(ctk.CTkFrame):
    def __init__(self, parent) -> None:
        super().__init__(parent, fg_color="transparent", height=0)
        self.columnconfigure(0, weight=1)

        self.caption = ctk.CTkLabel(
            self, text="Y = --", anchor="w",
            font=font(13, "bold", mono=True), text_color=color("text"),
        )
        self.caption.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            self, text="Capacity", anchor="e",
            font=font(11), text_color=color("text_muted"),
        ).grid(row=0, column=1, sticky="e")

        self.track = ctk.CTkFrame(
            self, height=TRACK_HEIGHT, corner_radius=TRACK_HEIGHT // 2,
            fg_color=color("surface_alt"),
        )
        self.track.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        self.fill = ctk.CTkFrame(self.track, corner_radius=TRACK_HEIGHT // 2)

        # A small tick where the intersection starts to get heavy.
        marks = ctk.CTkFrame(self, fg_color="transparent", height=24)
        marks.grid(row=2, column=0, columnspan=2, sticky="ew")
        ctk.CTkFrame(
            marks, width=2, height=6, corner_radius=0, fg_color=color("text_muted"),
        ).place(relx=HEAVY_MARK, y=0, anchor="n")
        ctk.CTkLabel(
            marks, text="heavy", height=16, font=font(10), text_color=color("text_muted"),
        ).place(relx=HEAVY_MARK, y=8, anchor="n")

        self.set_error()

    def set(self, value: float) -> None:
        self.caption.configure(text=f"Y = {value:.4f}")
        self._draw_fill(min(value, 1.0), self._color_for(value))

    def set_error(self) -> None:
        # Not enough valid numbers yet, so show an empty bar.
        self.caption.configure(text="Y = --")
        self._draw_fill(0, "signal_green")

    def _draw_fill(self, fraction: float, token: str) -> None:
        if fraction <= 0:
            self.fill.place_forget()
            return
        self.fill.configure(fg_color=color(token))
        self.fill.place(x=0, y=0, relheight=1, relwidth=fraction)

    @staticmethod
    def _color_for(value: float) -> str:
        if value >= 0.95:
            return "signal_red"
        if value >= 0.70:
            return "signal_amber"
        return "signal_green"


# Widgets: ModelCard

DIAGRAM_WIDTH = 120
DIAGRAM_HEIGHT = 56
# The mini diagram just repeats green, amber, red to hint at how many phases there are.
BAR_TOKENS = ("signal_green", "signal_amber", "signal_red")


class ModelCard(ctk.CTkFrame):
    def __init__(self, parent, model: PhaseModel, on_select: Callable[[str], None]) -> None:
        super().__init__(
            parent,
            corner_radius=RADIUS_CARD,
            height=0,
            border_width=1,
            fg_color=color("surface"),
            border_color=color("border"),
        )
        self.model = model
        self.on_select = on_select
        self.highlighted = False

        self.diagram = tk.Canvas(
            self, width=DIAGRAM_WIDTH, height=DIAGRAM_HEIGHT, highlightthickness=0, bd=0,
        )
        self.diagram.pack(anchor="w", padx=PAD_M, pady=(PAD_M, PAD_S))

        self.name = ctk.CTkLabel(
            self, text=model.name, anchor="w",
            font=font(18, serif=True), text_color=color("text"),
        )
        self.name.pack(fill="x", padx=PAD_M)

        self.description = ctk.CTkLabel(
            self, text=model.description, anchor="w", justify="left", wraplength=220,
            font=font(13), text_color=color("text_muted"),
        )
        self.description.pack(fill="x", padx=PAD_M, pady=(4, PAD_S))

        self.inputs = ctk.CTkLabel(
            self, text=f"{model.phase_count} volume inputs", anchor="w",
            font=font(12, "bold"), text_color=color("accent"),
        )
        self.inputs.pack(fill="x", padx=PAD_M, pady=(0, PAD_M))

        self._draw_diagram()
        self._wire_events()

    def _wire_events(self) -> None:
        # Clicks and hovers land on the labels and canvas too, so wire them all.
        for widget in (self, self.diagram, self.name, self.description, self.inputs):
            widget.bind("<Button-1>", self._select)
            widget.bind("<Enter>", self._on_enter)
            widget.bind("<Leave>", self._on_leave)
            # A hand cursor tells people the whole card can be clicked.
            widget.configure(cursor="hand2")

        # Make the card reachable with Tab, and selectable with Enter or Space.
        tk.Frame.configure(self, takefocus=True)
        self.bind("<FocusIn>", lambda _: self._highlight(True))
        self.bind("<FocusOut>", lambda _: self._highlight(False))
        self.bind("<Return>", self._select)
        self.bind("<space>", self._select)

    def _select(self, _event=None) -> None:
        self.focus_set()
        self.on_select(self.model.key)

    def _on_enter(self, _event) -> None:
        self._highlight(True)

    def _on_leave(self, event) -> None:
        # Moving onto a child label also fires Leave on the card; ignore that.
        under_pointer = self.winfo_containing(event.x_root, event.y_root)
        if under_pointer is not None and str(under_pointer).startswith(str(self)):
            return
        if self.focus_get() is not self:
            self._highlight(False)

    def _highlight(self, on: bool) -> None:
        self.highlighted = on
        self.configure(
            border_color=color("accent" if on else "border"),
            border_width=2 if on else 1,
        )

    def _draw_diagram(self) -> None:
        self.diagram.configure(bg=resolve("surface"))
        self.diagram.delete("all")

        count = self.model.phase_count
        gap = 3
        bar_width = (DIAGRAM_WIDTH - gap * (count - 1)) / count
        for i in range(count):
            left = i * (bar_width + gap)
            token = BAR_TOKENS[i % len(BAR_TOKENS)]
            self.diagram.create_rectangle(
                left, 8, left + bar_width, DIAGRAM_HEIGHT - 8,
                fill=resolve(token), outline="",
            )

    def _set_appearance_mode(self, mode_string: str) -> None:
        # The canvas can't switch colors on its own, so redraw when the theme flips.
        super()._set_appearance_mode(mode_string)
        self._draw_diagram()


# Widgets: StatCard

class StatCard(ctk.CTkFrame):
    def __init__(self, parent, caption: str, value: str, subtitle: str, accent: str | None = None) -> None:
        super().__init__(
            parent, corner_radius=RADIUS_CARD, border_width=1, height=0,
            fg_color=color("surface"), border_color=color("border"),
        )
        self.columnconfigure(0, weight=1)

        # A thin colored bar along the top marks the headline number.
        if accent:
            ctk.CTkFrame(
                self, height=3, corner_radius=0, fg_color=color(accent),
            ).grid(row=0, column=0, sticky="ew", padx=PAD_M)

        ctk.CTkLabel(
            self, text=caption.upper(), anchor="w",
            font=font(11), text_color=color("text_muted"),
        ).grid(row=1, column=0, sticky="ew", padx=PAD_M, pady=(PAD_M, 0))

        self.value = ctk.CTkLabel(
            self, text=value, anchor="w",
            font=font(32, "bold", mono=True),
            text_color=color(accent or "text"),
        )
        self.value.grid(row=2, column=0, sticky="ew", padx=PAD_M)

        self.subtitle = ctk.CTkLabel(
            self, text=subtitle, anchor="w", justify="left",
            font=font(12), text_color=color("text_muted"),
        )
        self.subtitle.grid(row=3, column=0, sticky="ew", padx=PAD_M, pady=(0, PAD_M))
        self.bind("<Configure>", self._wrap_subtitle)

        # Other widgets (like the Y meter) can be dropped in here, under the subtitle.
        self.extra = ctk.CTkFrame(self, fg_color="transparent", height=0)

    def update_values(self, value: str, subtitle: str) -> None:
        self.value.configure(text=value)
        self.subtitle.configure(text=subtitle)

    def add_extra(self, widget_factory):
        # Pass a function that builds the widget inside self.extra.
        self.extra.grid(row=4, column=0, sticky="ew", padx=PAD_M, pady=(0, PAD_M))
        widget = widget_factory(self.extra)
        widget.pack(fill="x")
        self.subtitle.grid_configure(pady=(0, PAD_S))
        return widget

    def _wrap_subtitle(self, event) -> None:
        # Wrap against the card width; the label's own width would feed back on itself.
        self.subtitle.configure(wraplength=max(self.winfo_width() - 2 * PAD_M, 80))


# Widgets: PhaseTable

# Phase code, label, then the four number columns.
HEADERS = ("Phase", "Volume (veh/hr)", "Flow ratio Yi", "Green (s)", "Share of Te")
# Each row gets its own dot color so the table can match the legend elsewhere.
DOT_TOKENS = (
    "accent", "signal_green", "signal_amber", "signal_red",
    "text_muted", "accent_hover", "border", "text",
)


class PhaseTable(ctk.CTkFrame):
    def __init__(self, parent) -> None:
        super().__init__(parent, fg_color="transparent", height=0)
        self.columnconfigure(0, weight=3)
        for column in range(1, len(HEADERS)):
            self.columnconfigure(column, weight=1)

    def set(self, result: TimingResult) -> None:
        for child in self.winfo_children():
            child.destroy()

        self._row(0, HEADERS, "surface_alt", bold=True)
        for index, phase in enumerate(result.phases):
            shade = "surface" if index % 2 == 0 else "surface_alt"
            cells = (
                None,
                f"{phase.volume:g}",
                f"{phase.flow_ratio:.4f}",
                str(phase.green),
                f"{phase.green_share * 100:.1f}%",
            )
            self._row(index + 1, cells, shade, phase=phase, dot=DOT_TOKENS[index % len(DOT_TOKENS)])

        totals = (
            "Total",
            f"{sum(p.volume for p in result.phases):g}",
            f"{result.total_flow_ratio:.4f}",
            str(result.effective_green),
            "100.0%",
        )
        self._row(len(result.phases) + 1, totals, "surface_alt", bold=True)

    def _row(self, row: int, cells, shade: str, bold: bool = False, phase=None, dot: str | None = None) -> None:
        for column, text in enumerate(cells):
            holder = ctk.CTkFrame(self, corner_radius=0, width=1, height=34, fg_color=color(shade))
            holder.grid(row=row, column=column, sticky="nsew")
            holder.grid_propagate(False)
            holder.columnconfigure(1 if column == 0 else 0, weight=1)

            if column == 0:
                self._phase_cell(holder, text, phase, dot, bold)
                continue

            ctk.CTkLabel(
                holder, text=text, anchor="e",
                font=font(12, "bold" if bold else "normal", mono=True),
                text_color=color("text"),
            ).grid(row=0, column=0, sticky="e", padx=PAD_M)

    def _phase_cell(self, holder, text, phase, dot, bold) -> None:
        if phase is None:
            # Header and totals rows have no dot, so the text starts where the dot would.
            ctk.CTkLabel(
                holder, text=text, anchor="w",
                font=font(12, "bold"), text_color=color("text"),
            ).grid(row=0, column=0, columnspan=2, sticky="w", padx=PAD_M)
            return

        ctk.CTkFrame(
            holder, width=8, height=8, corner_radius=4, fg_color=color(dot),
        ).grid(row=0, column=0, padx=(PAD_M, 6))
        ctk.CTkLabel(
            holder, text=f"{phase.code}  {phase.label}", anchor="w",
            font=font(12), text_color=color("text"),
        ).grid(row=0, column=1, sticky="w")


# Widgets: TimelineCanvas

ROW_HEIGHT = 34
ROW_STEP = 44
LABEL_WIDTH = 90
PLOT_LEFT = 100
PLOT_RIGHT_MARGIN = 16
TOP_MARGIN = 8
AXIS_SPACE = 48
MIN_TEXT_WIDTH = 36
REDRAW_DELAY_MS = 50
RED_STRENGTH = 0.35

KIND_NAMES = {"G": "Green", "YR": "Yellow / All-Red", "R": "Red"}
KIND_LETTERS = {"G": "G", "YR": "Y/R", "R": "R"}


def blend(foreground: str, background: str, amount: float) -> str:
    # Tk has no transparency, so a "faded" color is mixed into the background by hand.
    def channel(hex_color: str, start: int) -> int:
        return int(hex_color[start:start + 2], 16)

    mixed = [
        round(channel(foreground, i) * amount + channel(background, i) * (1 - amount))
        for i in (1, 3, 5)
    ]
    return "#{:02X}{:02X}{:02X}".format(*mixed)


def tick_step(cycle: int) -> int:
    if cycle <= 60:
        return 5
    if cycle <= 150:
        return 10
    return 25


class TimelineCanvas(ctk.CTkFrame):
    def __init__(self, parent) -> None:
        super().__init__(parent, fg_color="transparent", height=0)
        self.columnconfigure(0, weight=1)
        self.timeline: Timeline | None = None
        # Each hit is (left, top, right, bottom, tooltip text) in canvas pixels.
        self.hits: list[tuple[int, int, int, int, str]] = []
        self._redraw_job: str | None = None

        self._build_legend()
        self.canvas = tk.Canvas(self, highlightthickness=0, bd=0, height=ROW_STEP + AXIS_SPACE)
        self.canvas.grid(row=1, column=0, sticky="ew", pady=(PAD_S, 0))
        self.canvas.bind("<Configure>", self._schedule_redraw)
        self.canvas.bind("<Motion>", self._show_tooltip)
        self.canvas.bind("<Leave>", lambda _: self.canvas.delete("tip"))

    def _build_legend(self) -> None:
        legend = ctk.CTkFrame(self, fg_color="transparent", height=0)
        legend.grid(row=0, column=0, sticky="w")
        for token, text in (
            ("signal_green", "Green"),
            ("signal_amber", "Yellow / All-Red"),
            ("signal_red", "Red"),
        ):
            ctk.CTkFrame(
                legend, width=12, height=12, corner_radius=3, fg_color=color(token),
            ).pack(side="left", padx=(0, 6))
            ctk.CTkLabel(
                legend, text=text, font=font(11), text_color=color("text_muted"),
            ).pack(side="left", padx=(0, PAD_M))

    def draw(self, timeline: Timeline) -> None:
        self.timeline = timeline
        self.canvas.configure(height=len(timeline.rows) * ROW_STEP + AXIS_SPACE)
        self._redraw()

    def _schedule_redraw(self, _event=None) -> None:
        # Wait for the resize to settle so dragging the window stays smooth.
        if self._redraw_job:
            self.after_cancel(self._redraw_job)
        self._redraw_job = self.after(REDRAW_DELAY_MS, self._redraw)

    def _set_appearance_mode(self, mode_string: str) -> None:
        super()._set_appearance_mode(mode_string)
        self._redraw()

    def _redraw(self) -> None:
        self._redraw_job = None
        self.canvas.configure(bg=resolve("surface"))
        self.canvas.delete("all")
        self.hits = []

        plot_width = self.canvas.winfo_width() - PLOT_LEFT - PLOT_RIGHT_MARGIN
        if self.timeline is None or plot_width < 50:
            return

        self._draw_rows(plot_width)
        self._draw_phase_starts(plot_width)
        self._draw_axis(plot_width)

    def _segment_colors(self, kind: str) -> tuple[str, str]:
        # Returns (fill color, text color) for a segment kind.
        if kind == "G":
            return resolve("signal_green"), resolve("on_accent")
        if kind == "YR":
            # Dark text reads much better than white on amber.
            return resolve("signal_amber"), resolve("text")
        faded = blend(resolve("signal_red"), resolve("surface"), RED_STRENGTH)
        return faded, resolve("text")

    def _rows_bottom(self) -> int:
        return TOP_MARGIN + len(self.timeline.rows) * ROW_STEP - (ROW_STEP - ROW_HEIGHT)

    def _draw_rows(self, plot_width: int) -> None:
        cycle = self.timeline.cycle
        for index, row in enumerate(self.timeline.rows):
            top = TOP_MARGIN + index * ROW_STEP
            bottom = top + ROW_HEIGHT
            self.canvas.create_text(
                LABEL_WIDTH, (top + bottom) / 2, text=row.code, anchor="e",
                font=font(12, mono=True), fill=resolve("text"),
            )

            scaled = scale_segments(row, plot_width, cycle)
            for segment, (kind, x, width) in zip(row.segments, scaled):
                left = PLOT_LEFT + x
                right = left + width
                fill, text_color = self._segment_colors(kind)
                self.canvas.create_rectangle(left, top, right, bottom, fill=fill, outline="")

                end = segment.start + segment.duration
                name = KIND_NAMES[kind]
                self.hits.append((
                    left, top, right, bottom,
                    f"{row.code}: {name} {segment.duration}s (t = {segment.start} to {end}s)",
                ))
                if width >= MIN_TEXT_WIDTH:
                    self.canvas.create_text(
                        (left + right) / 2, (top + bottom) / 2,
                        text=f"{KIND_LETTERS[kind]} {segment.duration}s",
                        font=font(11, "bold"), fill=text_color,
                    )

    def _draw_phase_starts(self, plot_width: int) -> None:
        # A dashed line where each phase's green begins.
        for row in self.timeline.rows:
            green = next(s for s in row.segments if s.kind == "G")
            x = PLOT_LEFT + round(green.start / self.timeline.cycle * plot_width)
            self.canvas.create_line(
                x, TOP_MARGIN, x, self._rows_bottom(), dash=(3, 3), fill=resolve("text_muted"),
            )

    def _draw_axis(self, plot_width: int) -> None:
        cycle = self.timeline.cycle
        step = tick_step(cycle)
        y = self._rows_bottom() + 6

        self.canvas.create_line(PLOT_LEFT, y, PLOT_LEFT + plot_width, y, fill=resolve("border"))
        # Skip a regular tick that would sit right next to the final one at the cycle length.
        times = [t for t in range(0, cycle, step) if cycle - t >= step / 2] + [cycle]
        for t in times:
            x = PLOT_LEFT + round(t / cycle * plot_width)
            self.canvas.create_line(x, y, x, y + 5, fill=resolve("text_muted"))
            self.canvas.create_text(
                x, y + 8, text=str(t), anchor="n",
                font=font(10), fill=resolve("text_muted"),
            )
        self.canvas.create_text(
            PLOT_LEFT + plot_width, y + 26, text="seconds", anchor="e",
            font=font(10), fill=resolve("text_muted"),
        )

    def _show_tooltip(self, event) -> None:
        self.canvas.delete("tip")
        for left, top, right, bottom, text in self.hits:
            if left <= event.x < right and top <= event.y <= bottom:
                self._draw_tooltip(event.x, event.y, text)
                return

    def _draw_tooltip(self, x: int, y: int, text: str) -> None:
        label = self.canvas.create_text(
            x + 12, y - 14, text=text, anchor="sw", tags="tip",
            font=font(11), fill=resolve("text"),
        )
        left, top, right, bottom = self.canvas.bbox(label)
        # Nudge it left if it would run off the right edge.
        shift = max(0, right + 6 - self.canvas.winfo_width())
        self.canvas.move(label, -shift, 0)
        box = self.canvas.create_rectangle(
            left - 6 - shift, top - 3, right + 6 - shift, bottom + 3, tags="tip",
            fill=resolve("surface_alt"), outline=resolve("border"),
        )
        self.canvas.tag_raise(label, box)


# Screens: ModelSelectScreen

WIDE_LAYOUT_MIN_WIDTH = 900
RELAYOUT_DELAY_MS = 100


class ModelSelectScreen(ctk.CTkFrame):
    def __init__(self, parent, app) -> None:
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.columns = 0
        self._relayout_job: str | None = None

        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        ctk.CTkLabel(
            self, text="Choose a phase model", anchor="w",
            font=font(28, serif=True), text_color=color("text"),
        ).grid(row=0, column=0, sticky="ew", padx=PAD_L, pady=(PAD_L, 0))
        ctk.CTkLabel(
            self, text="Pick the signal phasing that matches your intersection.", anchor="w",
            font=font(13), text_color=color("text_muted"),
        ).grid(row=1, column=0, sticky="ew", padx=PAD_L, pady=(4, PAD_M))

        self.grid_area = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.grid_area.grid(row=2, column=0, sticky="nsew", padx=PAD_L)
        self.cards = [ModelCard(self.grid_area, model, self._choose) for model in MODELS.values()]

        Banner(
            self, "info", "Phases with a volume of 0 are left out of the cycle.",
        ).grid(row=3, column=0, sticky="ew", padx=PAD_L, pady=PAD_M)

        self.bind("<Configure>", self._on_resize)
        self._layout_cards(3)

    def _choose(self, model_key: str) -> None:
        # Keep what the user typed if they pick the same model again.
        if model_key != self.app.model_key:
            self.app.form_values = {}
        self.app.model_key = model_key
        self.app.show("inputs")

    def _on_resize(self, _event) -> None:
        # Wait for the resize to settle so we don't re-grid on every pixel.
        if self._relayout_job:
            self.after_cancel(self._relayout_job)
        self._relayout_job = self.after(RELAYOUT_DELAY_MS, self._relayout)

    def _relayout(self) -> None:
        self._relayout_job = None
        wide = self.winfo_width() >= WIDE_LAYOUT_MIN_WIDTH
        self._layout_cards(3 if wide else 2)

    def _layout_cards(self, columns: int) -> None:
        if columns == self.columns:
            return
        self.columns = columns
        for index in range(3):
            self.grid_area.columnconfigure(index, weight=0, uniform="")
        for index in range(columns):
            self.grid_area.columnconfigure(index, weight=1, uniform="cards")
        for index, card in enumerate(self.cards):
            row, column = divmod(index, columns)
            card.grid(
                row=row, column=column, sticky="nsew",
                padx=PAD_S, pady=PAD_S,
            )


# Screens: InputFormScreen

STACK_BELOW_WIDTH = 760
GLOBAL_KEYS = ("saturation_flow", "lost_time")

# One filled-in example per model, so people can see the app work in one click.
# These are the reference cases from the PRD. Phases not listed get 0.
EXAMPLES = {
    "2": {"NS": "850", "EW": "600"},
    "3": {"MajThru": "800", "MajLeft": "300", "MinStem": "450"},
    "4": {"NSL": "200", "NST": "700", "EWL": "150", "EWT": "600"},
    "6": {"NBL": "250", "ArtThru": "900", "MinEB": "500"},
    "8": {"NBL": "150", "SBT": "600", "EBL": "150", "WBT": "500"},
}
EXAMPLE_SATURATION = "1900"
EXAMPLE_LOST_TIME = "4"


class InputFormScreen(ctk.CTkFrame):
    def __init__(self, parent, app) -> None:
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.built_for: str | None = None
        self.entries: dict[str, LabeledEntry] = {}
        self.stacked: bool | None = None
        self._relayout_job: str | None = None

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self._build_header()
        self._build_body()
        self._build_footer()
        for key in GLOBAL_KEYS:
            self._wire_entry(self.entries[key])
        self.bind("<Configure>", self._on_resize)

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=PAD_L, pady=(PAD_L, PAD_M))
        header.columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header, text="Model / Inputs", anchor="w",
            font=font(11), text_color=color("text_muted"),
        ).grid(row=0, column=0, sticky="w")
        self.title = ctk.CTkLabel(
            header, text="", anchor="w",
            font=font(28, serif=True), text_color=color("text"),
        )
        self.title.grid(row=1, column=0, sticky="w")
        ctk.CTkButton(
            header, text="Change model", width=0, height=32, font=font(13),
            fg_color="transparent", hover_color=color("surface_alt"),
            text_color=color("accent"),
            command=lambda: self.app.show("model"),
        ).grid(row=0, column=1, rowspan=2, sticky="e")

    def _build_body(self) -> None:
        self.body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.body.grid(row=1, column=0, sticky="nsew", padx=(PAD_L, PAD_S))

        self.card_a = Card(self.body, "Intersection parameters")
        self.entries["saturation_flow"] = LabeledEntry(
            self.card_a, "Saturation flow rate", "veh/hr/lane",
            "Typical 1800 to 1900", placeholder="1900",
        )
        self.entries["lost_time"] = LabeledEntry(
            self.card_a, "Lost time per phase", "s",
            "Amber + all-red, whole seconds", placeholder="4",
        )
        for row, key in enumerate(GLOBAL_KEYS, start=1):
            self.entries[key].grid(row=row, column=0, sticky="ew", padx=PAD_M, pady=(0, PAD_M))

        self.card_b = Card(self.body, "Traffic volumes")
        self.volume_grid = ctk.CTkFrame(self.card_b, fg_color="transparent")
        self.volume_grid.grid(row=1, column=0, sticky="ew", padx=PAD_M)
        for column in range(2):
            self.volume_grid.columnconfigure(column, weight=1, uniform="volumes")

    def _build_footer(self) -> None:
        footer = ctk.CTkFrame(
            self, corner_radius=RADIUS_CARD, border_width=1, height=0,
            fg_color=color("surface"), border_color=color("border"),
        )
        footer.grid(row=2, column=0, sticky="ew", padx=PAD_L, pady=PAD_M)
        footer.columnconfigure(0, weight=1)

        self.meter = YMeter(footer)
        self.meter.grid(row=0, column=0, sticky="ew", padx=PAD_M, pady=(PAD_M, 0))
        self.banner = Banner(footer, "error", "")
        self.banner.grid(row=2, column=0, sticky="ew", padx=PAD_M, pady=(PAD_S, 0))
        self.banner.hide()

        self.buttons = ctk.CTkFrame(footer, fg_color="transparent")
        self.buttons.grid(row=3, column=0, sticky="ew", padx=PAD_M, pady=PAD_M)
        ctk.CTkButton(
            self.buttons, text="Calculate", width=130, height=36, font=font(13, "bold"),
            corner_radius=RADIUS_INPUT, fg_color=color("accent"),
            hover_color=color("accent_hover"), text_color=color("on_accent"),
            command=self._on_calculate,
        ).pack(side="right")
        ctk.CTkButton(
            self.buttons, text="Reset", width=90, height=36, font=font(13),
            corner_radius=RADIUS_INPUT, fg_color="transparent", border_width=1,
            border_color=color("border"), hover_color=color("surface_alt"),
            text_color=color("text"), command=self._on_reset,
        ).pack(side="left", padx=(0, PAD_S))
        ctk.CTkButton(
            self.buttons, text="Fill example", width=0, height=36, font=font(13),
            fg_color="transparent", hover_color=color("surface_alt"),
            text_color=color("accent"), command=self._on_fill_example,
        ).pack(side="left")
        # Sits in the button row to keep the footer short on small windows.
        self.count_label = ctk.CTkLabel(
            self.buttons, text="", anchor="w",
            font=font(12), text_color=color("text_muted"),
        )
        self.count_label.pack(side="left", padx=PAD_M)

    # Showing the screen and building the fields

    def on_show(self) -> None:
        model = MODELS[self.app.model_key]
        self.title.configure(text=f"{model.name} inputs")
        if self.built_for != model.key:
            self._rebuild_volumes(model.key)
        self._restore_values()
        self._clear_feedback()
        self._update_live_feedback()
        self._layout_cards(force=True)

    def _rebuild_volumes(self, model_key: str) -> None:
        for key in [k for k in self.entries if k not in GLOBAL_KEYS]:
            self.entries.pop(key).destroy()

        for index, phase in enumerate(MODELS[model_key].phases):
            entry = LabeledEntry(self.volume_grid, phase.label, "veh/hr", phase.hint)
            row, column = divmod(index, 2)
            entry.grid(row=row, column=column, sticky="ew", padx=PAD_S, pady=(0, PAD_M))
            self.entries[phase.code] = entry
            self._wire_entry(entry)
        self.built_for = model_key

    def _wire_entry(self, entry: LabeledEntry) -> None:
        entry.bind_change(self._on_change)
        entry.bind_enter(self._on_calculate)

    def _restore_values(self) -> None:
        # Global values survive a model switch; keys that no longer exist are simply dropped.
        for key, entry in self.entries.items():
            entry.set(self.app.form_values.get(key, ""))

    # Layout

    def _on_resize(self, _event) -> None:
        if self._relayout_job:
            self.after_cancel(self._relayout_job)
        self._relayout_job = self.after(RELAYOUT_DELAY_MS, self._layout_cards)

    def _layout_cards(self, force: bool = False) -> None:
        self._relayout_job = None
        stacked = self.winfo_width() < STACK_BELOW_WIDTH
        if stacked == self.stacked and not force:
            return
        self.stacked = stacked

        self.card_a.grid_forget()
        self.card_b.grid_forget()
        self.body.columnconfigure(0, weight=1)
        self.body.columnconfigure(1, weight=0 if stacked else 1)
        if stacked:
            self.card_a.grid(row=0, column=0, sticky="new", pady=(0, PAD_M))
            self.card_b.grid(row=1, column=0, sticky="new")
        else:
            self.card_a.grid(row=0, column=0, sticky="new", padx=(0, PAD_S))
            self.card_b.grid(row=0, column=1, sticky="new", padx=(PAD_S, 0))

    # Live feedback

    def _on_change(self) -> None:
        self.app.form_values = {key: entry.get() for key, entry in self.entries.items()}
        # Any edit makes an old result out of date, so Results waits for the next Calculate.
        if self.app.result is not None:
            self.app.result = None
            self.app.update_nav()
        self._update_live_feedback()

    def _update_live_feedback(self) -> None:
        saturation = parse_number(self.entries["saturation_flow"].get())
        phases = MODELS[self.built_for].phases

        volumes = []
        for phase in phases:
            value = parse_number(self.entries[phase.code].get())
            if value is not None:
                volumes.append(max(value, 0))

        active = sum(1 for v in volumes if v > 0)
        self.count_label.configure(text=f"{active} of {len(phases)} phases active")

        if saturation and saturation > 0 and volumes:
            self.meter.set(sum(v / saturation for v in volumes))
        else:
            self.meter.set_error()

    def _clear_feedback(self) -> None:
        self.banner.hide()
        for entry in self.entries.values():
            entry.clear_error()

    # Buttons

    def _on_reset(self) -> None:
        for entry in self.entries.values():
            entry.set("")
        self._clear_feedback()
        self._on_change()

    def _on_fill_example(self) -> None:
        example = EXAMPLES[self.built_for]
        self.entries["saturation_flow"].set(EXAMPLE_SATURATION)
        self.entries["lost_time"].set(EXAMPLE_LOST_TIME)
        for phase in MODELS[self.built_for].phases:
            self.entries[phase.code].set(example.get(phase.code, "0"))
        self._clear_feedback()
        self._on_change()

    # Calculate and the two retry loops

    def _on_calculate(self) -> None:
        self._clear_feedback()
        try:
            self._calculate()
        except (ValueError, ZeroDivisionError):
            # Safety net only. Validation should already have caught anything odd.
            self._show_error("Unexpected input problem. Check the values and try again.")

    def _calculate(self) -> None:
        raw = {key: entry.get() for key, entry in self.entries.items()}
        timing_input, errors = validate_inputs(self.app.model_key, raw)

        if errors:
            self._show_field_errors(errors)
            return

        result = compute_timing(timing_input)
        if result.oversaturated:
            self._show_oversaturation(result)
            return

        self.app.timing_input = timing_input
        self.app.result = result
        self.app.show("results")

    def _show_field_errors(self, errors) -> None:
        # Nothing is cleared here: the user keeps everything they typed and just fixes the marked fields.
        volume_keys = [k for k in self.entries if k not in GLOBAL_KEYS]
        for error in errors:
            targets = volume_keys if error.field == "volumes" else [error.field]
            for key in targets:
                self.entries[key].set_error(error.message)

        marked = {key for error in errors for key in (volume_keys if error.field == "volumes" else [error.field])}
        first = next(key for key in self.entries if key in marked)
        self.entries[first].focus()
        self._show_error(f"Please fix {len(errors)} field(s) to continue.")

    def _show_oversaturation(self, result) -> None:
        busiest = sorted(result.phases, key=lambda p: p.flow_ratio, reverse=True)[:2]
        names = ", ".join(f"{p.code} ({p.flow_ratio:.3f})" for p in busiest)
        self._show_error(
            f"{result.message} Largest demand: {names}. "
            "Reduce volumes or add capacity, then try again."
        )
        self.meter.set(result.total_flow_ratio)
        for phase in busiest:
            self.entries[phase.code].set_highlight()

    def _show_error(self, text: str) -> None:
        self.banner.set("error", text)
        self.banner.show()


# Screens: ResultsScreen

TWO_BY_TWO_BELOW_WIDTH = 760
COPIED_MESSAGE_MS = 1500
TEXT_MARGIN = 120  # scrollbar, card padding and body padding around the wrapped text


def formula_lines(result: TimingResult, saturation_flow: float, lost_time: int) -> list[str]:
    # The same numbers the app used, written out so a student can check them by hand.
    lines = []
    for p in result.phases:
        lines.append(f"Y({p.code}) = {p.volume:g} / {saturation_flow:g} = {p.flow_ratio:.4f}")

    ratios = " + ".join(f"{p.flow_ratio:.4f}" for p in result.phases)
    lines.append(f"Y = {ratios} = {result.total_flow_ratio:.4f}")
    lines.append(f"L = {result.active_count} x {lost_time} = {result.total_lost_time} s")
    lines.append(
        f"Co = (1.5 x {result.total_lost_time} + 5) / (1 - {result.total_flow_ratio:.4f})"
        f" = {result.raw_cycle:.2f} s"
    )
    lines.append(f"C = {result.cycle} s (rounded up to the next 5 s)")
    lines.append(f"Te = {result.cycle} - {result.total_lost_time} = {result.effective_green} s")
    for p in result.phases:
        exact = p.flow_ratio / result.total_flow_ratio * result.effective_green
        lines.append(
            f"g({p.code}) = ({p.flow_ratio:.4f} / {result.total_flow_ratio:.4f})"
            f" x {result.effective_green} = {exact:.2f} -> {p.green} s"
        )
    return lines


class ResultsScreen(ctk.CTkFrame):
    def __init__(self, parent, app) -> None:
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.report_text = ""
        self.stat_columns: int | None = None
        self._relayout_job: str | None = None

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.body.grid(row=0, column=0, sticky="nsew", padx=(PAD_L, PAD_S), pady=(PAD_S, 0))
        self.body.columnconfigure(0, weight=1)

        self._build_header()
        self.warning_area = ctk.CTkFrame(self.body, fg_color="transparent", height=0)
        self.warning_area.grid(row=1, column=0, sticky="ew")
        self.warning_area.columnconfigure(0, weight=1)
        self._build_stat_cards()
        self._build_cards()
        self._build_actions()

        self.bind("<Configure>", self._on_resize)
        # Keyboard shortcuts live on the window, but only act while this screen is showing.
        window = self.winfo_toplevel()
        window.bind("<Escape>", self._on_escape, add="+")
        window.bind("<Control-c>", self._on_ctrl_c, add="+")

    # Building the pieces

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self.body, fg_color="transparent", height=0)
        header.grid(row=0, column=0, sticky="ew", pady=(PAD_S, PAD_M))
        ctk.CTkLabel(
            header, text="Model / Inputs / Results", anchor="w",
            font=font(11), text_color=color("text_muted"),
        ).pack(fill="x")
        self.title = ctk.CTkLabel(
            header, text="", anchor="w",
            font=font(28, serif=True), text_color=color("text"),
        )
        self.title.pack(fill="x")
        self.subtitle = ctk.CTkLabel(
            header, text="", anchor="w",
            font=font(13), text_color=color("text_muted"),
        )
        self.subtitle.pack(fill="x")

    def _build_stat_cards(self) -> None:
        self.stat_area = ctk.CTkFrame(self.body, fg_color="transparent", height=0)
        self.stat_area.grid(row=2, column=0, sticky="ew", pady=(PAD_M, 0))

        self.cycle_card = StatCard(self.stat_area, "Optimal cycle length (Co)", "", "", accent="accent")
        self.green_card = StatCard(self.stat_area, "Total effective green (Te)", "", "")
        self.flow_card = StatCard(self.stat_area, "Total flow ratio (Y)", "", "")
        self.meter: YMeter = self.flow_card.add_extra(YMeter)
        self.lost_card = StatCard(self.stat_area, "Total lost time (L)", "", "")
        self.stat_cards = [self.cycle_card, self.green_card, self.flow_card, self.lost_card]

    def _build_cards(self) -> None:
        table_card = Card(self.body, "Phase green times")
        table_card.grid(row=3, column=0, sticky="ew", pady=(PAD_M, 0))
        self.table = PhaseTable(table_card)
        self.table.grid(row=1, column=0, sticky="ew", padx=PAD_M, pady=(0, PAD_M))

        timeline_card = Card(self.body, "Phase timeline")
        timeline_card.grid(row=4, column=0, sticky="ew", pady=(PAD_M, 0))
        self.timeline_view = TimelineCanvas(timeline_card)
        self.timeline_view.grid(row=1, column=0, sticky="ew", padx=PAD_M, pady=(0, PAD_M))

        self.narrative_labels: dict[str, ctk.CTkLabel] = {}
        for offset, title in enumerate(("Summary", "Description", "Results", "Discussion")):
            card = Card(self.body, title)
            card.grid(row=5 + offset, column=0, sticky="ew", pady=(PAD_M, 0))
            label = ctk.CTkLabel(
                card, text="", anchor="w", justify="left", wraplength=500,
                font=font(13), text_color=color("text"),
            )
            label.grid(row=1, column=0, sticky="ew", padx=PAD_M, pady=(0, PAD_M))
            self.narrative_labels[title] = label

        formula_card = Card(self.body, "Formulas used")
        formula_card.grid(row=9, column=0, sticky="ew", pady=PAD_M)
        self.formulas = ctk.CTkLabel(
            formula_card, text="", anchor="w", justify="left",
            font=font(12, mono=True), text_color=color("text"),
        )
        self.formulas.grid(row=1, column=0, sticky="ew", padx=PAD_M, pady=(0, PAD_M))

    def _build_actions(self) -> None:
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=1, column=0, sticky="ew", padx=PAD_L, pady=PAD_M)

        self.copy_button = ctk.CTkButton(
            bar, text="Copy results", width=140, height=36, font=font(13, "bold"),
            corner_radius=RADIUS_INPUT, fg_color=color("accent"),
            hover_color=color("accent_hover"), text_color=color("on_accent"),
            command=self._copy_report,
        )
        self.copy_button.pack(side="left", padx=(0, PAD_S))
        ctk.CTkButton(
            bar, text="Edit inputs", width=110, height=36, font=font(13),
            corner_radius=RADIUS_INPUT, fg_color="transparent", border_width=1,
            border_color=color("border"), hover_color=color("surface_alt"),
            text_color=color("text"), command=lambda: self.app.show("inputs"),
        ).pack(side="left", padx=(0, PAD_S))
        ctk.CTkButton(
            bar, text="New calculation", width=0, height=36, font=font(13),
            fg_color="transparent", hover_color=color("surface_alt"),
            text_color=color("accent"), command=self.app.reset,
        ).pack(side="left")

    # Showing the screen

    def on_show(self) -> None:
        result = self.app.result
        data = self.app.timing_input
        if result is None or data is None:
            self.app.show("inputs")
            return

        timeline = build_timeline(result, data.lost_time)
        self.report_text = render_report(result, data.saturation_flow, data.lost_time)

        self.title.configure(text=f"{result.model.name} results")
        self.subtitle.configure(
            text=f"Saturation flow {data.saturation_flow:g} veh/hr/lane, "
                 f"lost time {data.lost_time} s per phase"
        )
        self._show_warnings(result.warnings)
        self._fill_stat_cards(result, data.lost_time)
        self.table.set(result)
        self.timeline_view.draw(timeline)
        self._fill_narrative(result, data.saturation_flow, data.lost_time)
        self.formulas.configure(text="\n".join(formula_lines(result, data.saturation_flow, data.lost_time)))
        self._layout_stat_cards(force=True)

    def _show_warnings(self, warnings: list[str]) -> None:
        for child in self.warning_area.winfo_children():
            child.destroy()
        # An empty area would still leave a gap, so only show it when there is something to say.
        if warnings:
            self.warning_area.grid()
        else:
            self.warning_area.grid_remove()
        for row, text in enumerate(warnings):
            Banner(self.warning_area, "warning", text).grid(
                row=row, column=0, sticky="ew", pady=(0, PAD_S),
            )

    def _fill_stat_cards(self, result: TimingResult, lost_time: int) -> None:
        self.cycle_card.update_values(
            f"{result.cycle} s", f"Webster raw: {result.raw_cycle:.2f} s, rounded up to 5 s",
        )
        self.green_card.update_values(
            f"{result.effective_green} s", f"Cycle minus {result.total_lost_time} s lost time",
        )
        self.flow_card.update_values(
            f"{result.total_flow_ratio:.4f}", f"{result.active_count} active phases",
        )
        self.meter.set(result.total_flow_ratio)
        self.lost_card.update_values(
            f"{result.total_lost_time} s", f"{result.active_count} phases x {lost_time} s",
        )

    def _fill_narrative(self, result: TimingResult, saturation_flow: float, lost_time: int) -> None:
        for title, text in build_narrative(result, saturation_flow, lost_time):
            self.narrative_labels[title].configure(text=text)
        self._wrap_narrative()

    def _wrap_narrative(self) -> None:
        wrap = max(self.winfo_width() - TEXT_MARGIN, 200)
        for label in self.narrative_labels.values():
            label.configure(wraplength=wrap)

    # Layout

    def _on_resize(self, _event) -> None:
        if self._relayout_job:
            self.after_cancel(self._relayout_job)
        self._relayout_job = self.after(RELAYOUT_DELAY_MS, self._layout_stat_cards)

    def _layout_stat_cards(self, force: bool = False) -> None:
        self._relayout_job = None
        self._wrap_narrative()
        columns = 2 if self.winfo_width() < TWO_BY_TWO_BELOW_WIDTH else 4
        if columns == self.stat_columns and not force:
            return
        self.stat_columns = columns

        # Columns that are no longer used must drop out of the equal-width group too.
        for index in range(4):
            used = index < columns
            self.stat_area.columnconfigure(
                index, weight=1 if used else 0, uniform="stats" if used else "",
            )
        for index, card in enumerate(self.stat_cards):
            row, column = divmod(index, columns)
            card.grid(row=row, column=column, sticky="nsew", padx=PAD_S // 2, pady=PAD_S // 2)

    # Actions

    def _copy_report(self) -> None:
        self.clipboard_clear()
        self.clipboard_append(self.report_text)
        self.copy_button.configure(text="Copied")
        self.after(COPIED_MESSAGE_MS, lambda: self.copy_button.configure(text="Copy results"))

    def _on_escape(self, _event) -> None:
        if self.app.current == "results":
            self.app.show("inputs")

    def _on_ctrl_c(self, _event) -> None:
        if self.app.current != "results":
            return
        self._copy_report()


# App

WINDOW_WIDTH = 1120
WINDOW_HEIGHT = 720
SIDEBAR_WIDTH = 220
NAV_HEIGHT = 36
ICON_PATH = str(Path(__file__).resolve().parent / "assets" / "flow.ico")


class FlowApp(ctk.CTk):
    def __init__(self) -> None:
        # Both of these have to be set before the window exists.
        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")
        super().__init__(fg_color=color("bg"))

        self.title("FLOW | Traffic Signal Timing Optimizer")
        self.minsize(960, 640)
        self._center_window()
        # CustomTkinter sets its own icon a moment after startup, so ours goes in after that.
        self.after(250, self._set_icon)

        # State shared by every screen.
        self.model_key: str | None = None
        self.form_values: dict[str, str] = {}
        self.result: TimingResult | None = None
        self.timing_input: TimingInput | None = None

        self.columnconfigure(0, weight=0, minsize=SIDEBAR_WIDTH)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        self.current: str | None = None
        self._build_sidebar()
        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.columnconfigure(0, weight=1)
        self.content.rowconfigure(0, weight=1)

        self.screens: dict[str, ctk.CTkFrame] = {
            "model": ModelSelectScreen(self.content, self),
            "inputs": InputFormScreen(self.content, self),
            "results": ResultsScreen(self.content, self),
        }
        self.show("model")

    def _set_icon(self) -> None:
        try:
            self.iconbitmap(ICON_PATH)
        except tk.TclError:
            # A missing icon is not worth stopping the app for.
            pass

    def _center_window(self) -> None:
        x = (self.winfo_screenwidth() - WINDOW_WIDTH) // 2
        y = (self.winfo_screenheight() - WINDOW_HEIGHT) // 2
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}+{max(x, 0)}+{max(y, 0)}")

    def _build_sidebar(self) -> None:
        sidebar = ctk.CTkFrame(
            self, width=SIDEBAR_WIDTH, corner_radius=0, fg_color=color("surface_alt"),
        )
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        sidebar.rowconfigure(2, weight=1)

        ctk.CTkLabel(
            sidebar, text="FLOW", anchor="w",
            font=font(24, "bold", serif=True), text_color=color("accent"),
        ).grid(row=0, column=0, sticky="ew", padx=PAD_M, pady=(PAD_L, 0))
        ctk.CTkLabel(
            sidebar, text="Signal Timing Optimizer", anchor="w",
            font=font(11), text_color=color("text_muted"),
        ).grid(row=1, column=0, sticky="ew", padx=PAD_M, pady=(0, PAD_L))

        nav = ctk.CTkFrame(sidebar, fg_color="transparent")
        nav.grid(row=2, column=0, sticky="new", padx=PAD_S)
        nav.columnconfigure(0, weight=1)
        self.nav_buttons = {
            "model": self._nav_button(nav, "New calculation", self.reset),
            "inputs": self._nav_button(nav, "Inputs", lambda: self.show("inputs")),
            "results": self._nav_button(nav, "Results", lambda: self.show("results")),
        }
        for row, button in enumerate(self.nav_buttons.values()):
            button.grid(row=row, column=0, sticky="ew", pady=2)

        bottom = ctk.CTkFrame(sidebar, fg_color="transparent")
        bottom.grid(row=3, column=0, sticky="ew", padx=PAD_M, pady=PAD_M)
        bottom.columnconfigure(0, weight=1)
        ctk.CTkLabel(
            bottom, text="Appearance", anchor="w",
            font=font(11), text_color=color("text_muted"),
        ).grid(row=0, column=0, sticky="ew", pady=(0, 4))
        appearance = ctk.CTkSegmentedButton(
            bottom, values=["Light", "Dark", "System"], font=font(11),
            command=lambda mode: ctk.set_appearance_mode(mode.lower()),
            fg_color=color("border"),
            selected_color=color("accent"),
            selected_hover_color=color("accent_hover"),
            unselected_color=color("border"),
            unselected_hover_color=color("surface"),
            text_color=color("text"),
        )
        appearance.grid(row=1, column=0, sticky="ew")
        # set() only picks the starting option; it doesn't fire the callback.
        appearance.set("System")
        ctk.CTkLabel(
            bottom, text="ENGG 1035 | Webster's Method", anchor="w",
            font=font(10), text_color=color("text_muted"),
        ).grid(row=2, column=0, sticky="ew", pady=(PAD_M, 0))

    def _nav_button(self, parent, text: str, command) -> ctk.CTkButton:
        return ctk.CTkButton(
            parent, text=text, command=command, anchor="w", height=NAV_HEIGHT,
            corner_radius=RADIUS_INPUT, font=font(13),
            fg_color="transparent", hover_color=color("border"),
            text_color=color("text"), text_color_disabled=color("text_muted"),
        )

    def show(self, name: str) -> None:
        if self.current:
            self.screens[self.current].grid_remove()
        self.current = name
        screen = self.screens[name]
        screen.grid(row=0, column=0, sticky="nsew")
        if hasattr(screen, "on_show"):
            screen.on_show()
        self.update_nav()

    def reset(self) -> None:
        self.model_key = None
        self.form_values = {}
        self.result = None
        self.timing_input = None
        self.show("model")

    def update_nav(self) -> None:
        # Inputs need a chosen model; Results need a finished calculation.
        enabled = {
            "model": True,
            "inputs": self.model_key is not None,
            "results": self.result is not None,
        }
        for name, button in self.nav_buttons.items():
            is_active = name == self.current
            button.configure(
                state="normal" if enabled[name] else "disabled",
                fg_color=color("surface") if is_active else "transparent",
                text_color=color("accent") if is_active else color("text"),
            )


def main() -> None:
    app = FlowApp()
    app.mainloop()


if __name__ == "__main__":
    main()
