<!--
SPDX-FileCopyrightText: 2026 AURIS simulator contributors
SPDX-License-Identifier: CC-BY-4.0
-->

# Getting started

## 1. Install SOFA

The electrode array is simulated with the [Cosserat](https://github.com/SofaDefrost/Cosserat)
plugin, using `Frames2StrainCosseratMapping`. This mapping is on Cosserat's `main` branch but not
in its v26.06 release, so for now you need **SOFA master** (nightly binaries, or a build from
source with SofaPython3) and **Cosserat built from `main`** (the CI uses the commit pinned in
`.github/workflows/ci.yml`). From SOFA v26.12 on, the release binaries should be enough.

Set `SOFA_ROOT` to the SOFA directory, and make SofaPython3 visible to Python:

```bash
export SOFA_ROOT=/path/to/sofa
export PYTHONPATH="$SOFA_ROOT/plugins/SofaPython3/lib/python3/site-packages:$PYTHONPATH"
```

## 2. Install the Python package

Use the **same Python version** as the one SOFA was built with.

```bash
git clone https://github.com/eu-auris/auris-simulator.git
cd auris-simulator
python -m pip install -e ".[dev]"
python -m pytest -m "not sofa"     # checks that do not need SOFA
python -m pytest                   # all checks, with SOFA available
```

## 3. Build the SOFA plugin (optional for now)

The C++ plugin has no components yet; build it when you start adding some.

```bash
cmake -S . -B build -G Ninja -DCMAKE_PREFIX_PATH="$SOFA_ROOT/lib/cmake" -DCMAKE_BUILD_TYPE=Release
cmake --build build
```

## 4. Run the example scene

```bash
runSofa scenes/electrode_insertion.py                       # with the GUI
python scenes/electrode_insertion.py --headless --steps 500 # writes results/
```

The scene inserts a straight electrode array into a synthetic spiral duct. Edit
`scenes/cases/synthetic_spiral.yaml` (or pass `--case`) to change the instrument or the
insertion strategy. Results are written as `metrics.json`, `timeseries.csv` and
`manifest.json`.
