# SPDX-FileCopyrightText: 2026 AURIS simulator contributors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Insertion metrics (see the benchmark protocol in ``docs/design.md``, section 4.4).

Inputs and outputs are in SI units, except angles (degrees). These functions
work the same on simulated and on measured data, so that both can be compared
with one code path. Metric definitions are drafts, to be agreed with the
clinical partners.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike


def _as_1d(values: ArrayLike, name: str) -> np.ndarray:
    a = np.asarray(values, dtype=float)
    if a.ndim != 1 or a.size == 0:
        raise ValueError(f"{name} must be a non-empty 1-D array")
    return a


def peak_force(force: ArrayLike) -> float:
    """Peak of the absolute insertion force (N)."""
    return float(np.max(np.abs(_as_1d(force, "force"))))


def mean_force(force: ArrayLike) -> float:
    """Mean of the absolute insertion force (N)."""
    return float(np.mean(np.abs(_as_1d(force, "force"))))


def insertion_work(force: ArrayLike, depth: ArrayLike) -> float:
    """Work of the insertion force along the insertion depth (J), trapezoidal rule."""
    f, d = _as_1d(force, "force"), _as_1d(depth, "depth")
    if f.shape != d.shape:
        raise ValueError("force and depth must have the same length")
    return float(np.sum(0.5 * (f[1:] + f[:-1]) * np.diff(d)))


def angular_insertion_depth(
    points: ArrayLike,
    axis: ArrayLike = (0.0, 0.0, 1.0),
    origin: ArrayLike = (0.0, 0.0, 0.0),
) -> float:
    """Angle (degrees) swept by a trajectory around an axis.

    ``points`` is the ``(n, 3)`` trajectory of the instrument tip, in the anatomy
    frame. The angle is unwrapped, so several turns are counted (e.g. 540 deg for
    one turn and a half). In the cochlear frame the axis is the modiolar axis.
    """
    p = np.asarray(points, dtype=float)
    if p.ndim != 2 or p.shape[1] != 3 or len(p) < 2:
        raise ValueError("points must be an (n >= 2, 3) array")
    axis = np.asarray(axis, dtype=float)
    axis = axis / np.linalg.norm(axis)
    rel = p - np.asarray(origin, dtype=float)
    # Orthonormal basis (e1, e2) of the plane normal to the axis.
    helper = np.array([1.0, 0.0, 0.0]) if abs(axis[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    e1 = np.cross(axis, helper)
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(axis, e1)
    angles = np.unwrap(np.arctan2(rel @ e2, rel @ e1))
    return float(np.degrees(abs(angles[-1] - angles[0])))
