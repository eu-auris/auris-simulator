# SPDX-FileCopyrightText: 2026 AURIS simulator contributors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Scene helpers that do not need SOFA."""

import numpy as np
import pytest

from auris_sim.geometry import SpiralDuct, insertion_frame
from auris_sim.geometry.spiral import centerline
from auris_sim.io import load_case
from auris_sim.scene import guided_frames, rod_profile
from auris_sim.units import MM_KG_S


def test_uniform_profile_in_scene_units(example_case_path):
    instr = load_case(example_case_path)["instrument"]
    prof = rod_profile(instr, MM_KG_S)
    assert len(prof.lengths) == instr["n_sections"]
    assert prof.length == pytest.approx(25.0)  # mm
    assert prof.radius == pytest.approx(0.3)  # mm
    assert prof.young[0] == pytest.approx(1.0e5)  # kPa
    assert prof.abscissa[0] == 0.0 and len(prof.abscissa) == len(prof.lengths) + 1


def test_explicit_profile():
    instr = {
        "length": 0.02, "radius": 2e-4, "young_modulus": 1e8, "poisson_ratio": 0.45,
        "density": 1100, "n_sections": 10,
        "sections": [
            {"length": 0.015, "young_modulus": 2e8},
            {"length": 0.005, "young_modulus": 1e7},
        ],
    }  # fmt: skip
    prof = rod_profile(instr, MM_KG_S)
    assert prof.lengths == pytest.approx([15.0, 5.0])
    assert prof.young == pytest.approx([2e5, 1e4])
    assert prof.poisson == [0.45, 0.45]


def test_guided_frames():
    s = [0.0, 1.0, 2.0, 3.0]
    assert guided_frames(s, travel=0.0, guide_length=2.5) == [0, 1, 2]
    assert guided_frames(s, travel=1.0, guide_length=2.5) == [0, 1]
    assert guided_frames(s, travel=5.0, guide_length=2.5) == [0]


def test_insertion_frame_aligns_entrance_with_x():
    params = SpiralDuct()
    rotation, centre = insertion_frame(params)
    assert rotation @ rotation.T == pytest.approx(np.eye(3))
    assert np.linalg.det(rotation) == pytest.approx(1.0)
    points, _ = centerline(params)
    moved = (points - centre) @ rotation.T
    assert moved[0] == pytest.approx(np.zeros(3))
    direction = moved[1] - moved[0]
    assert direction / np.linalg.norm(direction) == pytest.approx([1.0, 0.0, 0.0], abs=1e-3)
