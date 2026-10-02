import math

from core.models import (
    CYCLE_STEP,
    MIN_GREEN_WARNING,
    MODELS,
    PRACTICAL_CYCLE_LIMIT,
    PhaseResult,
    TimingInput,
    TimingResult,
)


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
