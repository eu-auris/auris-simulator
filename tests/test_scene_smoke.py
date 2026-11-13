# SPDX-FileCopyrightText: 2026 AURIS simulator contributors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Scene smoke tests: build the example scene and run it headless.

Skipped when SOFA (with SofaPython3) is not importable. Needs the Cosserat plugin.
"""

import numpy as np
import pytest

from auris_sim.io import load_case

pytestmark = pytest.mark.sofa

Sofa = pytest.importorskip("Sofa")
pytest.importorskip("Sofa.Simulation")


def _run(case, steps):
    from auris_sim.scene import create_insertion_scene

    root = Sofa.Core.Node("root")
    monitor = create_insertion_scene(root, case, gui=False)
    Sofa.Simulation.init(root)
    for _ in range(steps):
        Sofa.Simulation.animate(root, root.dt.value)
    return monitor


def test_insertion_scene_runs(example_case_path):
    case = load_case(example_case_path)
    monitor = _run(case, 50)

    ts = monitor.timeseries()
    assert len(ts["time_s"]) == 50
    for values in ts.values():
        assert np.all(np.isfinite(values))
    # 50 steps of 0.01 s at 1 mm/s: the base moved 0.5 mm;
    # the tip started 0.3 mm before the entrance.
    assert ts["insertion_depth_m"][-1] == pytest.approx(0.2e-3, abs=1e-6)
    assert set(monitor.metrics()) >= {"angular_insertion_depth_deg", "peak_insertion_force_n"}


@pytest.mark.slow
def test_rod_follows_the_spiral(example_case_path):
    """Insert 8 mm quickly: the tip must turn with the duct and the wall must push back."""
    case = load_case(example_case_path)
    case.data["strategy"].update(insertion_speed=4e-3, insertion_depth=8e-3)
    monitor = _run(case, 220)
    metrics = monitor.metrics()
    assert metrics["target_depth_reached"]
    assert metrics["angular_insertion_depth_deg"] > 60.0
    assert metrics["peak_insertion_force_n"] > 0.0
