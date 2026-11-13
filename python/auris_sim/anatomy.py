# SPDX-FileCopyrightText: 2026 AURIS simulator contributors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Anatomy of a case, placed for insertion (pure NumPy, no SOFA).

:func:`build_anatomy` turns the ``anatomy`` block of a case into meshes in the
*insertion frame* (SI units): the entrance centre is at the origin, the
instrument enters along +x, and the spiral axis is along +z. The insertion angle
of the strategy (``insertion_angle_deg``) rotates the anatomy about +z through
the entrance: the instrument keeps its axis and the cochlea turns.

Two sources:

- ``synthetic``: the parametric spiral duct of :mod:`auris_sim.geometry.spiral`;
- ``files``: a ``collision`` mesh (and optionally a finer ``display`` mesh) read
  from STL/OBJ files, checked against their SHA-256, scaled to metres and moved
  by their optional 4x4 transform into the anatomy frame. The entrance is the
  planar open loop of the collision mesh (or the one given in ``entrance``); the
  other open loops are closed and the triangles are turned towards the lumen.
  Both meshes get the placement computed on the collision mesh.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from auris_sim.geometry import SpiralDuct, TriangleMesh, insertion_frame, spiral_duct
from auris_sim.geometry.mesh import (
    MeshError,
    Placement,
    apply_transform,
    boundary_loops,
    close_except,
    file_sha256,
    orient_towards_lumen,
    place_by_entrance,
    read_mesh,
    surface_centroid,
)
from auris_sim.io import Case


class AnatomyError(ValueError):
    """Raised when the anatomy of a case cannot be built."""


@dataclass
class Anatomy:
    """Anatomy placed in the insertion frame (SI units)."""

    collision: TriangleMesh  # insertion frame, triangles facing the lumen
    display: TriangleMesh | None  # insertion frame, or None to show the collision mesh
    placement: Placement  # anatomy frame -> insertion frame (angle included)
    axis_origin: np.ndarray  # spiral (modiolar) axis, anatomy frame
    axis_direction: np.ndarray
    axis_estimated: bool  # True when the axis was estimated from the mesh
    inputs: dict = field(default_factory=dict)  # provenance of the files read

    def to_anatomy(self, points) -> np.ndarray:
        """Insertion frame -> anatomy frame (SI)."""
        return self.placement.to_anatomy(points)


def resolve_path(case: Case, file: str) -> Path:
    """Path of an external file: ``~`` and ``$VARIABLES`` expanded, relative to the case."""
    expanded = os.path.expandvars(os.path.expanduser(file))
    if "$" in expanded:
        raise AnatomyError(f"{file}: undefined environment variable")
    return case.resolve(expanded)


def load_mesh_ref(case: Case, ref: dict, name: str) -> tuple[TriangleMesh, dict]:
    """Read one ``fileRef`` of the case: checksum, unit, transform. Returns (mesh, provenance)."""
    path = resolve_path(case, ref["file"])
    if not path.is_file():
        raise AnatomyError(f"anatomy/source/meshes/{name}: file not found: {path}")
    digest = file_sha256(path)
    if "sha256" in ref and ref["sha256"] != digest:
        raise AnatomyError(
            f"anatomy/source/meshes/{name}: SHA-256 mismatch for {path}\n"
            f"  expected {ref['sha256']}\n  found    {digest}"
        )
    try:
        mesh = read_mesh(path, ref.get("unit", "m"))
        if "transform" in ref:
            mesh = apply_transform(mesh, ref["transform"])
    except MeshError as exc:
        raise AnatomyError(f"anatomy/source/meshes/{name}: {exc}") from exc
    provenance = {"file": ref["file"], "sha256": digest}
    if "doi" in ref:
        provenance["doi"] = ref["doi"]
    return mesh, provenance


def _moved(mesh: TriangleMesh, placement: Placement) -> TriangleMesh:
    return TriangleMesh(placement.to_insertion(mesh.vertices), mesh.triangles.copy())


def _synthetic(case: Case, angle: float) -> Anatomy:
    params = SpiralDuct.from_dict(case["anatomy"]["source"].get("parameters"))
    rotation, centre = insertion_frame(params)
    placement = Placement(rotation, centre).rotated(angle)
    return Anatomy(
        collision=_moved(spiral_duct(params), placement),
        display=None,
        placement=placement,
        axis_origin=np.zeros(3),
        axis_direction=np.array([0.0, 0.0, 1.0]),
        axis_estimated=False,
    )


def _from_files(case: Case, angle: float) -> Anatomy:
    source = case["anatomy"]["source"]
    meshes = source["meshes"]
    collision, prov = load_mesh_ref(case, meshes["collision"], "collision")
    inputs = {"collision": prov}
    display = None
    if "display" in meshes:
        display, inputs["display"] = load_mesh_ref(case, meshes["display"], "display")

    loops = boundary_loops(collision)
    try:
        placement = place_by_entrance(collision, loops, source.get("entrance"))
    except MeshError as exc:
        raise AnatomyError(f"anatomy/source: {exc}") from exc
    closed, n_capped = close_except(collision, loops, placement.entrance_loop)
    closed = orient_towards_lumen(closed, [loops[placement.entrance_loop]] if loops else [])
    placement.info["capped_loops"] = n_capped

    # Spiral axis in the anatomy frame: given in the case, or the z axis of the
    # placement through the surface centroid (a rough estimate of the modiolar axis).
    axis = case["anatomy"].get("modiolar_axis")
    if axis:
        origin = np.asarray(axis["origin"], dtype=float)
        direction = np.asarray(axis["direction"], dtype=float)
        estimated = False
    else:
        origin, direction, estimated = surface_centroid(collision), placement.rotation[2], True

    placement = placement.rotated(angle)
    return Anatomy(
        collision=_moved(closed, placement),
        display=_moved(display, placement) if display is not None else None,
        placement=placement,
        axis_origin=origin,
        axis_direction=direction / np.linalg.norm(direction),
        axis_estimated=estimated,
        inputs=inputs,
    )


def build_anatomy(case: Case) -> Anatomy:
    """Build and place the anatomy of ``case`` (see the module docstring)."""
    source = case["anatomy"]["source"]
    angle = float(case["strategy"].get("insertion_angle_deg", 0.0))
    if source["type"] == "synthetic":
        anatomy = _synthetic(case, angle)
        if "modiolar_axis" in case["anatomy"]:
            axis = case["anatomy"]["modiolar_axis"]
            anatomy.axis_origin = np.asarray(axis["origin"], dtype=float)
            anatomy.axis_direction = np.asarray(axis["direction"], dtype=float)
        return anatomy
    if source["type"] == "files":
        return _from_files(case, angle)
    raise AnatomyError(f"unknown anatomy source {source['type']!r}")
