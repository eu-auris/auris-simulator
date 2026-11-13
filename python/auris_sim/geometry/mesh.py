# SPDX-FileCopyrightText: 2026 AURIS simulator contributors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Triangle meshes read from files: reading, checksums, boundary loops, placement.

A segmented cochlea is usually a surface of the lumen that is **open** where it
was cut: at the entrance (round window or cochleostomy) and sometimes at the
apex or elsewhere. The functions here find the entrance among these open loops,
compute the rigid placement that brings it onto the insertion axis, close the
other loops and orient the triangles towards the lumen.

Insertion frame (the result of :func:`place_by_entrance`): the entrance centre
is at the origin, the instrument enters along +x, the spiral axis (thinnest
direction of the mesh) is along z, and the bulk of the cochlea lies on the +y
side, so that the spiral turns counter-clockwise around +z.

Lengths are in the units of the mesh (metres once :func:`read_mesh` has scaled
it).
"""

from __future__ import annotations

import hashlib
import re
import struct
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from auris_sim.geometry.spiral import TriangleMesh

#: Scale factors from the length units accepted for mesh files to metres.
LENGTH_UNITS = {"m": 1.0, "mm": 1.0e-3, "um": 1.0e-6}


class MeshError(ValueError):
    """Raised when a mesh file cannot be read or used."""


# --------------------------------------------------------------------------------------
# Reading
# --------------------------------------------------------------------------------------
def file_sha256(path: str | Path) -> str:
    """SHA-256 of a file, as 64 lowercase hexadecimal characters."""
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def weld(corners: np.ndarray, rel_tol: float = 1e-9) -> TriangleMesh:
    """Build an indexed mesh from triangle corners ``(m, 3, 3)``, merging equal vertices.

    Vertices closer than ``rel_tol`` times the bounding-box diagonal are merged.
    Triangles that become degenerate (two equal corners) are dropped.
    """
    pts = np.asarray(corners, dtype=float).reshape(-1, 3)
    if len(pts) == 0:
        raise MeshError("mesh has no triangles")
    diag = float(np.linalg.norm(pts.max(axis=0) - pts.min(axis=0))) or 1.0
    key = np.round(pts / (rel_tol * diag)).astype(np.int64)
    _, first, inverse = np.unique(key, axis=0, return_index=True, return_inverse=True)
    triangles = inverse.reshape(-1, 3)
    keep = (
        (triangles[:, 0] != triangles[:, 1])
        & (triangles[:, 1] != triangles[:, 2])
        & (triangles[:, 0] != triangles[:, 2])
    )
    return TriangleMesh(pts[first], triangles[keep].astype(np.int64))


def read_stl(path: str | Path) -> TriangleMesh:
    """Read an ASCII or binary STL file (lengths in the file's own unit)."""
    raw = Path(path).read_bytes()
    if len(raw) >= 84:
        n = struct.unpack("<I", raw[80:84])[0]
        if len(raw) == 84 + 50 * n:  # binary: the size gives it away
            rec = np.frombuffer(
                raw, offset=84, count=n,
                dtype=np.dtype([("normal", "<f4", 3), ("v", "<f4", (3, 3)), ("attr", "<u2")]),
            )  # fmt: skip
            return weld(rec["v"].astype(float))
    text = raw.decode("ascii", errors="replace")
    if not text.lstrip().startswith("solid"):
        raise MeshError(f"{path}: not an STL file")
    number = r"([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)"
    coords = re.findall(rf"vertex\s+{number}\s+{number}\s+{number}", text)
    if not coords or len(coords) % 3:
        raise MeshError(f"{path}: malformed ASCII STL")
    return weld(np.array(coords, dtype=float).reshape(-1, 3, 3))


def read_obj(path: str | Path) -> TriangleMesh:
    """Read the vertices and faces of a Wavefront OBJ file (polygons are fanned)."""
    vertices, triangles = [], []
    for line in Path(path).read_text(errors="replace").splitlines():
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "v":
            vertices.append([float(x) for x in parts[1:4]])
        elif parts[0] == "f":
            idx = [int(p.split("/")[0]) for p in parts[1:]]
            idx = [i - 1 if i > 0 else len(vertices) + i for i in idx]
            triangles += [[idx[0], idx[k], idx[k + 1]] for k in range(1, len(idx) - 1)]
    if not triangles:
        raise MeshError(f"{path}: no faces")
    v = np.asarray(vertices, dtype=float)
    return weld(v[np.asarray(triangles)])


_READERS = {".stl": read_stl, ".obj": read_obj}


def read_mesh(path: str | Path, unit: str = "m") -> TriangleMesh:
    """Read a surface mesh (STL or OBJ) and scale it to metres.

    ``unit`` is the length unit of the file: ``"m"``, ``"mm"`` or ``"um"``.
    """
    path = Path(path)
    reader = _READERS.get(path.suffix.lower())
    if reader is None:
        raise MeshError(f"{path}: unsupported format (supported: {', '.join(_READERS)})")
    if unit not in LENGTH_UNITS:
        raise MeshError(f"unknown length unit {unit!r} (expected one of {list(LENGTH_UNITS)})")
    return reader(path).scaled(LENGTH_UNITS[unit])


def apply_transform(mesh: TriangleMesh, matrix) -> TriangleMesh:
    """Apply a 4x4 rigid transform (row-major list of 16 numbers, or a 4x4 array)."""
    m = np.asarray(matrix, dtype=float).reshape(4, 4)
    r, t = m[:3, :3], m[:3, 3]
    if not np.allclose(r @ r.T, np.eye(3), atol=1e-6) or np.linalg.det(r) < 0:
        raise MeshError("transform: the 3x3 block is not a rotation")
    if not np.allclose(m[3], [0.0, 0.0, 0.0, 1.0]):
        raise MeshError("transform: the last row must be [0, 0, 0, 1]")
    return TriangleMesh(mesh.vertices @ r.T + t, mesh.triangles.copy())


# --------------------------------------------------------------------------------------
# Topology
# --------------------------------------------------------------------------------------
def boundary_loops(mesh: TriangleMesh) -> list[np.ndarray]:
    """Open loops of the surface: ordered vertex indices, one array per loop.

    A boundary edge belongs to one triangle only. Each loop follows the boundary
    edges in the direction given by their triangle, so that ``loop[i] -> loop[i+1]``
    is an edge of the mesh with the mesh's orientation.
    """
    t = mesh.triangles
    directed = np.vstack([t[:, [0, 1]], t[:, [1, 2]], t[:, [2, 0]]])
    undirected = np.sort(directed, axis=1)
    _, inverse, counts = np.unique(undirected, axis=0, return_inverse=True, return_counts=True)
    boundary = directed[counts[inverse.ravel()] == 1]
    successors: dict[int, list[int]] = defaultdict(list)
    for a, b in boundary:
        successors[int(a)].append(int(b))
    loops = []
    while successors:
        start = next(iter(successors))
        loop, v = [start], start
        while v in successors:
            nxt = successors[v].pop()
            if not successors[v]:
                del successors[v]
            if nxt == start:
                break
            loop.append(nxt)
            v = nxt
        if len(loop) >= 3:
            loops.append(np.asarray(loop, dtype=np.int64))
    return loops


def cap_loop(mesh: TriangleMesh, loop: np.ndarray) -> TriangleMesh:
    """Close an open loop with a fan around its centroid, keeping the mesh orientation."""
    centre_index = len(mesh.vertices)
    vertices = np.vstack([mesh.vertices, mesh.vertices[loop].mean(axis=0)])
    nxt = np.roll(loop, -1)
    fan = np.column_stack([nxt, loop, np.full(len(loop), centre_index)])
    return TriangleMesh(vertices, np.vstack([mesh.triangles, fan]))


def signed_volume(mesh: TriangleMesh) -> float:
    """Signed enclosed volume: positive when a closed surface has outward normals."""
    v = mesh.vertices[mesh.triangles]
    return float(np.einsum("ij,ij->i", v[:, 0], np.cross(v[:, 1], v[:, 2])).sum() / 6.0)


def triangle_areas(mesh: TriangleMesh) -> np.ndarray:
    v = mesh.vertices[mesh.triangles]
    return 0.5 * np.linalg.norm(np.cross(v[:, 1] - v[:, 0], v[:, 2] - v[:, 0]), axis=1)


def surface_centroid(mesh: TriangleMesh) -> np.ndarray:
    """Area-weighted centroid of the surface."""
    w = triangle_areas(mesh)
    return (mesh.vertices[mesh.triangles].mean(axis=1) * w[:, None]).sum(axis=0) / w.sum()


def _principal_axes(points: np.ndarray, weights: np.ndarray | None = None):
    """Eigenvalues (ascending) and eigenvectors (columns) of the weighted covariance."""
    w = np.ones(len(points)) if weights is None else weights
    c = (points * w[:, None]).sum(axis=0) / w.sum()
    d = points - c
    cov = (d * w[:, None]).T @ d / w.sum()
    return np.linalg.eigh(cov)


def loop_planarity(mesh: TriangleMesh, loop: np.ndarray) -> float:
    """Out-of-plane spread of a loop relative to its size (0 for a planar loop)."""
    values, _ = _principal_axes(mesh.vertices[loop])
    return float(np.sqrt(max(values[0], 0.0) / max(values[2], 1e-300)))


def loop_size(mesh: TriangleMesh, loop: np.ndarray) -> float:
    """Mean distance of the loop vertices to their centroid."""
    pts = mesh.vertices[loop]
    return float(np.linalg.norm(pts - pts.mean(axis=0), axis=1).mean())


# --------------------------------------------------------------------------------------
# Placement
# --------------------------------------------------------------------------------------
@dataclass
class Placement:
    """Rigid placement from the anatomy frame to the insertion frame.

    A point ``p`` of the anatomy frame goes to ``(p - centre) @ rotation.T``.
    """

    rotation: np.ndarray  # (3, 3), rows = insertion axes expressed in the anatomy frame
    centre: np.ndarray  # (3,), entrance centre in the anatomy frame
    entrance_loop: int | None = None  # index in the list of boundary loops
    entrance_radius: float | None = None
    info: dict = field(default_factory=dict)

    def to_insertion(self, points) -> np.ndarray:
        return (np.asarray(points, dtype=float) - self.centre) @ self.rotation.T

    def to_anatomy(self, points) -> np.ndarray:
        return np.asarray(points, dtype=float) @ self.rotation + self.centre

    def rotated(self, angle_deg: float) -> Placement:
        """Same placement followed by a rotation of ``angle_deg`` about +z (the spiral axis)."""
        return Placement(
            rotation_about_z(angle_deg) @ self.rotation, self.centre.copy(),
            self.entrance_loop, self.entrance_radius, dict(self.info),
        )  # fmt: skip


def rotation_about_z(angle_deg: float) -> np.ndarray:
    """Rotation matrix of ``angle_deg`` degrees about +z (counter-clockwise seen from +z)."""
    a = np.radians(angle_deg)
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


def find_entrance(
    mesh: TriangleMesh, loops: list[np.ndarray], centre=None, min_vertices: int = 6
) -> int:
    """Index of the entrance among the open ``loops``.

    With ``centre`` (a point of the anatomy frame), the loop whose centroid is
    closest. Otherwise the most planar loop among those with at least
    ``min_vertices`` vertices (small holes left by the segmentation are ignored).
    """
    if not loops:
        raise MeshError("the mesh has no open loop: no entrance to insert through")
    if centre is not None:
        d = [np.linalg.norm(mesh.vertices[lp].mean(axis=0) - np.asarray(centre)) for lp in loops]
        return int(np.argmin(d))
    candidates = [i for i, lp in enumerate(loops) if len(lp) >= min_vertices]
    if not candidates:
        raise MeshError(f"no open loop with at least {min_vertices} vertices: no entrance found")
    return min(candidates, key=lambda i: loop_planarity(mesh, loops[i]))


def place_by_entrance(
    mesh: TriangleMesh, loops: list[np.ndarray] | None = None, entrance: dict | None = None
) -> Placement:
    """Rigid placement that puts the entrance at the origin, facing the instrument.

    - x: normal of the entrance plane, pointing into the cochlea;
    - z: thinnest principal direction of the surface (spiral axis), made normal to x;
    - y = z x x, with the sign of z chosen so that the surface centroid has y > 0.

    ``entrance`` may give ``centre`` (and optionally ``normal``, pointing into the
    cochlea) in the anatomy frame, for meshes whose entrance is ambiguous.
    """
    loops = boundary_loops(mesh) if loops is None else loops
    entrance = entrance or {}
    index = find_entrance(mesh, loops, entrance.get("centre")) if loops else None
    if index is None and "centre" not in entrance:
        raise MeshError("the mesh has no open loop: give anatomy/source/entrance")

    centroid = surface_centroid(mesh)
    if index is not None:
        pts = mesh.vertices[loops[index]]
        centre = pts.mean(axis=0)
        _, vectors = _principal_axes(pts)
        ex = vectors[:, 0]
        radius = loop_size(mesh, loops[index])
    else:
        centre, ex, radius = np.asarray(entrance["centre"], dtype=float), None, None
    if "centre" in entrance:
        centre = np.asarray(entrance["centre"], dtype=float)
    if "normal" in entrance:
        ex = np.asarray(entrance["normal"], dtype=float)
    elif ex is None:
        raise MeshError("anatomy/source/entrance: 'normal' is needed when the mesh is closed")
    ex = ex / np.linalg.norm(ex)
    if "normal" not in entrance and np.dot(centroid - centre, ex) < 0.0:
        ex = -ex

    _, axes = _principal_axes(mesh.vertices[mesh.triangles].mean(axis=1), triangle_areas(mesh))
    ez = axes[:, 0] - np.dot(axes[:, 0], ex) * ex
    if np.linalg.norm(ez) < 1e-6:  # degenerate: entrance normal along the thin direction
        ez = axes[:, 1] - np.dot(axes[:, 1], ex) * ex
    ez /= np.linalg.norm(ez)
    ey = np.cross(ez, ex)
    if np.dot(centroid - centre, ey) < 0.0:
        ez, ey = -ez, -ey
    info = {
        "n_open_loops": len(loops),
        "entrance_vertices": int(len(loops[index])) if index is not None else 0,
        "entrance_planarity": loop_planarity(mesh, loops[index]) if index is not None else None,
    }
    return Placement(np.vstack([ex, ey, ez]), centre, index, radius, info)


def close_except(
    mesh: TriangleMesh, loops: list[np.ndarray], keep: int | None
) -> tuple[TriangleMesh, int]:
    """Cap every open loop except ``loops[keep]``; return the mesh and the number capped."""
    out, n = mesh, 0
    for i, loop in enumerate(loops):
        if i != keep:
            out, n = cap_loop(out, loop), n + 1
    return out, n


def orient_towards_lumen(mesh: TriangleMesh, loops: list[np.ndarray]) -> TriangleMesh:
    """Make triangle normals point into the lumen (inside the closed surface).

    The orientation is decided on the surface with all its loops capped: inward
    normals give a negative signed volume. Assumes consistently oriented triangles.
    """
    closed, _ = close_except(mesh, loops, None)
    if signed_volume(closed) > 0.0:
        return TriangleMesh(mesh.vertices.copy(), mesh.triangles[:, ::-1].copy())
    return mesh


def mesh_report(mesh: TriangleMesh) -> dict:
    """Basic checks of a surface mesh (sizes in the mesh units)."""
    t = mesh.triangles
    undirected = np.sort(np.vstack([t[:, [0, 1]], t[:, [1, 2]], t[:, [2, 0]]]), axis=1)
    _, counts = np.unique(undirected, axis=0, return_counts=True)
    loops = boundary_loops(mesh)
    ends = mesh.vertices[undirected]
    edges = np.linalg.norm(ends[:, 0] - ends[:, 1], axis=1)
    return {
        "vertices": int(len(mesh.vertices)),
        "triangles": int(len(t)),
        "boundary_edges": int((counts == 1).sum()),
        "non_manifold_edges": int((counts > 2).sum()),
        "open_loops": [int(len(lp)) for lp in loops],
        "edge_mean": float(edges.mean()),
        "area": float(triangle_areas(mesh).sum()),
    }
