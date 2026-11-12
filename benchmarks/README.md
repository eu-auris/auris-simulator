<!--
SPDX-FileCopyrightText: 2026 AURIS simulator contributors
SPDX-License-Identifier: CC-BY-4.0
-->

# Benchmarks

Benchmarks compare robotic instruments and cochlear-implantation strategies in a reproducible
way. The protocol (anatomies × instruments × strategies, metrics, outputs) is described in the
design note, [section 4.4](../docs/design.md#44-benchmark-protocol).

Planned layout:

```
benchmarks/<name>/
├── benchmark.yaml     # anatomies, instruments, strategies, settings, metrics
└── README.md          # purpose, data needed (with registry ids), expected outputs
```

Runs write to `results/<benchmark>/<case>/<run_id>/` with `metrics.json`, `timeseries.csv` and
`manifest.json` (see `auris_sim.results`).

No benchmark is defined yet: metric definitions must first be agreed with DC14 and the clinical
partners (TODO).
