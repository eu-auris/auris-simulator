# SPDX-FileCopyrightText: 2026 AURIS simulator contributors
# SPDX-License-Identifier: LGPL-2.1-or-later
import json

import numpy as np
import pytest

from auris_sim.data import Dataset, fetch, load_registry
from auris_sim.results import write_run


def test_write_run(tmp_path):
    out = write_run(
        tmp_path / "run",
        {"peak_insertion_force_n": 0.1},
        {"time_s": np.arange(3.0), "inserted_length_m": np.array([0.0, 1e-3, 2e-3])},
        case_sha256="0" * 64,
    )
    assert json.loads((out / "metrics.json").read_text()) == {"peak_insertion_force_n": 0.1}
    header = (out / "timeseries.csv").read_text().splitlines()[0]
    assert header == "time_s,inserted_length_m"
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["case_sha256"] == "0" * 64
    assert manifest["auris_sim_version"]


def test_write_run_rejects_ragged_series(tmp_path):
    with pytest.raises(ValueError):
        write_run(tmp_path, {}, {"a": [1, 2], "b": [1]})


def test_repository_registry_is_valid(repo_root):
    assert isinstance(load_registry(repo_root / "data" / "registry.yaml"), dict)


def test_registry_checks(tmp_path):
    reg = tmp_path / "registry.yaml"
    reg.write_text("datasets:\n  - {id: a, title: A, licence: CC-BY-4.0, access: open}\n")
    with pytest.raises(ValueError, match="url"):
        load_registry(reg)


def test_fetch_refuses_controlled_data():
    ds = Dataset(
        id="x", title="X", licence="DUA", access="controlled", access_procedure="ask the producer"
    )
    with pytest.raises(PermissionError, match="ask the producer"):
        fetch(ds)
