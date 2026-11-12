# SPDX-FileCopyrightText: 2026 AURIS simulator contributors
# SPDX-License-Identifier: LGPL-2.1-or-later
import pytest

from auris_sim.units import MM_KG_S, SI


def test_si_is_identity():
    assert SI.force == SI.pressure == SI.density == 1.0
    assert SI.length_to_scene(2.5) == 2.5


def test_mm_kg_s_derived_units():
    assert MM_KG_S.force == pytest.approx(1e-3)  # mN
    assert MM_KG_S.pressure == pytest.approx(1e3)  # kPa
    assert MM_KG_S.density == pytest.approx(1e9)


def test_round_trip():
    assert MM_KG_S.length_to_scene(0.025) == pytest.approx(25.0)
    assert MM_KG_S.length_to_si(MM_KG_S.length_to_scene(0.025)) == pytest.approx(0.025)
    assert MM_KG_S.force_to_si(MM_KG_S.force_to_scene(0.1)) == pytest.approx(0.1)
    assert MM_KG_S.pressure_to_scene(1e7) == pytest.approx(1e4)
