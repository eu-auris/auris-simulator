# SPDX-FileCopyrightText: 2026 AURIS simulator contributors
# SPDX-License-Identifier: LGPL-2.1-or-later
import copy

import pytest

from auris_sim.io import CaseError, load_case, validate_case
from auris_sim.io.case import load_yaml


def test_example_case_is_valid(example_case_path):
    case = load_case(example_case_path)
    assert case["anatomy"]["source"]["type"] == "synthetic"
    assert case.base_dir == example_case_path.parent
    assert len(case.sha256()) == 64


def test_defaults_are_filled(example_case_path):
    raw = load_yaml(example_case_path.read_text())
    del raw["contact"]
    del raw["instrument"]["n_beams"]
    data = validate_case(raw)
    assert data["contact"]["friction"] == pytest.approx(0.1)
    assert data["instrument"]["n_beams"] == 30


@pytest.mark.parametrize(
    "mutate, message",
    [
        (lambda d: d.pop("instrument"), "instrument"),
        (lambda d: d["units"].update(length="mm"), "units/length"),
        (lambda d: d["strategy"].update(insertion_speed=-1), "strategy/insertion_speed"),
        (lambda d: d.update(typo=1), "typo"),
        (lambda d: d["strategy"].update(insertion_depth=1.0), "insertion_depth"),
        (lambda d: d["instrument"]["diameter"].update(tip=1e-2), "tip is larger"),
    ],
)
def test_invalid_cases(example_case_path, mutate, message):
    raw = copy.deepcopy(load_yaml(example_case_path.read_text()))
    mutate(raw)
    with pytest.raises(CaseError, match=message):
        validate_case(raw)


def test_yaml_scientific_notation_is_float():
    data = load_yaml("a: 1.0e7\nb: 1e-3\nc: 2.5\nd: '1e3'\ne: 12\n")
    assert data == {"a": 1.0e7, "b": 1e-3, "c": 2.5, "d": "1e3", "e": 12}
    assert isinstance(data["e"], int)
