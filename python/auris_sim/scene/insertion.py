# SPDX-FileCopyrightText: 2026 AURIS simulator contributors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Electrode-array insertion scene, with the Cosserat plugin.

The electrode array is a *frame-primary* Cosserat rod: the degrees of freedom are
the poses (``Rigid3d``) of the section boundaries, and the section strains
(``Vec6d``) are derived from them by ``Frames2StrainCosseratMapping``, with a
``BeamHookeLawForceField`` per section (non-uniform sections allowed). The base is
pushed along +x; the part of the rod still behind the entrance stays on a
straight guide. The anatomy is a rigid, non-simulated obstacle; contacts are
Lagrangian with Coulomb friction.

The insertion force is the sum, along the insertion axis, of the contact forces
the wall exerts (``lambda`` of the obstacle's MechanicalObject).

Frames:

- *insertion frame* (scene): the rod is built along +x from the origin, the
  entrance of the duct is centred on the +x axis and faces -x;
- *anatomy frame*: the frame of the case file (for the synthetic duct, the spiral
  winds around +z; for meshes read from files, the file frame after the optional
  transform). Recorded trajectories are given back in the anatomy frame.

The placement of the anatomy (entrance detection, insertion angle, closing of the
other open loops) is done by :func:`auris_sim.anatomy.build_anatomy`.

Units: the scene runs in (mm, kg, s), i.e. forces in mN and moduli in kPa
(:data:`auris_sim.units.MM_KG_S`); case files and results are in SI.

Needs SOFA (master / v26.12 or later), SofaPython3 and Cosserat (with
``Frames2StrainCosseratMapping``).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from auris_sim.anatomy import Anatomy, build_anatomy
from auris_sim.io import Case
from auris_sim.metrics import angular_insertion_depth, insertion_work, mean_force, peak_force
from auris_sim.units import MM_KG_S, UnitSystem

try:
    import Sofa
    import Sofa.Core
except ImportError:  # pragma: no cover - documented requirement
    Sofa = None

REQUIRED_PLUGINS = [
    "Cosserat",
    "Sofa.Component.AnimationLoop",
    "Sofa.Component.Collision.Detection.Algorithm",
    "Sofa.Component.Collision.Detection.Intersection",
    "Sofa.Component.Collision.Geometry",
    "Sofa.Component.Collision.Response.Contact",
    "Sofa.Component.Constraint.Lagrangian.Correction",
    "Sofa.Component.Constraint.Lagrangian.Solver",
    "Sofa.Component.Constraint.Projective",
    "Sofa.Component.IntegrationScheme.Backward",
    "Sofa.Component.LinearSolver.Direct",
    "Sofa.Component.Mapping.Linear",
    "Sofa.Component.Mass",
    "Sofa.Component.StateContainer",
    "Sofa.Component.Topology.Container.Constant",
    "Sofa.Component.Topology.Container.Dynamic",
    "Sofa.Component.Visual",
]
GUI_PLUGINS = ["Sofa.GL.Component.Rendering3D"]


# --------------------------------------------------------------------------------------
# Pure helpers (no SOFA): section profile, abscissa, guided insertion kinematics
# --------------------------------------------------------------------------------------
@dataclass
class RodProfile:
    """Sections of the rod, in scene units."""

    lengths: list[float]
    young: list[float]
    poisson: list[float]
    radius: float
    density: float

    @property
    def abscissa(self) -> list[float]:
        s = [0.0]
        for length in self.lengths:
            s.append(s[-1] + length)
        return s

    @property
    def length(self) -> float:
        return self.abscissa[-1]

    @property
    def mass(self) -> float:
        return self.density * math.pi * self.radius**2 * self.length


def rod_profile(instrument: dict, units: UnitSystem = MM_KG_S) -> RodProfile:
    """Build the section profile from the ``instrument`` block of a case.

    Either explicit ``sections`` (one entry per section), or ``n_sections``
    uniform sections with the instrument's modulus and Poisson ratio.
    """
    if instrument.get("sections"):
        secs = instrument["sections"]
        lengths = [units.length_to_scene(s["length"]) for s in secs]
        young = [units.pressure_to_scene(s["young_modulus"]) for s in secs]
        poisson = [s.get("poisson_ratio", instrument["poisson_ratio"]) for s in secs]
    else:
        n = int(instrument["n_sections"])
        lengths = [units.length_to_scene(instrument["length"]) / n] * n
        young = [units.pressure_to_scene(instrument["young_modulus"])] * n
        poisson = [instrument["poisson_ratio"]] * n
    return RodProfile(
        lengths=lengths,
        young=young,
        poisson=poisson,
        radius=units.length_to_scene(instrument["radius"]),
        density=units.density_to_scene(instrument["density"]),
    )


def guided_frames(abscissa, travel: float, guide_length: float) -> list[int]:
    """Indices of the frames held on the straight guide for a base travel ``travel``.

    The base (frame 0) is always held; any frame still behind ``guide_length``
    (the entrance) is held too.
    """
    return [i for i, a in enumerate(abscissa) if i == 0 or travel + a < guide_length]


# --------------------------------------------------------------------------------------
# SOFA controllers
# --------------------------------------------------------------------------------------
_Controller = Sofa.Core.Controller if Sofa else object


class GuidedInsertion(_Controller):
    """Pushes the base along +x at ``speed`` up to ``travel``.

    Frames still behind the entrance (``guide_length``) are held on the straight guide.
    """

    def __init__(self, *, frames_mo, clamp, abscissa, speed, travel, guide_length, **kwargs):
        if Sofa:
            Sofa.Core.Controller.__init__(self, **kwargs)
        self.frames_mo, self.clamp = frames_mo, clamp
        self.abscissa = list(abscissa)
        self.speed, self.travel, self.guide_length = speed, travel, guide_length
        self.s = 0.0
        self._n_locked = -1

    @property
    def done(self) -> bool:
        return self.s >= self.travel

    def onAnimateBeginEvent(self, event):  # noqa: N802 - SOFA callback name
        dt = self.getContext().dt.value
        self.s = min(self.travel, self.s + self.speed * dt)
        locked = guided_frames(self.abscissa, self.s, self.guide_length)
        moving = [self.speed, 0.0, 0.0, 0.0, 0.0, 0.0] if not self.done else [0.0] * 6
        with self.frames_mo.position.writeable() as pos, self.frames_mo.velocity.writeable() as vel:
            for i in locked:
                pos[i] = [self.s + self.abscissa[i], 0.0, 0.0, 0.0, 0.0, 0.0, 1.0]
                vel[i] = moving
        if len(locked) != self._n_locked:
            self._n_locked = len(locked)
            self.clamp.indices.value = locked


class InsertionMonitor(_Controller):
    """Records insertion depth, tip trajectory and insertion force; computes the metrics."""

    def __init__(
        self, *, insertion, frames_mo, obstacle_mo, entry_offset, to_anatomy, units,
        axis_origin=(0.0, 0.0, 0.0), axis_direction=(0.0, 0.0, 1.0), **kw,
    ):  # fmt: skip
        if Sofa:
            Sofa.Core.Controller.__init__(self, **kw)
        self.ins, self.frames_mo, self.obstacle_mo = insertion, frames_mo, obstacle_mo
        self.entry_offset = entry_offset  # scene units: tip start -> entrance distance
        # callable: (n, 3) scene points -> anatomy frame (scene units)
        self.to_anatomy = to_anatomy
        self.units = units
        # spiral axis for the angular insertion depth, anatomy frame, SI
        self.axis_origin = np.asarray(axis_origin, dtype=float)
        self.axis_direction = np.asarray(axis_direction, dtype=float)
        self.time: list[float] = []
        self.depth: list[float] = []
        self.force: list[float] = []
        self.tip: list[np.ndarray] = []

    def onAnimateEndEvent(self, event):  # noqa: N802 - SOFA callback name
        lam = np.asarray(self.obstacle_mo.findData("lambda").value, dtype=float).reshape(-1, 3)
        self.time.append(float(self.getContext().time.value))
        self.depth.append(self.ins.s - self.entry_offset)
        self.force.append(float(lam[:, 0].sum()) if len(lam) else 0.0)
        self.tip.append(np.array(self.frames_mo.position.value[-1][:3], dtype=float))

    def timeseries(self) -> dict[str, np.ndarray]:
        """Recorded signals in SI units, tip in the anatomy frame."""
        u = self.units
        tip = u.length_to_si(self.to_anatomy(np.array(self.tip).reshape(-1, 3)))
        return {
            "time_s": np.array(self.time),
            "insertion_depth_m": u.length_to_si(np.array(self.depth)),
            "insertion_force_n": u.force_to_si(np.array(self.force)),
            "tip_x_m": tip[:, 0],
            "tip_y_m": tip[:, 1],
            "tip_z_m": tip[:, 2],
        }

    def metrics(self) -> dict[str, float | bool | None]:
        ts = self.timeseries()
        if len(ts["time_s"]) == 0:
            return {}
        tip = np.column_stack([ts["tip_x_m"], ts["tip_y_m"], ts["tip_z_m"]])
        inside = ts["insertion_depth_m"] > 0.0
        angle = None
        if len(tip) > 1:
            angle = angular_insertion_depth(tip, self.axis_direction, self.axis_origin)
        force, depth = ts["insertion_force_n"][inside], ts["insertion_depth_m"][inside]
        return {
            "final_insertion_depth_m": float(ts["insertion_depth_m"][-1]),
            "angular_insertion_depth_deg": angle,
            "peak_insertion_force_n": peak_force(force) if len(force) else None,
            "mean_insertion_force_n": mean_force(force) if len(force) else None,
            "insertion_work_j": insertion_work(np.abs(force), depth) if len(force) > 1 else None,
            "target_depth_reached": bool(self.ins.done),
        }


# --------------------------------------------------------------------------------------
# Scene
# --------------------------------------------------------------------------------------
def _add_rod(parent, profile: RodProfile, rayleigh_stiffness: float):
    """Frame-primary Cosserat rod built along +x from the origin, base clamped."""
    s = profile.abscissa
    poses = [[si, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0] for si in s]
    frames = parent.addChild("ElectrodeFrames")
    frames_mo = frames.addObject(
        "MechanicalObject", template="Rigid3d", name="FramesMO", position=poses,
        showObject=False, showObjectScale=2 * profile.radius,
    )  # fmt: skip
    clamp = frames.addObject("FixedProjectiveConstraint", name="clamp", indices=[0])
    frames.addObject("UniformMass", totalMass=profile.mass)

    bending = frames.addChild("Bending")
    strain_mo = bending.addObject(
        "MechanicalObject", template="Vec6d", name="cosserat_state",
        position=[[0.0, 0.0, 0.0, 1.0, 0.0, 0.0] for _ in profile.lengths],
    )  # fmt: skip
    bending.addObject(
        "BeamHookeLawForceField", crossSectionShape="circular", length=profile.lengths,
        radius=profile.radius, variantSections=True, youngModulusList=profile.young,
        poissonRatioList=profile.poisson, rayleighStiffness=rayleigh_stiffness,
    )  # fmt: skip
    bending.addObject(
        "Frames2StrainCosseratMapping", name="cosseratMapping", curv_abs_input=s,
        curv_abs_output=s, input=frames_mo.getLinkPath(), output=strain_mo.getLinkPath(),
        radius=profile.radius,
    )  # fmt: skip

    points = [p[:3] for p in poses]
    collision = frames.addChild("Collision")
    collision.addObject(
        "EdgeSetTopologyContainer", position=points,
        edges=[[i, i + 1] for i in range(len(points) - 1)],
    )  # fmt: skip
    collision.addObject("MechanicalObject", name="points", template="Vec3d", position=points)
    collision.addObject("LineCollisionModel", proximity=profile.radius)
    collision.addObject("IdentityMapping")
    return frames, frames_mo, clamp, strain_mo


def _add_obstacle(parent, collision, display, gui: bool):
    """Rigid, non-simulated anatomy; ``collision`` / ``display`` are (vertices, triangles)."""
    vertices, triangles = collision
    node = parent.addChild("Anatomy")
    node.addObject("MeshTopology", name="topology", position=vertices, triangles=triangles)
    mo = node.addObject("MechanicalObject", name="dofs", template="Vec3d", position=vertices)
    node.addObject("TriangleCollisionModel", moving=False, simulated=False)
    if gui:
        vis_vertices, vis_triangles = display or collision
        visual = node.addChild("Visual")
        visual.addObject(
            "OglModel", name="surface", position=vis_vertices, triangles=vis_triangles,
            color=[0.9, 0.7, 0.6, 0.35],
        )  # fmt: skip
    return mo


def create_insertion_scene(
    root, case: Case, units: UnitSystem = MM_KG_S, gui: bool = True,
    anatomy: Anatomy | None = None,
):  # fmt: skip
    """Fill ``root`` with the insertion scene described by ``case``.

    ``anatomy`` may be passed when it was already built with
    :func:`auris_sim.anatomy.build_anatomy` (it is built from ``case`` otherwise).
    Returns the :class:`InsertionMonitor`, which holds the recorded data.
    """
    if Sofa is None:
        raise ImportError("create_insertion_scene needs SOFA with SofaPython3 and Cosserat")
    anatomy = anatomy or build_anatomy(case)

    instr, strat = case["instrument"], case["strategy"]
    contact, sim = case["contact"], case["simulation"]
    profile = rod_profile(instr, units)
    entry_offset = units.length_to_scene(strat["entry_offset"])
    entrance_x = profile.length + entry_offset

    # Anatomy (insertion frame, SI) shifted so that the entrance is at (entrance_x, 0, 0).
    entrance = np.array([entrance_x, 0.0, 0.0])

    def to_scene(mesh):
        verts = units.length_to_scene(mesh.vertices) + entrance
        return verts.tolist(), mesh.triangles.tolist()

    def to_anatomy(points: np.ndarray) -> np.ndarray:
        si = anatomy.to_anatomy(units.length_to_si(points - entrance))
        return units.length_to_scene(si)

    root.dt = units.time_to_scene(sim["dt"])
    root.gravity = units.length_to_scene(np.asarray(sim["gravity"], dtype=float)).tolist()
    plugins = REQUIRED_PLUGINS + (GUI_PLUGINS if gui else [])
    root.addObject("RequiredPlugin", pluginName=" ".join(plugins))
    root.addObject(
        "VisualStyle", displayFlags="showVisualModels showCollisionModels hideBehaviorModels"
    )
    root.addObject("FreeMotionAnimationLoop")
    root.addObject(
        "UnbuiltGaussSeidelConstraintSolver",
        tolerance=sim["constraint_tolerance"], maxIterations=sim["constraint_max_iterations"],
    )  # fmt: skip
    root.addObject("CollisionPipeline", depth=6)
    root.addObject("BruteForceBroadPhase")
    root.addObject("BVHNarrowPhase")
    root.addObject(
        "NewProximityIntersection",
        alarmDistance=units.length_to_scene(contact["alarm_distance"]),
        contactDistance=units.length_to_scene(contact["contact_distance"]),
    )  # fmt: skip
    root.addObject(
        "RuleBasedContactManager", response="FrictionContactConstraint", rules="default",
        responseParams=f"mu={contact['friction']}",
    )  # fmt: skip

    solver = root.addChild("ElectrodeSolver")
    solver.addObject(
        "EulerImplicitIntegrationScheme", name="odesolver", firstOrder=False,
        rayleighMass=sim["rayleigh_mass"], rayleighStiffness=sim["rayleigh_stiffness"],
    )  # fmt: skip
    solver.addObject("BTDLinearSolver", name="linear_solver", template="BTDMatrix6d")
    frames, frames_mo, clamp, _ = _add_rod(solver, profile, sim["rayleigh_stiffness"])
    frames.addObject(
        "LinearSolverConstraintCorrection", linearSolver="@../linear_solver",
        ODESolver="@../odesolver", wire_optimization=False,
    )  # fmt: skip

    display = to_scene(anatomy.display) if anatomy.display is not None else None
    obstacle_mo = _add_obstacle(root, to_scene(anatomy.collision), display, gui)

    insertion = GuidedInsertion(
        frames_mo=frames_mo, clamp=clamp, abscissa=profile.abscissa,
        speed=units.velocity_to_scene(strat["insertion_speed"]),
        travel=units.length_to_scene(strat["insertion_depth"]) + entry_offset,
        guide_length=entrance_x, name="GuidedInsertion",
    )  # fmt: skip
    monitor = InsertionMonitor(
        insertion=insertion, frames_mo=frames_mo, obstacle_mo=obstacle_mo,
        entry_offset=entry_offset, to_anatomy=to_anatomy, units=units,
        axis_origin=anatomy.axis_origin, axis_direction=anatomy.axis_direction,
        name="InsertionMonitor",
    )  # fmt: skip
    monitor.anatomy = anatomy
    root.addObject(insertion)
    root.addObject(monitor)
    return monitor
