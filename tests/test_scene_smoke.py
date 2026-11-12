# SPDX-FileCopyrightText: 2026 AURIS simulator contributors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Scene smoke test: build the example scene and run a few steps headless.

Skipped when SOFA (with SofaPython3) or BeamAdapter is not available.
"""

import numpy as np
import pytest

from auris_sim.io import load_case

pytestmark = pytest.mark.sofa

Sofa = pytest.importorskip("Sofa")
pytest.importorskip("Sofa.Simulation")


def test_insertion_scene_runs(example_case_path, tmp_path, monkeypatch):
    monkeypatch.setenv("AURIS_SIM_CACHE", str(tmp_path))
    from auris_sim.scene import create_insertion_scene

    case = load_case(example_case_path)
    root = Sofa.Core.Node("root")
    monitor = create_insertion_scene(root, case)
    Sofa.Simulation.init(root)
    for _ in range(50):
        Sofa.Simulation.animate(root, root.dt.value)

    ts = monitor.timeseries()
    assert len(ts["time_s"]) == 50
    for values in ts.values():
        assert np.all(np.isfinite(values))
    # 50 steps of 0.01 s at 1 mm/s: about 0.5 mm inserted.
    assert ts["inserted_length_m"][-1] == pytest.approx(0.5e-3, rel=0.1)
    assert monitor.metrics()["angular_insertion_depth_deg"] is not None
