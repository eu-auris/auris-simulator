# SPDX-FileCopyrightText: 2026 AURIS simulator contributors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Geometries: the synthetic spiral duct, and meshes read from files."""

from auris_sim.geometry.mesh import (
    MeshError,
    Placement,
    boundary_loops,
    file_sha256,
    mesh_report,
    place_by_entrance,
    read_mesh,
)
from auris_sim.geometry.spiral import (
    SpiralDuct,
    TriangleMesh,
    entry_pose,
    insertion_frame,
    spiral_duct,
    write_stl,
)

__all__ = [
    "MeshError",
    "Placement",
    "SpiralDuct",
    "TriangleMesh",
    "boundary_loops",
    "entry_pose",
    "file_sha256",
    "insertion_frame",
    "mesh_report",
    "place_by_entrance",
    "read_mesh",
    "spiral_duct",
    "write_stl",
]
