# SPDX-FileCopyrightText: 2026 AURIS simulator contributors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Electrode-array insertion scene.

The electrode array is a BeamAdapter wire (two straight sections: a proximal one
with the base diameter and a distal one with the tip diameter), pushed at
constant speed by an ``InterventionalRadiologyController`` into a rigid duct.
Contact uses Lagrange multipliers with Coulomb friction.

The scene runs in (mm, kg, s) units (:data:`auris_sim.units.MM_KG_S`); the case
file and the recorded results are in SI.

Not modelled yet (see ``docs/design.md``): insertion force measurement,
deformable structures (basilar membrane), robotic instruments, patient-specific
anatomies from the digital twin.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import numpy as np

from auris_sim.geometry import SpiralDuct, entry_pose, spiral_duct, write_stl
from auris_sim.io import Case
from auris_sim.metrics import angular_insertion_depth
from auris_sim.units import MM_KG_S, UnitSystem

try:
    import Sofa
    import Sofa.Core
except ImportError:  # pragma: no cover - documented requirement
    Sofa = None

REQUIRED_PLUGINS = [
    "BeamAdapter",
    "Sofa.Component.AnimationLoop",
    "Sofa.Component.Collision.Detection.Algorithm",
    "Sofa.Component.Collision.Detection.Intersection",
    "Sofa.Component.Collision.Geometry",
    "Sofa.Component.Collision.Response.Contact",
    "Sofa.Component.Constraint.Lagrangian.Correction",
    "Sofa.Component.Constraint.Lagrangian.Solver",
    "Sofa.Component.Constraint.Projective",
    "Sofa.Component.IO.Mesh",
    "Sofa.Component.IntegrationScheme.Backward",
    "Sofa.Component.LinearSolver.Direct",
    "Sofa.Component.SolidMechanics.Spring",
    "Sofa.Component.StateContainer",
    "Sofa.Component.Topology.Container.Constant",
    "Sofa.Component.Topology.Container.Dynamic",
    "Sofa.Component.Topology.Container.Grid",
    "Sofa.Component.Visual",
]


def _cache_dir() -> Path:
    return Path(os.environ.get("AURIS_SIM_CACHE", Path.home() / ".cache" / "auris_sim"))


def _quaternion_from_x_to(direction: np.ndarray) -> list[float]:
    """Quaternion (x, y, z, w) rotating the +x axis (beam axis) onto ``direction``."""
    d = np.asarray(direction, dtype=float)
    d /= np.linalg.norm(d)
    x = np.array([1.0, 0.0, 0.0])
    c = float(np.dot(x, d))
    if c < -1.0 + 1e-12:
        return [0.0, 0.0, 1.0, 0.0]  # half turn around z
    axis = np.cross(x, d)
    w = 1.0 + c
    q = np.array([axis[0], axis[1], axis[2], w])
    return (q / np.linalg.norm(q)).tolist()


def _synthetic_anatomy(case: Case, units: UnitSystem):
    """Generate the spiral duct STL (in scene units) and return (path, entry pose)."""
    params = SpiralDuct.from_dict(case["anatomy"]["source"].get("parameters"))
    key = hashlib.sha256(json.dumps(params.__dict__, sort_keys=True).encode()).hexdigest()[:16]
    stl = _cache_dir() / "geometry" / f"spiral_duct_{key}_mm.stl"
    if not stl.exists():
        write_stl(stl, spiral_duct(params).scaled(1.0 / units.length))
    position, direction = entry_pose(params)
    return stl, units.length_to_scene(position), direction


class InsertionMonitor(Sofa.Core.Controller if Sofa else object):
    """Records the inserted length and the tip trajectory; stops at the target depth."""

    def __init__(self, deploy_controller, dofs, target_depth, units: UnitSystem, **kwargs):
        if Sofa:
            Sofa.Core.Controller.__init__(self, **kwargs)
        self.deploy = deploy_controller
        self.dofs = dofs
        self.target_depth = target_depth  # scene units
        self.units = units
        self.time: list[float] = []
        self.inserted: list[float] = []
        self.tip: list[np.ndarray] = []
        self.done = False

    def onAnimateEndEvent(self, event):  # noqa: N802 - SOFA callback name
        xtip = float(self.deploy.xtip.value[0])
        self.time.append(float(self.getContext().time.value))
        self.inserted.append(xtip)
        self.tip.append(np.array(self.dofs.position.value[-1][:3], dtype=float))
        if not self.done and xtip >= self.target_depth:
            self.deploy.speed.value = 0.0
            self.done = True

    def timeseries(self) -> dict[str, np.ndarray]:
        """Recorded signals in SI units."""
        tip = self.units.length_to_si(np.array(self.tip).reshape(-1, 3))
        return {
            "time_s": np.array(self.time),
            "inserted_length_m": self.units.length_to_si(np.array(self.inserted)),
            "tip_x_m": tip[:, 0],
            "tip_y_m": tip[:, 1],
            "tip_z_m": tip[:, 2],
        }

    def metrics(self) -> dict[str, float | bool | None]:
        ts = self.timeseries()
        tip = np.column_stack([ts["tip_x_m"], ts["tip_y_m"], ts["tip_z_m"]])
        return {
            "final_inserted_length_m": float(ts["inserted_length_m"][-1]) if len(tip) else None,
            "angular_insertion_depth_deg": angular_insertion_depth(tip) if len(tip) > 1 else None,
            "target_depth_reached": self.done,
            # TODO: insertion force (needs the constraint forces: planned C++ component).
            "peak_insertion_force_n": None,
        }


def create_insertion_scene(root, case: Case, units: UnitSystem = MM_KG_S, gui: bool = True):
    """Fill ``root`` with the insertion scene described by ``case``.

    Returns the :class:`InsertionMonitor`, which holds the recorded data.
    """
    if Sofa is None:
        raise ImportError("create_insertion_scene needs SOFA with SofaPython3")

    source = case["anatomy"]["source"]
    if source["type"] != "synthetic":
        raise NotImplementedError("only synthetic anatomies are supported in this version")
    stl, start, direction = _synthetic_anatomy(case, units)

    instr, strat = case["instrument"], case["strategy"]
    contact, sim = case["contact"], case["simulation"]
    length = units.length_to_scene(instr["length"])
    tip_len = length * instr["tip_fraction"]
    radius_base = units.length_to_scene(instr["diameter"]["base"]) / 2.0
    radius_tip = units.length_to_scene(instr["diameter"]["tip"]) / 2.0
    young = units.pressure_to_scene(instr["young_modulus"])
    density = units.density_to_scene(instr["density"])
    n_beams = int(instr["n_beams"])
    n_tip = max(1, round(n_beams * instr["tip_fraction"]))

    root.dt = units.time_to_scene(sim["dt"])
    root.gravity = units.length_to_scene(np.asarray(sim["gravity"], dtype=float)).tolist()
    root.addObject("RequiredPlugin", pluginName=" ".join(REQUIRED_PLUGINS))
    root.addObject(
        "VisualStyle",
        displayFlags="showVisualModels showCollisionModels hideBehaviorModels hideMappings",
    )
    root.addObject("FreeMotionAnimationLoop")
    root.addObject("DefaultVisualManagerLoop")
    root.addObject(
        "LCPConstraintSolver", mu=contact["friction"], tolerance=1e-8, maxIt=1000, build_lcp=False
    )
    root.addObject("CollisionPipeline", depth=6, verbose=False, draw=False)
    root.addObject("BruteForceBroadPhase")
    root.addObject("BVHNarrowPhase")
    root.addObject(
        "LocalMinDistance",
        alarmDistance=units.length_to_scene(contact["alarm_distance"]),
        contactDistance=units.length_to_scene(contact["contact_distance"]),
        angleCone=0.2,
    )
    root.addObject("CollisionResponse", response="FrictionContactConstraint")

    # Rest shape of the electrode array: proximal (base diameter) + distal (tip diameter).
    topo = root.addChild("ElectrodeRestShape")
    common = dict(youngModulus=young, massDensity=density, poissonRatio=instr["poisson_ratio"])
    topo.addObject(
        "RodStraightSection",
        name="Proximal",
        length=length - tip_len,
        radius=radius_base,
        nbBeams=n_beams - n_tip,
        nbEdgesCollis=4 * (n_beams - n_tip),
        nbEdgesVisu=8 * (n_beams - n_tip),
        **common,
    )
    topo.addObject(
        "RodStraightSection",
        name="Distal",
        length=tip_len,
        radius=radius_tip,
        nbBeams=n_tip,
        nbEdgesCollis=4 * n_tip,
        nbEdgesVisu=8 * n_tip,
        **common,
    )
    topo.addObject(
        "WireRestShape", name="RestShape", template="Rigid3d", wireMaterials="@Proximal @Distal"
    )
    topo.addObject("EdgeSetTopologyContainer", name="meshLines")
    topo.addObject("EdgeSetTopologyModifier", name="Modifier")
    topo.addObject("EdgeSetGeometryAlgorithms", name="GeomAlgo", template="Rigid3d")
    topo.addObject("MechanicalObject", name="dofTopo", template="Rigid3d")

    starting_pos = list(map(float, start)) + _quaternion_from_x_to(direction)
    beam = root.addChild("Electrode")
    # Named EulerImplicitSolver before SOFA v26.06.
    beam.addObject("EulerImplicitIntegrationScheme", rayleighStiffness=0.2, rayleighMass=0.1)
    beam.addObject("BTDLinearSolver", verification=False, subpartSolve=False, verbose=False)
    beam.addObject(
        "RegularGridTopology",
        name="MeshLines",
        nx=n_beams + 1,
        ny=1,
        nz=1,
        xmin=0.0,
        xmax=0.0,
        ymin=0.0,
        ymax=0.0,
        zmin=0.0,
        zmax=0.0,
        p0=[0.0, 0.0, 0.0],
    )
    dofs = beam.addObject("MechanicalObject", name="DOFs", template="Rigid3d")
    beam.addObject(
        "WireBeamInterpolation",
        name="Interpolation",
        WireRestShape="@../ElectrodeRestShape/RestShape",
    )
    beam.addObject(
        "AdaptiveBeamForceFieldAndMass",
        name="ForceField",
        massDensity=density,
        interpolation="@Interpolation",
    )
    deploy = beam.addObject(
        "InterventionalRadiologyController",
        name="DeployController",
        template="Rigid3d",
        instruments="Interpolation",
        topology="@MeshLines",
        startingPos=starting_pos,
        xtip=[0.0],
        rotationInstrument=[0.0],
        step=units.length_to_scene(1e-4),
        speed=units.velocity_to_scene(strat["insertion_speed"]),
        listening=True,
        controlledInstrument=0,
    )
    beam.addObject("LinearSolverConstraintCorrection", wire_optimization=True)
    beam.addObject("FixedProjectiveConstraint", indices=0, name="FixedBase")
    beam.addObject(
        "RestShapeSpringsForceField",
        points="@DeployController.indexFirstNode",
        stiffness=1e8,
        angularStiffness=1e8,
    )
    collis = beam.addChild("Collision")
    collis.addObject("EdgeSetTopologyContainer", name="collisEdgeSet")
    collis.addObject("EdgeSetTopologyModifier", name="collisEdgeModifier")
    collis.addObject("MechanicalObject", name="CollisionDOFs")
    collis.addObject(
        "MultiAdaptiveBeamMapping",
        controller="../DeployController",
        useCurvAbs=True,
        name="collisMap",
    )
    collis.addObject("LineCollisionModel", contactDistance=0.0)
    collis.addObject("PointCollisionModel", contactDistance=0.0)

    duct = root.addChild("Duct")
    duct.addObject("MeshSTLLoader", name="loader", filename=str(stl), triangulate=True)
    duct.addObject("MeshTopology", position="@loader.position", triangles="@loader.triangles")
    duct.addObject("MechanicalObject", name="DOFs")
    duct.addObject("TriangleCollisionModel", moving=False, simulated=False)
    duct.addObject("LineCollisionModel", moving=False, simulated=False)

    monitor = InsertionMonitor(
        deploy,
        dofs,
        units.length_to_scene(strat["insertion_depth"]),
        units,
        name="InsertionMonitor",
    )
    root.addObject(monitor)
    return monitor
