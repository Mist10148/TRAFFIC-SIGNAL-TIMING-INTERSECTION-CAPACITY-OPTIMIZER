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
