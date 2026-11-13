<!--
SPDX-FileCopyrightText: 2026 AURIS simulator contributors
SPDX-License-Identifier: CC-BY-4.0
-->

# Case file format (draft 0.1)

A **case file** describes one simulation: anatomy, instrument, insertion strategy, contact and
solver settings. It is the exchange format between the digital twin (DC14) and the simulator
(DC15). It is written in YAML (by hand) or JSON (by programs), and validated against the JSON
Schema `python/auris_sim/schemas/case.schema.json`.

!!! note "Draft"
    Version 0.1 is a starting point, to be agreed with DC14. Changes go through pull requests
    reviewed by both sides; incompatible changes bump `schema_version`.

## Rules

- All quantities are in **SI units** (m, kg, s, N, Pa); the `units` block makes it explicit.
  Scenes convert to their own unit system (`auris_sim.units`).
- Scientific notation such as `1e-3` or `1.0e7` is read as a number.
- File paths are relative to the case file. Each external file may carry a `doi`, a `sha256`
  checksum and a 4×4 `transform` to the anatomy frame.
- Unknown keys are rejected, so typos are caught early.

## Sections

| Section | Content |
|---|---|
| `schema_version` | `"0.1"` |
| `units` | Must be SI |
| `anatomy` | `id`, `frame`, and a `source`: either `synthetic` (generator `spiral_duct` and its parameters) or `files` (named meshes) |
| `instrument` | `electrode_array` modelled as a `cosserat` rod: length, radius, Young's modulus, Poisson ratio, density, and either `n_sections` uniform sections or an explicit `sections` list (length, modulus, Poisson ratio per section) |
| `strategy` | Insertion speed, target depth of the tip beyond the entrance, initial tip-to-entrance distance |
| `contact` | Friction coefficient, alarm and contact distances |
| `simulation` | Time step, duration, gravity, Rayleigh damping, constraint-solver tolerance and iterations |
| `outputs` | Requested outputs |

## Example

```yaml
--8<-- "scenes/cases/synthetic_spiral.yaml"
```

The full example is `scenes/cases/synthetic_spiral.yaml` in the repository.

## Loading a case in Python

```python
from auris_sim.io import load_case

case = load_case("scenes/cases/synthetic_spiral.yaml")
print(case["instrument"]["length"], case.sha256())
```
