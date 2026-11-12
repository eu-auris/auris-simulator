# SPDX-FileCopyrightText: 2026 AURIS simulator contributors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Registry of external datasets (they never live in this Git repository).

``data/registry.yaml`` lists datasets by DOI, version, licence, access mode and
SHA-256 checksum. Open datasets can be downloaded on demand with :func:`fetch`
(needs the optional ``pooch`` dependency: ``pip install auris-sim[data]``).
Controlled-access datasets are listed with their access procedure only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

ACCESS_MODES = ("open", "restricted", "controlled")


@dataclass(frozen=True)
class Dataset:
    id: str
    title: str
    licence: str
    access: str
    doi: str | None = None
    version: str | None = None
    url: str | None = None
    sha256: str | None = None
    producer: str | None = None
    access_procedure: str | None = None
    tags: tuple[str, ...] = field(default_factory=tuple)


def load_registry(path: str | Path) -> dict[str, Dataset]:
    """Load the dataset registry and check its entries."""
    with Path(path).open(encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    datasets: dict[str, Dataset] = {}
    for entry in raw.get("datasets") or []:
        entry = dict(entry)
        entry["tags"] = tuple(entry.get("tags", ()))
        ds = Dataset(**entry)
        if ds.access not in ACCESS_MODES:
            raise ValueError(f"dataset {ds.id}: access must be one of {ACCESS_MODES}")
        if ds.access == "open" and not (ds.url and ds.sha256):
            raise ValueError(f"dataset {ds.id}: open datasets need 'url' and 'sha256'")
        if ds.id in datasets:
            raise ValueError(f"duplicate dataset id: {ds.id}")
        datasets[ds.id] = ds
    return datasets


def fetch(dataset: Dataset, cache_dir: str | Path | None = None) -> Path:
    """Download an open dataset (checked against its SHA-256) and return its path."""
    if dataset.access != "open":
        procedure = dataset.access_procedure or "see the registry"
        raise PermissionError(f"dataset {dataset.id} is {dataset.access}: {procedure}")
    try:
        import pooch
    except ImportError as exc:  # pragma: no cover - depends on the environment
        raise ImportError("fetching datasets needs 'pip install auris-sim[data]'") from exc
    return Path(
        pooch.retrieve(
            url=dataset.url,
            known_hash=f"sha256:{dataset.sha256}",
            path=cache_dir or pooch.os_cache("auris_sim"),
        )
    )
