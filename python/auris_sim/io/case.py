# SPDX-FileCopyrightText: 2026 AURIS simulator contributors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Case files (``case.yaml`` / ``case.json``): the DC14 <-> DC15 exchange format.

A case describes one simulation: anatomy, instrument, insertion strategy,
contact and solver settings. It is validated against
``auris_sim/schemas/case.schema.json``; defaults declared in the schema are
filled in after validation.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any

import jsonschema
import yaml

SCHEMA_RESOURCE = "case.schema.json"


class _Yaml12FloatLoader(yaml.SafeLoader):
    """SafeLoader that also reads ``1e-3`` and ``1.0e7`` as floats (YAML 1.2 style).

    PyYAML follows YAML 1.1, where these are strings; scientific notation is
    common in case files, so we accept it.
    """


_Yaml12FloatLoader.add_implicit_resolver(
    "tag:yaml.org,2002:float",
    re.compile(
        r"""^(?:[-+]?(?:[0-9][0-9_]*)\.[0-9_]*(?:[eE][-+]?[0-9]+)?
        |[-+]?(?:[0-9][0-9_]*)(?:[eE][-+]?[0-9]+)
        |\.[0-9_]+(?:[eE][-+]?[0-9]+)?
        |[-+]?\.(?:inf|Inf|INF)
        |\.(?:nan|NaN|NAN))$""",
        re.X,
    ),
    list("-+0123456789."),
)


def load_yaml(text: str):
    """Parse YAML text, reading scientific notation as floats."""
    return yaml.load(text, Loader=_Yaml12FloatLoader)  # noqa: S506 - SafeLoader subclass


class CaseError(ValueError):
    """Raised when a case file is invalid."""


def case_schema() -> dict:
    text = resources.files("auris_sim.schemas").joinpath(SCHEMA_RESOURCE).read_text("utf-8")
    return json.loads(text)


@dataclass
class Case:
    """A validated case. ``data`` holds SI values, with schema defaults filled in."""

    data: dict[str, Any]
    path: Path | None = None

    @property
    def base_dir(self) -> Path:
        return self.path.parent if self.path else Path.cwd()

    def resolve(self, relative: str) -> Path:
        """Resolve a file path given relative to the case file."""
        p = Path(relative)
        return p if p.is_absolute() else self.base_dir / p

    def sha256(self) -> str:
        """Hash of the normalised case content (for run manifests)."""
        blob = json.dumps(self.data, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(blob).hexdigest()

    def __getitem__(self, key: str) -> Any:
        return self.data[key]


def _fill_defaults(instance: Any, schema: dict, root: dict) -> Any:
    """Fill ``default`` values of object properties (recursively, simple cases only)."""
    if "$ref" in schema:
        name = schema["$ref"].rsplit("/", 1)[-1]
        schema = root["$defs"][name]
    if isinstance(instance, dict) and "properties" in schema:
        for key, sub in schema["properties"].items():
            if key not in instance and "default" in sub:
                instance[key] = copy.deepcopy(sub["default"])
            if key in instance:
                instance[key] = _fill_defaults(instance[key], sub, root)
    return instance


def validate_case(data: dict) -> dict:
    """Validate ``data`` and return a copy with defaults filled in.

    Raises :class:`CaseError` with all validation messages.
    """
    schema = case_schema()
    validator = jsonschema.Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))
    if errors:
        lines = [f"- {'/'.join(map(str, e.path)) or '<root>'}: {e.message}" for e in errors]
        raise CaseError("invalid case:\n" + "\n".join(lines))
    data = _fill_defaults(copy.deepcopy(data), schema, schema)
    data.setdefault("contact", _fill_defaults({}, schema["properties"]["contact"], schema))
    _check_consistency(data)
    return data


def _check_consistency(data: dict) -> None:
    """Checks that JSON Schema cannot express."""
    instr, strat = data["instrument"], data["strategy"]
    if strat["insertion_depth"] > instr["length"]:
        raise CaseError(
            "invalid case:\n- strategy/insertion_depth: larger than instrument/length "
            f"({strat['insertion_depth']} > {instr['length']})"
        )
    if instr["diameter"]["tip"] > instr["diameter"]["base"]:
        raise CaseError("invalid case:\n- instrument/diameter: tip is larger than base")


def load_case(path: str | Path) -> Case:
    """Load and validate a YAML or JSON case file."""
    path = Path(path)
    with path.open(encoding="utf-8") as f:
        raw = json.load(f) if path.suffix == ".json" else load_yaml(f.read())
    if not isinstance(raw, dict):
        raise CaseError(f"invalid case: {path} does not contain a mapping")
    return Case(validate_case(raw), path.resolve())
