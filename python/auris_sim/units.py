# SPDX-FileCopyrightText: 2026 AURIS simulator contributors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Unit systems.

Exchange files (``case.yaml``, results) are in SI units. A SOFA scene may use
another consistent unit system, for example millimetres for the inner ear. A
:class:`UnitSystem` is defined by the size of its length, mass and time units in
SI; every derived unit follows from them.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UnitSystem:
    """A consistent (length, mass, time) unit system, expressed in SI.

    Example: ``UnitSystem(length=1e-3, mass=1.0, time=1.0)`` is (mm, kg, s), whose
    force unit is 1e-3 N (mN) and pressure unit is 1e3 Pa (kPa).
    """

    length: float = 1.0  # metres per scene length unit
    mass: float = 1.0  # kilograms per scene mass unit
    time: float = 1.0  # seconds per scene time unit

    @property
    def force(self) -> float:
        """Size of the scene force unit, in newtons."""
        return self.mass * self.length / self.time**2

    @property
    def pressure(self) -> float:
        """Size of the scene pressure (and Young's modulus) unit, in pascals."""
        return self.mass / (self.length * self.time**2)

    @property
    def density(self) -> float:
        """Size of the scene mass-density unit, in kg/m^3."""
        return self.mass / self.length**3

    @property
    def velocity(self) -> float:
        """Size of the scene velocity unit, in m/s."""
        return self.length / self.time

    # SI -> scene
    def length_to_scene(self, value):
        return value / self.length

    def time_to_scene(self, value):
        return value / self.time

    def force_to_scene(self, value):
        return value / self.force

    def pressure_to_scene(self, value):
        return value / self.pressure

    def density_to_scene(self, value):
        return value / self.density

    def velocity_to_scene(self, value):
        return value / self.velocity

    # scene -> SI
    def length_to_si(self, value):
        return value * self.length

    def force_to_si(self, value):
        return value * self.force


SI = UnitSystem()
"""SI units (m, kg, s)."""

MM_KG_S = UnitSystem(length=1e-3, mass=1.0, time=1.0)
"""(mm, kg, s): force in mN, pressure in kPa. Default for inner-ear scenes."""
