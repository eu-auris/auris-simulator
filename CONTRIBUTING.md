<!--
SPDX-FileCopyrightText: 2026 AURIS simulator contributors
SPDX-License-Identifier: CC-BY-4.0
-->

# Contributing to the AURIS simulator

Thank you for contributing. This repository is shared by the AURIS doctoral candidates
(in particular DC15 and DC14), their supervisors and external users.

## Ground rules

- **No data in Git.** Never commit patient-derived data (images, segmentations, meshes from
  patient scans), even pseudonymised, nor large files (> ~5 MB). Add a reference to
  [`data/registry.yaml`](data/registry.yaml) instead. Synthetic geometry must be generated
  by code.
- **Licence headers.** Every new file starts with an SPDX header:
  <!-- REUSE-IgnoreStart -->
  ```
  SPDX-FileCopyrightText: 2026 AURIS simulator contributors
  SPDX-License-Identifier: LGPL-2.1-or-later   (code)  or  CC-BY-4.0  (docs, tutorials, cases)
  ```
  <!-- REUSE-IgnoreEnd -->
  Files that cannot hold a comment (JSON, binary) are covered by [`REUSE.toml`](REUSE.toml).
  `reuse lint` checks this in CI.
- **Units.** Exchange files and results are in SI units. Scenes may use another consistent
  unit system through `auris_sim.units` (see the design note, section 4.2).
- **No invented parameters.** Placeholder values must be marked as such in comments; real
  values come with a reference (publication, dataset DOI, measurement protocol).

## Sign-off

<!-- TODO: confirm with Inria's IP office whether a DCO is enough or a CLA is needed. -->
Proposed: each commit carries a `Signed-off-by:` line ([Developer Certificate of
Origin](https://developercertificate.org)), added with `git commit -s`. This will be confirmed
before the first public release.

## Workflow

1. Open an issue describing the change (bug, feature, new benchmark, interface change).
2. Create a branch, make the change with tests, open a pull request against `main`.
3. CI must pass: Python tests and lint, licence check, plugin build against SOFA v26.06.
4. Changes to the exchange formats (`python/auris_sim/schemas/`) need a review from both the
   DC14 and the DC15 sides, and a bump of `schema_version` when they are not backward compatible.

## Development setup

```bash
python -m pip install -e ".[dev,docs]"
ruff check .
python -m pytest -m "not sofa"        # without SOFA
python -m pytest                      # with SOFA + SofaPython3 + BeamAdapter available
reuse lint
mkdocs serve                          # documentation preview
```

Commit messages follow [Conventional Commits](https://www.conventionalcommits.org)
(`feat:`, `fix:`, `docs:`, `ci:`, `chore:`, …).

## Releases

Maintainers tag `vMAJOR.MINOR.PATCH` and publish a GitHub release; the release notes state the
compatible SOFA version. Zenodo archives each release and issues a DOI. See the design note,
section 2.7, for the Software Heritage and HAL steps.
