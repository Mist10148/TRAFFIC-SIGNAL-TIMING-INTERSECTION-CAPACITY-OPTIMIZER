import math
from dataclasses import dataclass

from core.models import (
    MAX_LOST_TIME,
    MAX_SATURATION_FLOW,
    MAX_VOLUME,
    MIN_LOST_TIME,
    MODELS,
    TimingInput,
)


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
