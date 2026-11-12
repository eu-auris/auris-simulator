# SPDX-FileCopyrightText: 2026 AURIS simulator contributors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""AURIS hybrid ear-surgery simulator (DC15).

Sub-packages:

- :mod:`auris_sim.geometry`: synthetic geometries (no patient data).
- :mod:`auris_sim.io`: loading and validating case files (``case.yaml``).
- :mod:`auris_sim.metrics`: benchmark metrics (pure NumPy, no SOFA needed).
- :mod:`auris_sim.results`: writing run outputs (metrics, time series, manifest).
- :mod:`auris_sim.data`: registry of external datasets.
- :mod:`auris_sim.scene`: SofaPython3 scene builders (needs SOFA).
"""

__version__ = "0.1.0"
