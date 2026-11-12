# SPDX-FileCopyrightText: 2026 AURIS simulator contributors
# SPDX-License-Identifier: LGPL-2.1-or-later
import numpy as np
import pytest

from auris_sim.metrics import angular_insertion_depth, insertion_work, mean_force, peak_force


def test_force_metrics():
    f = np.array([0.0, 0.01, -0.03, 0.02])
    assert peak_force(f) == pytest.approx(0.03)
    assert mean_force(f) == pytest.approx(0.015)


def test_insertion_work_constant_force():
    depth = np.linspace(0.0, 0.02, 11)
    assert insertion_work(np.full(11, 0.05), depth) == pytest.approx(0.05 * 0.02)


def test_insertion_work_shape_mismatch():
    with pytest.raises(ValueError):
        insertion_work([1.0, 2.0], [0.0])


def test_angular_depth_one_and_a_half_turns():
    t = np.linspace(0.0, 3 * np.pi, 400)
    pts = np.column_stack([np.cos(t), np.sin(t), 0.1 * t])
    assert angular_insertion_depth(pts) == pytest.approx(540.0)


def test_angular_depth_other_axis_and_origin():
    t = np.linspace(0.0, np.pi / 2, 50)
    pts = np.column_stack([np.full_like(t, 5.0), 1 + np.cos(t), 2 + np.sin(t)])
    assert angular_insertion_depth(pts, axis=(1, 0, 0), origin=(0, 1, 2)) == pytest.approx(90.0)


def test_invalid_inputs():
    with pytest.raises(ValueError):
        peak_force([])
    with pytest.raises(ValueError):
        angular_insertion_depth([[0, 0, 0]])
