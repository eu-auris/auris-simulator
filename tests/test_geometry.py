# SPDX-FileCopyrightText: 2026 AURIS simulator contributors
# SPDX-License-Identifier: LGPL-2.1-or-later
import numpy as np
import pytest

from auris_sim.geometry import SpiralDuct, entry_pose, spiral_duct, write_stl
from auris_sim.geometry.spiral import centerline, triangle_normals
from auris_sim.metrics import angular_insertion_depth


def test_centerline_turns_and_radius():
    params = SpiralDuct(turns=2.5, n_rings=500)
    points, theta = centerline(params)
    assert theta[-1] == pytest.approx(2 * np.pi * 2.5)
    r = np.hypot(points[:, 0], points[:, 1])
    assert r[0] == pytest.approx(params.spiral_radius_base)
    assert r[-1] == pytest.approx(params.spiral_radius_apex)
    assert np.all(np.diff(r) < 0)
    assert angular_insertion_depth(points) == pytest.approx(900.0, rel=1e-6)


def test_mesh_is_valid_and_faces_lumen():
    params = SpiralDuct(n_rings=60, n_sides=12)
    mesh = spiral_duct(params)
    n_wall = (params.n_rings - 1) * params.n_sides * 2
    assert mesh.triangles.shape == (n_wall + params.n_sides, 3)
    assert mesh.triangles.min() == 0
    assert mesh.triangles.max() == len(mesh.vertices) - 1

    normals = triangle_normals(mesh)
    assert np.all(np.isfinite(normals))
    # Every wall triangle faces its own ring centre (lumen side).
    points, _ = centerline(params)
    ring = mesh.triangles[:n_wall, 0] // params.n_sides
    centroids = mesh.vertices[mesh.triangles[:n_wall]].mean(axis=1)
    to_center = points[ring] - centroids
    assert np.all(np.einsum("ij,ij->i", normals[:n_wall], to_center) > 0)


def test_entry_pose_points_into_duct():
    params = SpiralDuct()
    position, direction = entry_pose(params, offset=1e-3)
    points, _ = centerline(params)
    assert np.linalg.norm(direction) == pytest.approx(1.0)
    assert np.linalg.norm(points[0] - position) == pytest.approx(1e-3)
    assert np.dot(points[1] - points[0], direction) > 0


def test_write_stl(tmp_path):
    mesh = spiral_duct(SpiralDuct(n_rings=10, n_sides=8))
    path = write_stl(tmp_path / "duct.stl", mesh.scaled(1e3))
    assert path.stat().st_size == 84 + 50 * len(mesh.triangles)
