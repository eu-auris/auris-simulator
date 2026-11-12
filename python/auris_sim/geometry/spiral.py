# SPDX-FileCopyrightText: 2026 AURIS simulator contributors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Parametric spiral duct: a *cochlea-like* synthetic geometry.

This is a teaching and testing geometry, **not an anatomical model**: default
values are illustrative only. Real anatomies come from the digital twin (DC14)
or from published datasets listed in ``data/registry.yaml``.

Frame convention: the spiral winds counter-clockwise around the +z axis (the
"modiolar" axis of the synthetic frame), starting on the +x axis at z = 0 and
rising towards +z. Angular insertion depth is measured around this axis (see
:func:`auris_sim.metrics.angular_insertion_depth`). All lengths are in metres.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class SpiralDuct:
    """Parameters of the synthetic spiral duct (SI units, illustrative values)."""

    turns: float = 2.5
    spiral_radius_base: float = 4.0e-3
    spiral_radius_apex: float = 1.0e-3
    height: float = 3.0e-3
    duct_radius_base: float = 0.9e-3
    duct_radius_apex: float = 0.5e-3
    n_rings: int = 240
    n_sides: int = 16

    @classmethod
    def from_dict(cls, params: dict | None) -> SpiralDuct:
        return cls(**(params or {}))


@dataclass
class TriangleMesh:
    vertices: np.ndarray  # (n, 3) float
    triangles: np.ndarray  # (m, 3) int

    def scaled(self, factor: float) -> TriangleMesh:
        return TriangleMesh(self.vertices * factor, self.triangles.copy())


def centerline(params: SpiralDuct) -> tuple[np.ndarray, np.ndarray]:
    """Return the centreline points ``(n_rings, 3)`` and their angles (rad).

    The spiral radius decreases exponentially from base to apex, and the height
    increases linearly with the angle.
    """
    theta_max = 2.0 * np.pi * params.turns
    theta = np.linspace(0.0, theta_max, params.n_rings)
    ratio = params.spiral_radius_apex / params.spiral_radius_base
    r = params.spiral_radius_base * ratio ** (theta / theta_max)
    z = params.height * theta / theta_max
    points = np.column_stack([r * np.cos(theta), r * np.sin(theta), z])
    return points, theta


def _duct_radius(params: SpiralDuct, s: np.ndarray) -> np.ndarray:
    """Duct radius along the normalised abscissa ``s`` in [0, 1] (linear taper)."""
    return params.duct_radius_base + (params.duct_radius_apex - params.duct_radius_base) * s


def _tangents(points: np.ndarray) -> np.ndarray:
    t = np.gradient(points, axis=0)
    return t / np.linalg.norm(t, axis=1, keepdims=True)


def spiral_duct(params: SpiralDuct | None = None) -> TriangleMesh:
    """Build the duct wall as a triangle mesh, open at the base, closed at the apex.

    Triangle normals point **into the lumen**, i.e. towards the side where the
    inserted instrument lies.
    """
    params = params or SpiralDuct()
    points, _ = centerline(params)
    tangents = _tangents(points)
    s = np.linspace(0.0, 1.0, len(points))
    radii = _duct_radius(params, s)

    # Local frame per ring: n is horizontal and perpendicular to the tangent,
    # b completes the frame. The tangent is never vertical for this geometry.
    z_axis = np.array([0.0, 0.0, 1.0])
    n = np.cross(tangents, z_axis)
    n /= np.linalg.norm(n, axis=1, keepdims=True)
    b = np.cross(tangents, n)

    phi = np.linspace(0.0, 2.0 * np.pi, params.n_sides, endpoint=False)
    cos_phi, sin_phi = np.cos(phi)[None, :, None], np.sin(phi)[None, :, None]
    ring = points[:, None, :] + radii[:, None, None] * (
        cos_phi * n[:, None, :] + sin_phi * b[:, None, :]
    )
    vertices = ring.reshape(-1, 3)

    k = params.n_sides
    tris = []
    for i in range(len(points) - 1):
        for j in range(k):
            a, b_, c, d = i * k + j, i * k + (j + 1) % k, (i + 1) * k + j, (i + 1) * k + (j + 1) % k
            tris.append((a, c, b_))
            tris.append((b_, c, d))
    # Apex cap: fan around the last centreline point.
    apex_index = len(vertices)
    vertices = np.vstack([vertices, points[-1]])
    last = (len(points) - 1) * k
    for j in range(k):
        tris.append((last + j, last + (j + 1) % k, apex_index))
    triangles = np.asarray(tris, dtype=np.int64)

    mesh = TriangleMesh(vertices, triangles)
    _orient_towards_lumen(mesh, points)
    return mesh


def triangle_normals(mesh: TriangleMesh) -> np.ndarray:
    v = mesh.vertices[mesh.triangles]
    nrm = np.cross(v[:, 1] - v[:, 0], v[:, 2] - v[:, 0])
    return nrm / np.linalg.norm(nrm, axis=1, keepdims=True)


def _orient_towards_lumen(mesh: TriangleMesh, points: np.ndarray) -> None:
    """Flip all triangles if the first wall triangle does not face the centreline."""
    nrm = triangle_normals(mesh)[0]
    centroid = mesh.vertices[mesh.triangles[0]].mean(axis=0)
    if np.dot(nrm, points[0] - centroid) < 0.0:
        mesh.triangles[:] = mesh.triangles[:, ::-1]


def entry_pose(params: SpiralDuct | None = None, offset: float = 1.0e-3):
    """Return ``(position, direction)`` for inserting an instrument into the duct.

    The instrument starts ``offset`` metres before the duct opening, on the
    centreline tangent.
    """
    params = params or SpiralDuct()
    points, _ = centerline(params)
    direction = _tangents(points)[0]
    position = points[0] - offset * direction
    return position, direction


def write_stl(path: str | Path, mesh: TriangleMesh, name: str = "auris_sim") -> Path:
    """Write ``mesh`` as a binary STL file (no units: they are given by the caller)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    normals = triangle_normals(mesh).astype(np.float32)
    v = mesh.vertices[mesh.triangles].astype(np.float32)
    record = np.zeros(
        len(mesh.triangles),
        dtype=[("normal", "<f4", 3), ("v", "<f4", (3, 3)), ("attr", "<u2")],
    )
    record["normal"] = normals
    record["v"] = v
    with path.open("wb") as f:
        f.write(name.encode("ascii", "replace")[:80].ljust(80, b" "))
        f.write(struct.pack("<I", len(mesh.triangles)))
        f.write(record.tobytes())
    return path
