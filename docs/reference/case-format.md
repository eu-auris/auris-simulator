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
- File paths are relative to the case file, or absolute; `~` and environment variables such as
  `${AURIS_DATA}` are expanded. Each external file may carry a `doi`, a `sha256` checksum (checked
  when the file is read), the length `unit` of the file (`m`, `mm` or `um`; default `m`) and a
  4×4 `transform` to the anatomy frame.
- Unknown keys are rejected, so typos are caught early.

## Sections

| Section | Content |
|---|---|
| `schema_version` | `"0.1"` |
| `units` | Must be SI |
| `anatomy` | `id`, `frame`, optional `modiolar_axis`, and a `source`: either `synthetic` (generator `spiral_duct` and its parameters) or `files` (meshes, see below) |
| `instrument` | `electrode_array` modelled as a `cosserat` rod: length, radius, Young's modulus, Poisson ratio, density, and either `n_sections` uniform sections or an explicit `sections` list (length, modulus, Poisson ratio per section) |
| `strategy` | Insertion speed, target depth of the tip beyond the entrance, initial tip-to-entrance distance, insertion angle |
| `contact` | Friction coefficient, alarm and contact distances |
| `simulation` | Time step, duration, gravity, Rayleigh damping, constraint-solver tolerance and iterations |
| `outputs` | Requested outputs |

## Example

```yaml
--8<-- "scenes/cases/synthetic_spiral.yaml"
```

The full example is `scenes/cases/synthetic_spiral.yaml` in the repository.

## Anatomy from mesh files

A segmented cochlea is given as a surface of the lumen (STL or OBJ), open at the entrance:

```yaml
anatomy:
  id: my-cochlea
  frame: specimen_ct                     # name of the anatomy frame (free text)
  source:
    type: files
    meshes:
      collision:                         # required: surface used for contacts (coarse)
        file: ${AURIS_DATA}/cochlea/collision.stl
        unit: mm
        sha256: <64 hex characters>      # optional, checked when the file is read
      display:                           # optional: finer surface, display only
        file: ${AURIS_DATA}/cochlea/display.stl
        unit: mm
    # entrance: {centre: [x, y, z], normal: [x, y, z]}   # optional override, anatomy frame (m)
  # modiolar_axis: {origin: [x, y, z], direction: [x, y, z]}  # optional, anatomy frame (m)

strategy:
  insertion_speed: 2.5e-4
  insertion_depth: 0.020
  insertion_angle_deg: -10               # optional, default 0
```

What the simulator does with it (`auris_sim.anatomy.build_anatomy`):

1. **Reading.** Each file is checked against its `sha256` (when given), scaled from `unit` to
   metres, then moved by its `transform` (when given) into the anatomy frame.
2. **Entrance.** The entrance is the most planar open loop of the collision mesh (loops of fewer
   than 6 vertices are ignored), or the loop closest to `entrance.centre` when it is given.
3. **Placement.** The anatomy is moved so that the entrance centre is on the insertion axis: the
   instrument enters along the normal of the entrance plane; the spiral axis is the thinnest
   principal direction of the surface; the bulk of the cochlea is on the +y side, so that the
   spiral turns counter-clockwise around +z. The display mesh gets the same placement.
4. **Closing.** The other open loops (apex, segmentation cuts) are closed, and the triangles are
   turned towards the lumen.
5. **Insertion angle.** `insertion_angle_deg` turns the anatomy about the spiral axis through the
   entrance (counter-clockwise seen from +z); the instrument keeps its axis.

Recorded tip trajectories are given back in the anatomy frame. The angular insertion depth is
measured around `modiolar_axis`. Without it, the axis is *estimated* (spiral axis through the
surface centroid; a few degrees off on the synthetic duct), and the run manifest says so
(`modiolar_axis_estimated`). The manifest also records the SHA-256 of every mesh read.

!!! warning "Restricted data"
    Case files that point to specimen-derived meshes or calibrated device profiles stay
    **outside the repository** (see `data/registry.yaml`). Keep them in a private folder and
    refer to the data with absolute paths or an environment variable such as `${AURIS_DATA}`.
    Run them with `python scenes/electrode_insertion.py --headless --case /path/to/case.yaml`, or
    `AURIS_CASE=/path/to/case.yaml runSofa scenes/electrode_insertion.py`.

## Loading a case in Python

```python
from auris_sim.io import load_case

case = load_case("scenes/cases/synthetic_spiral.yaml")
print(case["instrument"]["length"], case.sha256())
```
