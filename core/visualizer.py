from dataclasses import dataclass

from core.models import TimingResult


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


def _block(segment: Segment) -> str:
    if segment.kind == "G":
        return f"[=== G ({segment.duration}s) ===]"
    if segment.kind == "YR":
        return f"[Y/R: {segment.duration}s]"
    return f"[----- R ({segment.duration}s) -----]"


# The spec's sample output pads labels to 10 characters, so that's the minimum.
MIN_LABEL_WIDTH = 10


def render_text(timeline: Timeline) -> str:
    lines = [f"--- VISUAL PHASE DIAGRAM ({timeline.cycle}-Second Cycle) ---"]
    width = max(MIN_LABEL_WIDTH, max(len(row.code) for row in timeline.rows) + 1)
    for row in timeline.rows:
        blocks = "".join(_block(s) for s in row.segments)
        lines.append(f"{row.code:<{width}}: {blocks}")
    return "\n".join(lines)


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


def render_report(
    result: TimingResult, timeline: Timeline, saturation_flow: float, lost_time: float
) -> str:
    sections = [
        _inputs_section(result, saturation_flow, lost_time),
        _variables_section(result),
        _output_section(result),
    ]
    if result.warnings:
        sections.append(["WARNINGS"] + [f"- {w}" for w in result.warnings])
    sections.append([render_text(timeline)])
    return "\n\n".join("\n".join(lines) for lines in sections)


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
