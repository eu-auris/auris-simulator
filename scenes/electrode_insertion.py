# SPDX-FileCopyrightText: 2026 AURIS simulator contributors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Example scene: electrode-array insertion into a synthetic spiral duct.

With the GUI (needs ``pip install -e .`` in the Python used by SOFA)::

    runSofa scenes/electrode_insertion.py

Headless, writing results to ``results/``::

    python scenes/electrode_insertion.py --headless
    python scenes/electrode_insertion.py --headless --case my_case.yaml --steps 500

The case file sets the anatomy, the instrument and the insertion strategy; see
``scenes/cases/synthetic_spiral.yaml``.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from auris_sim.io import load_case
from auris_sim.results import write_run
from auris_sim.scene import create_insertion_scene

DEFAULT_CASE = Path(__file__).resolve().parent / "cases" / "synthetic_spiral.yaml"


def createScene(root):  # noqa: N802 - name required by runSofa
    case = load_case(os.environ.get("AURIS_CASE", DEFAULT_CASE))
    create_insertion_scene(root, case)
    return root


def run_headless(case_path: Path, steps: int | None, outdir: Path) -> Path:
    import Sofa
    import Sofa.Simulation

    case = load_case(case_path)
    root = Sofa.Core.Node("root")
    monitor = create_insertion_scene(root, case)
    Sofa.Simulation.init(root)
    n = steps or int(round(case["simulation"]["duration"] / case["simulation"]["dt"]))
    for _ in range(n):
        Sofa.Simulation.animate(root, root.dt.value)
    run_dir = write_run(
        outdir / case["anatomy"]["id"],
        monitor.metrics(),
        monitor.timeseries(),
        case_sha256=case.sha256(),
        case_file=str(case.path),
        steps=n,
    )
    print(f"results written to {run_dir}")
    return run_dir


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--case", type=Path, default=DEFAULT_CASE)
    parser.add_argument("--headless", action="store_true", help="run without GUI")
    parser.add_argument("--steps", type=int, default=None, help="default: duration / dt")
    parser.add_argument("--out", type=Path, default=Path("results"))
    args = parser.parse_args()

    if args.headless:
        run_headless(args.case, args.steps, args.out)
        return

    import Sofa
    import Sofa.Gui
    import Sofa.Simulation

    os.environ["AURIS_CASE"] = str(args.case)
    root = Sofa.Core.Node("root")
    createScene(root)
    Sofa.Simulation.init(root)
    Sofa.Gui.GUIManager.Init("auris", "qglviewer")
    Sofa.Gui.GUIManager.createGUI(root, __file__)
    Sofa.Gui.GUIManager.SetDimension(1080, 800)
    Sofa.Gui.GUIManager.MainLoop(root)
    Sofa.Gui.GUIManager.closeGUI()


if __name__ == "__main__":
    main()
