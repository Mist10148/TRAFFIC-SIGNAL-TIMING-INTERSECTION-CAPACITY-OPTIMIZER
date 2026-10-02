import pytest

from core.validation import parse_number, validate_inputs


def good_form(**overrides: str) -> dict[str, str]:
    form = {"saturation_flow": "1900", "lost_time": "4", "NS": "850", "EW": "600"}
    form.update(overrides)
    return form


def errors_by_field(form: dict[str, str]) -> dict[str, str]:
    _, errors = validate_inputs("2", form)
    return {e.field: e.message for e in errors}


def test_valid_input_returns_timing_input():
    data, errors = validate_inputs("2", good_form())

    assert errors == []
    assert data.model_key == "2"
    assert data.saturation_flow == 1900
    assert data.lost_time == 4
    assert data.volumes == {"NS": 850, "EW": 600}


def test_parse_number_basics():
    assert parse_number(" 12 ") == 12
    assert parse_number("1.5") == 1.5
    assert parse_number("1,5") == 1.5


@pytest.mark.parametrize("text", ["", "   ", "abc", "nan", "inf", "-inf", "1,2,3", "1e999"])
def test_parse_number_rejects_junk(text):
    assert parse_number(text) is None


@pytest.mark.parametrize(
    "field, value, message",
    [
        ("saturation_flow", "", "Required"),
        ("saturation_flow", "abc", "Enter a number"),
        ("saturation_flow", "nan", "Enter a number"),
        ("saturation_flow", "0", "Must be greater than 0"),
        ("saturation_flow", "-5", "Must be greater than 0"),
        ("saturation_flow", "2401", "Must be 2400 or less"),
        ("lost_time", "", "Required"),
        ("lost_time", "x", "Enter a number"),
        ("lost_time", "3.5", "Must be a whole number of seconds"),
        ("lost_time", "0", "Must be at least 1 s"),
        ("lost_time", "13", "Must be 12 s or less"),
        ("NS", "", "Required"),
        ("NS", "inf", "Enter a number"),
        ("NS", "-1", "Cannot be negative"),
        ("NS", "5001", "Must be 5000 or less"),
    ],
)
def test_field_messages(field, value, message):
    assert errors_by_field(good_form(**{field: value})) == {field: message}


def test_comma_decimal_is_accepted_for_volume():
    data, errors = validate_inputs("2", good_form(NS="850,5"))

    assert errors == []
    assert data.volumes["NS"] == 850.5


def test_all_zero_volumes_gives_volumes_error():
    assert errors_by_field(good_form(NS="0", EW="0")) == {
        "volumes": "At least one volume must be greater than 0"
    }


def test_zero_volume_error_is_skipped_when_another_field_is_bad():
    assert errors_by_field(good_form(NS="0", EW="abc")) == {"EW": "Enter a number"}


def test_several_bad_fields_are_reported_together():
    found = errors_by_field(good_form(saturation_flow="", lost_time="3.5", EW="-2"))

    assert found == {
        "saturation_flow": "Required",
        "lost_time": "Must be a whole number of seconds",
        "EW": "Cannot be negative",
    }


def test_missing_keys_count_as_empty():
    _, errors = validate_inputs("2", {})

    assert {e.field for e in errors} == {"saturation_flow", "lost_time", "NS", "EW"}
