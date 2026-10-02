import random

import pytest

from core.calculator import (
    apportion_greens,
    compute_timing,
    flow_ratio,
    round_cycle,
    total_lost_time,
    webster_cycle,
)
from core.models import MODELS, TimingInput

SATURATION = 1900
LOST = 4


def make_input(model_key: str, **volumes: float) -> TimingInput:
    # Any phase the test doesn't mention gets zero demand.
    full = {p.code: volumes.get(p.code, 0) for p in MODELS[model_key].phases}
    return TimingInput(model_key, SATURATION, LOST, full)


def test_flow_ratio():
    assert flow_ratio(850, 1900) == pytest.approx(0.447368, abs=1e-6)


def test_total_lost_time():
    assert total_lost_time(3, 4) == 12


def test_webster_cycle():
    assert webster_cycle(8, 0.763158) == pytest.approx(71.78, abs=0.01)


@pytest.mark.parametrize(
    "raw, expected",
    [(71.78, 75), (75.0, 75), (75.0000000001, 75), (75.01, 80)],
)
def test_round_cycle(raw, expected):
    assert round_cycle(raw) == expected


def test_apportion_greens_always_sums_to_total():
    rng = random.Random(42)
    for _ in range(200):
        ratios = [rng.uniform(0.01, 0.5) for _ in range(rng.randint(1, 8))]
        total = rng.randint(10, 200)
        assert sum(apportion_greens(ratios, total)) == total


def test_apportion_greens_tie_goes_to_lower_index():
    assert apportion_greens([1, 1, 1], 10) == [4, 3, 3]


ACCEPTANCE_CASES = [
    # model, volumes, Y, L, raw Co, cycle, Te, greens
    ("2", {"NS": 850, "EW": 600}, 0.7632, 8, 71.78, 75, 67, [39, 28]),
    ("3", {"MajThru": 800, "MajLeft": 300, "MinStem": 450}, 0.8158, 12, 124.86, 125, 113, [58, 22, 33]),
    ("4", {"NSL": 200, "NST": 700, "EWL": 150, "EWT": 600}, 0.8684, 16, 220.40, 225, 209, [25, 89, 19, 76]),
    ("6", {"NBL": 250, "ArtThru": 900, "MinEB": 500}, 0.8684, 12, 174.80, 175, 163, [25, 89, 49]),
    ("8", {"NBL": 150, "SBT": 600, "EBL": 150, "WBT": 500}, 0.7368, 16, 110.20, 115, 99, [11, 42, 11, 35]),
]


@pytest.mark.parametrize("model_key, volumes, y, lost, raw, cycle, te, greens", ACCEPTANCE_CASES)
def test_acceptance_cases(model_key, volumes, y, lost, raw, cycle, te, greens):
    result = compute_timing(make_input(model_key, **volumes))

    assert not result.oversaturated
    assert result.total_flow_ratio == pytest.approx(y, abs=1e-4)
    assert result.total_lost_time == lost
    assert result.raw_cycle == pytest.approx(raw, abs=0.01)
    assert result.cycle == cycle
    assert result.effective_green == te
    assert [p.green for p in result.phases] == greens
    assert sum(p.green for p in result.phases) == te


def test_oversaturated_case():
    result = compute_timing(make_input("2", NS=1200, EW=800))

    assert result.oversaturated is True
    assert result.total_flow_ratio == pytest.approx(1.0526, abs=1e-4)
    assert result.cycle is None
    assert result.raw_cycle is None
    assert result.effective_green is None
    assert "Oversaturated" in result.message


def test_y_exactly_one_is_oversaturated():
    result = compute_timing(make_input("2", NS=950, EW=950))

    assert result.total_flow_ratio == pytest.approx(1.0)
    assert result.oversaturated is True


def test_inactive_phases_are_dropped():
    result = compute_timing(make_input("6", NBL=250, ArtThru=900, MinEB=500))

    assert result.active_count == 3
    assert len(result.phases) == 3
    assert result.total_lost_time == 12
    assert [p.code for p in result.phases] == ["NBL", "ArtThru", "MinEB"]


def test_single_active_phase():
    result = compute_timing(make_input("2", NS=600))

    assert result.active_count == 1
    assert result.phases[0].green == result.effective_green
    assert result.phases[0].green_share == pytest.approx(1.0)


def test_long_cycle_warning():
    # Y = 0.99 pushes the cycle well past 150 s.
    result = compute_timing(make_input("2", NS=1000, EW=881))

    assert result.cycle > 150
    assert any("impractically long" in w for w in result.warnings)


def test_short_green_warning():
    result = compute_timing(make_input("2", NS=1000, EW=10))

    assert any("Phase EW" in w and "minimum" in w for w in result.warnings)


def test_no_warnings_for_a_healthy_case():
    result = compute_timing(make_input("2", NS=850, EW=600))

    assert result.warnings == []
