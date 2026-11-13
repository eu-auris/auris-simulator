<!--
SPDX-FileCopyrightText: 2026 AURIS simulator contributors
SPDX-License-Identifier: CC-BY-4.0
-->

# AURIS simulator

Open hybrid ear-surgery simulator (DC15) of the **AURIS** MSCA Doctoral Network
(*Advanced Ultra-precise Robotic Inner-ear Surgery*), hosted by Inria (DEFROST team,
Université de Lille).

The simulator is built on the [SOFA](https://www.sofa-framework.org) framework. Together with
the AURIS digital twin (DC14), it supports testing and comparison of robotic instruments and
cochlear-implantation strategies, for research and training.

> **Status: early development (v0.1.0).** The current version contains the repository
> skeleton, a synthetic example scene and the exchange formats (drafts). See the
> [design note](docs/design.md) for the scope and the roadmap.

<!-- TODO badges: CI, docs, Zenodo DOI, Software Heritage (once the first workflows and release have run). -->

## Contents

| Path | What |
|---|---|
| `src/AurisSimulator/`, `CMakeLists.txt` | SOFA plugin (C++), for components that need to be fast |
| `python/auris_sim/` | Python package: geometry, case files, metrics, results, scene builders |
| `scenes/` | Runnable example scenes and case files |
| `tutorials/` | Training material (in progress) |
| `benchmarks/` | Benchmark definitions (in progress) |
| `data/registry.yaml` | References to external datasets (no data in this repository) |
| `docs/` | Documentation site (MkDocs), including the design note |

## Requirements

- SOFA **master** (until v26.12 is released) with SofaPython3, and the
  [Cosserat](https://github.com/SofaDefrost/Cosserat) plugin from its `main` branch (the implant
  model uses `Frames2StrainCosseratMapping`, which is not in Cosserat v26.06).
- Python ≥ 3.10, the same Python as the one SOFA is built with.
- [SoftRobots](https://github.com/SofaDefrost/SoftRobots) for robotic instruments (later versions).

## Quick start

Python package only (geometry, case files, metrics; no SOFA needed):

```bash
python -m pip install -e ".[dev]"
python -m pytest -m "not sofa"
```

SOFA plugin:

```bash
cmake -S . -B build -G Ninja -DCMAKE_PREFIX_PATH="$SOFA_ROOT/lib/cmake" -DCMAKE_BUILD_TYPE=Release
cmake --build build
```

Example scene (with SOFA, SofaPython3 and Cosserat available):

```bash
runSofa scenes/electrode_insertion.py
python scenes/electrode_insertion.py --headless --steps 500
```

The example uses a **synthetic** spiral duct and placeholder parameters: it is a teaching and
testing scene, not an anatomical or validated model.

## Data

Datasets (OCT/US, anatomical models, digital-twin parameters, navigation protocols) are **not**
stored in this repository. They are referenced in [`data/registry.yaml`](data/registry.yaml)
by DOI, licence and checksum. Where they will be published is still to be decided by the
consortium (see [design note, section 3](docs/design.md#3-data-sharing-options-and-questions-for-the-consortium)).

## Citing

See [`CITATION.cff`](CITATION.cff) (GitHub shows a "Cite this repository" button). A DOI will be
issued through Zenodo with the first release.

## Licence

- Code: [LGPL-2.1-or-later](LICENSE), like SOFA.
- Documentation, tutorials, example case files: [CC-BY-4.0](LICENSES/CC-BY-4.0.txt).
- Every file carries an SPDX header ([REUSE](https://reuse.software) convention).

## Funding

<!-- TODO: exact acknowledgement wording and grant agreement number. -->
AURIS is a Marie Skłodowska-Curie Doctoral Network funded by the European Union
(Horizon Europe). Grant agreement number: TODO.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) and [MAINTAINERS.md](MAINTAINERS.md).
