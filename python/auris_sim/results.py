# SPDX-FileCopyrightText: 2026 AURIS simulator contributors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Writing run outputs: ``metrics.json``, ``timeseries.csv`` and ``manifest.json``.

The manifest records everything needed to reproduce or compare a run: simulator
version, git commit (when available), SOFA version (when available), case hash.
"""

from __future__ import annotations

import datetime as _dt
import json
import platform
import subprocess
from pathlib import Path
from typing import Any

import numpy as np

import auris_sim


def _git_commit() -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(__file__).resolve().parent,
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
        return out.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def _sofa_version() -> str | None:
    """SOFA version if SofaPython3 is importable (best effort), else ``None``."""
    try:
        import Sofa
    except ImportError:
        return None
    return str(getattr(Sofa, "__version__", "unknown"))  # pragma: no cover


def manifest(case_sha256: str | None = None, **extra: Any) -> dict[str, Any]:
    return {
        "auris_sim_version": auris_sim.__version__,
        "git_commit": _git_commit(),
        "sofa_version": _sofa_version(),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "case_sha256": case_sha256,
        "created_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        **extra,
    }


def write_run(
    outdir: str | Path,
    metrics: dict[str, Any],
    timeseries: dict[str, Any] | None = None,
    case_sha256: str | None = None,
    **extra: Any,
) -> Path:
    """Write one run into ``outdir`` and return the directory.

    ``timeseries`` maps column names (with units, e.g. ``"time_s"``) to 1-D arrays
    of equal length.
    """
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n")
    if timeseries:
        names = list(timeseries)
        cols = [np.asarray(timeseries[n], dtype=float) for n in names]
        if len({len(c) for c in cols}) != 1:
            raise ValueError("all time series must have the same length")
        np.savetxt(
            outdir / "timeseries.csv",
            np.column_stack(cols),
            delimiter=",",
            header=",".join(names),
            comments="",
        )
    (outdir / "manifest.json").write_text(
        json.dumps(manifest(case_sha256, **extra), indent=2, sort_keys=True) + "\n"
    )
    return outdir
