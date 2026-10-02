from core.models import TimingResult

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
