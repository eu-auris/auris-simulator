# SPDX-FileCopyrightText: 2026 AURIS simulator contributors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Synthetic geometries, so that scenes and tests run without restricted data."""

from auris_sim.geometry.spiral import (
    SpiralDuct,
    TriangleMesh,
    entry_pose,
    spiral_duct,
    write_stl,
)

__all__ = ["SpiralDuct", "TriangleMesh", "entry_pose", "spiral_duct", "write_stl"]
