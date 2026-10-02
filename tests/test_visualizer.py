import pytest

from core.calculator import compute_timing
from core.models import MODELS, TimingInput
from core.visualizer import Segment, build_timeline, render_text

SATURATION = 1900
LOST = 4

CASE_1_TEXT = (
    "--- VISUAL PHASE DIAGRAM (75-Second Cycle) ---\n"
    "NS        : [=== G (39s) ===][Y/R: 4s][----- R (32s) -----]\n"
    "EW        : [----- R (43s) -----][=== G (28s) ===][Y/R: 4s]"
)

# Same five cases as the calculator tests: (model, volumes)
CASES = [
    ("2", {"NS": 850, "EW": 600}),
    ("3", {"MajThru": 800, "MajLeft": 300, "MinStem": 450}),
    ("4", {"NSL": 200, "NST": 700, "EWL": 150, "EWT": 600}),
    ("6", {"NBL": 250, "ArtThru": 900, "MinEB": 500}),
    ("8", {"NBL": 150, "SBT": 600, "EBL": 150, "WBT": 500}),
]


def solve(model_key: str, **volumes: float):
    full = {p.code: volumes.get(p.code, 0) for p in MODELS[model_key].phases}
    return compute_timing(TimingInput(model_key, SATURATION, LOST, full))


def test_case_1_text_matches_spec_exactly():
    timeline = build_timeline(solve("2", NS=850, EW=600), LOST)

    assert render_text(timeline) == CASE_1_TEXT


def test_three_phase_layout():
    result = solve("3", MajThru=800, MajLeft=300, MinStem=450)
    timeline = build_timeline(result, LOST)
    lines = render_text(timeline).split("\n")

    assert [row.code for row in timeline.rows] == ["MajThru", "MajLeft", "MinStem"]
    assert [p.green for p in result.phases] == [58, 22, 33]
    # Short codes still get the 10-wide label column from the spec.
    assert lines[1].index(":") == 10
    assert timeline.rows[0].segments[0].kind == "G"
    assert timeline.rows[-1].segments[-1].kind == "YR"


@pytest.mark.parametrize("model_key, volumes", CASES)
def test_every_row_adds_up_and_is_contiguous(model_key, volumes):
    timeline = build_timeline(solve(model_key, **volumes), LOST)

    for row in timeline.rows:
        assert sum(s.duration for s in row.segments) == timeline.cycle
        for prev, nxt in zip(row.segments, row.segments[1:]):
            assert nxt.start == prev.start + prev.duration


@pytest.mark.parametrize("model_key, volumes", CASES)
def test_each_phase_has_one_green_and_one_lost_time_block(model_key, volumes):
    timeline = build_timeline(solve(model_key, **volumes), LOST)

    for row in timeline.rows:
        kinds = [s.kind for s in row.segments]
        assert kinds.count("G") == 1
        assert kinds.count("YR") == 1


def test_single_active_phase_has_no_red():
    timeline = build_timeline(solve("2", NS=600), LOST)

    assert len(timeline.rows) == 1
    assert [s.kind for s in timeline.rows[0].segments] == ["G", "YR"]


def test_oversaturated_result_is_rejected():
    result = solve("2", NS=1200, EW=800)

    with pytest.raises(ValueError, match="non-oversaturated"):
        build_timeline(result, LOST)


def test_broken_row_is_caught():
    # Greens that don't fill the cycle must not slip through quietly.
    result = solve("2", NS=850, EW=600)
    result.phases[0].green += 1

    with pytest.raises(AssertionError):
        build_timeline(result, LOST)
