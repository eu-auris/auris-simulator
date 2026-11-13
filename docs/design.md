<!--
SPDX-FileCopyrightText: 2026 AURIS simulator contributors
SPDX-License-Identifier: CC-BY-4.0
-->

# AURIS hybrid ear-surgery simulator — design note

| | |
|---|---|
| Status | **Draft v0.1**, approved by the author as a basis for the repository skeleton (2026-11-12); still to be discussed with the consortium |
| Author | Yinoussa Adagolodjo (Inria DEFROST / Université de Lille) |
| Date | 2026-11-12 |
| Scope | Software deliverable of DC15 and its interface with DC14 (digital twin), as committed in the AURIS proposal, section *P2 – Research Resources* |

> Everything marked **TODO** is an unknown project fact. It must be completed by the
> consortium and must not be guessed. Section 8 gathers all of them.

---

## 0. The commitment

From the AURIS proposal, section *P2 – Research Resources*:

> INRIA will host the hybrid ear surgery simulator (DC15) on GitHub, where it will remain
> accessible for future research and training. Together with the digital twin (DC14), it will
> support further testing and comparison of robotic instruments and cochlear implantation
> strategies. INRIA will maintain access to the simulator repository after the project. The
> digital twin, OCT/US datasets, anatomical models and navigation protocols will also be made
> available through [repository to be confirmed], managed by [partner(s) to be confirmed], in
> accordance with IP, ethical and data-sharing requirements.

This means three distinct promises:

1. **Host and keep accessible** an open simulator (software), led by Inria, which must stay accessible *after* the project ends.
2. **Make it usable for research and training:** comparing robotic instruments and cochlear-implantation strategies, together with DC14's digital twin.
3. **Share data** (digital twin, OCT/US datasets, anatomical models, navigation protocols) through a repository and a data manager that are **still to be decided**.

Decisions taken so far (2026-11-12):

| Topic | Decision | Still to confirm |
|---|---|---|
| GitHub hosting | A **new GitHub organisation dedicated to AURIS**: [`eu-auris`](https://github.com/eu-auris), repository `eu-auris/auris-simulator` | Owners (see §2.1) |
| Code licence | **LGPL-2.1-or-later** (same as SOFA) | Inria IP / technology-transfer office; consortium agreement |
| SOFA version | Blocking CI on **SOFA `master` + Cosserat `main` pinned to a commit** (the implant model needs `Frames2StrainCosseratMapping`, not in Cosserat v26.06), plus a weekly non-blocking job on unpinned `master`/`main`. Switch to the **v26.12** releases when they are out (decision of 2026-11-13) | Check that Cosserat v26.12 contains Frames2Strain |
| Implant model | **Cosserat plugin** only (frame-primary rod, `Frames2StrainCosseratMapping` + `BeamHookeLawForceField`); BeamAdapter is not used (decision of 2026-11-13) | — |
| Device and specimen data | Calibrated electrode-array section profiles and specimen-derived cochlea meshes stay **out of the repository** (restricted entries in `data/registry.yaml`) | Agreement of the rights holders before any publication |
| Partners, DC dates, supervisors | Not provided yet | All marked **TODO** |

---

## 1. Scope: software vs data

The commitment mixes two kinds of resource, which have very different constraints. They must
be handled separately.

| | (a) Software | (b) Data |
|---|---|---|
| What | DC15 hybrid ear-surgery simulator: SOFA plugin, SofaPython3 scenes, Python tools, tutorials, benchmark protocol, interface to the DC14 digital twin | OCT/US datasets, CT-derived anatomical models, digital-twin parameters, navigation protocols, experimental measurements used for validation |
| Where | GitHub (new AURIS org), archived in Software Heritage, deposited in HAL, DOI from Zenodo | **[Repository TODO]**: *not* GitHub |
| Size | Small (MB) | Potentially large (GB–TB for OCT/US volumes) |
| Legal | Licence + IP of contributors | GDPR, ethics approvals, consent, data-sharing agreements, IP |
| Who manages | Inria (DEFROST) | **[Partner(s) TODO]** |
| Lifetime after project | Kept by Inria (commitment) | Defined by the Data Management Plan (DMP) |

### 1.1 What the simulator is (software)

Working definition, to be refined with DC15 and their supervisors:

- **A SOFA plugin** (`AurisSimulator`, C++/CMake) for any component that needs to be fast or that SOFA does not provide yet (e.g. specific contact or trauma-metric components).
- **A Python package** (`auris_sim`) that builds SofaPython3 scenes from parameter files, computes metrics, runs benchmarks and talks to the DC14 digital twin.
- **Dependencies on existing SOFA plugins:**
  - [SofaPython3](https://github.com/sofa-framework/SofaPython3): scenes and scripting.
  - [Cosserat](https://github.com/SofaDefrost/Cosserat) (LGPL-3.0): the electrode array (and other slender instruments) as a Cosserat rod. The simulator uses the *frame-primary* formulation: the degrees of freedom are the poses of the section boundaries, the strains are derived by `Frames2StrainCosseratMapping`, with one `BeamHookeLawForceField` per section, so that non-uniform sections (soft parts and electrode rings), clamping on a guide, contacts and cable forces apply directly to the frames.
  - [SoftRobots](https://github.com/SofaDefrost/SoftRobots): actuation of soft or continuum robotic instruments (cables / tendons, pressure, …), e.g. an actuated implant.
  - *Optional:* SoftRobots.Inverse for inverse (control) problems. **Check its licence first:** it is not under the same licence as SOFA, so it must not become a hard dependency until compatibility is confirmed.
- **Example scenes and tutorials** for training.
- **A benchmark protocol** (§4.4) for comparing instruments and insertion strategies.

**TODO — meaning of "hybrid".** The proposal says "hybrid ear-surgery simulator". The
software architecture depends on what "hybrid" means, for example:
(i) physics-based simulation combined with data-driven or learned models;
(ii) virtual simulation coupled with a physical phantom or a real robot (hardware-in-the-loop);
(iii) a mix of rigid anatomy (bone) and deformable structures (membranes, soft tissue, electrode).
The DC15 description in the proposal should answer this; it is not in the text quoted above.

### 1.2 What is *not* in the GitHub repository

- No patient-derived data of any kind (images, segmentations, meshes extracted from patient scans), even pseudonymised.
- No large files (rule of thumb: nothing above ~5 MB; no Git LFS for research data).
- No data whose licence or consent status is unclear.
- No calibrated parameters of a commercial device (e.g. section lengths and moduli of an electrode array identified against force measurements) unless the rights holders agree: they are passed to the simulator through a case file kept outside the repository.

The repository only holds:

- **synthetic** demo geometry, generated by a script (e.g. a parametric spiral "cochlea-like" duct), so that scenes, tests and tutorials run without access to restricted data;
- a **data registry** (`data/registry.yaml`) that lists external datasets by DOI, version, licence and SHA-256 checksum, plus a small download helper (e.g. based on `pooch`) that fetches open datasets on demand and checks their integrity. Datasets under controlled access are listed with their access procedure; they are not downloaded automatically.

---

## 2. Software sustainability

Goal: make "INRIA will maintain access to the simulator repository after the project"
credible and checkable, independently of the people who are on the project at a given time.

### 2.1 GitHub organisation (new AURIS org)

Decision: a new organisation dedicated to AURIS. A dedicated org gives the project a clear
identity, but if nobody owns it after the network ends, it can become orphaned. Mitigations:

- **Owners:** at least two owners who are **permanent Inria staff** (not DCs, not fixed-term contracts), plus the DC15 PhD student as maintainer. **TODO:** names.
- **Name:** organisation [`eu-auris`](https://github.com/eu-auris), repository `auris-simulator` (`git@github.com:eu-auris/auris-simulator.git`); documentation at `https://eu-auris.github.io/auris-simulator/`.
- **Org settings:** 2FA required for all members; branch protection on `main` (pull requests, required CI); the default licence and the `.github` community health files (code of conduct, issue templates) in a `.github` repository of the org.
- **Exit plan** (written in `MAINTAINERS.md`): if the org is no longer maintained, transfer the repository to an Inria-managed org (GitHub keeps redirects after a transfer), or archive it read-only. Whatever happens on GitHub, Software Heritage and HAL (§2.7) keep a permanent copy.
- Possibly also mirror the repository on Inria's GitLab (`gitlab.inria.fr`). **TODO:** decide whether this is useful.

### 2.2 Licence

- **Code:** LGPL-2.1-or-later, same as SOFA and SoftRobots. This lets other people link the plugin from their own code without imposing a licence on it, while modifications to the simulator itself stay open. Cosserat is under LGPL-3.0: this is compatible ("or later" allows LGPL-3.0), and a distribution that bundles both is covered by LGPL-3.0.
- **Documentation, tutorials, synthetic models:** CC-BY-4.0.
<!-- REUSE-IgnoreStart -->
- **Each file** carries an SPDX header (`SPDX-License-Identifier: LGPL-2.1-or-later`), following the [REUSE](https://reuse.software) convention, which can be checked in CI.
<!-- REUSE-IgnoreEnd -->
- **To confirm before the first public release:**
  - with Inria's IP / technology-transfer service (open-source release of software developed at Inria);
  - with the AURIS consortium agreement: ownership of results (foreground) produced by DCs employed by other beneficiaries, and any access rights to background brought into the simulator;
  - how contributions are accepted: a **DCO** (`Signed-off-by` on each commit) is the lightest option; a CLA is only needed if the IP office requires it. **TODO.**

### 2.3 Continuous integration (GitHub Actions)

- **Blocking job:** install SOFA with the official [`sofa-framework/sofa-setup-action`](https://github.com/sofa-framework/sofa-setup-action) (v5, binaries including SofaPython3), build Cosserat from source at a **pinned commit**, build the plugin and run the scene tests. Because the implant model needs `Frames2StrainCosseratMapping` (Cosserat `main`, not in the v26.06 release branch), this job uses **SOFA `master`** until SOFA v26.12 is released; then SOFA and Cosserat are both pinned to v26.12, and to each later release. Start with Ubuntu; add macOS and Windows once the build is stable.
- **Non-blocking job** (scheduled weekly, plus manual trigger): same build on SOFA `master` and **unpinned** Cosserat `main`, to detect API changes early. It is a separate workflow, so its failures never block pull requests.
- **Dependencies:** Cosserat (and later SoftRobots) are built from source in CI, at commits compatible with the SOFA version used; their commit SHAs are pinned in the workflow.
- **Tests:**
  - pure-Python unit tests (parameter parsing, metrics, geometry generation), which run **without** SOFA (fast, on every push);
  - scene smoke tests: load each example scene and run *N* time steps headless; check that it does not diverge and that the metrics are produced;
  - (later) regression tests on benchmark metrics, with tolerances.
- **Other checks:** `pre-commit` (formatting, `ruff`), REUSE licence check, documentation build.
- **Version policy:** upgrade the pinned SOFA release twice a year, following SOFA's release cycle (June/December).

### 2.4 Documentation site (GitHub Pages)

- **Tool:** MkDocs with the Material theme and `mkdocstrings` for the Python API reference. It is simpler than Sphinx for a mainly Python + Markdown project. C++ API docs (Doxygen) can be added later if the C++ part grows.
- **Deployment:** GitHub Actions (`actions/deploy-pages`) on every push to `main`; later, versioned docs per release (e.g. with `mike`).
- **Content:** installation (SOFA binaries + plugin), user guide, tutorials, benchmark protocol, DC14 ↔ DC15 interface specification, data registry, how to cite, contributing.

### 2.5 Example scenes and tutorials (training use)

A graded path for students, surgeons-in-training and engineers:

1. Load and display a synthetic cochlea-like duct (rigid).
2. Insert an electrode array modelled as a Cosserat rod, at constant speed; plot the insertion force.
3. Contact and friction: effect of the friction coefficient and of the insertion speed.
4. Change the insertion strategy (angle, speed profile, advance-off-stylet, …) and compare the metrics.
5. Robotic instrument (SoftRobots-based actuation).
6. Load a patient-specific anatomy from the digital twin (DC14) through the parameter file.
7. Run the benchmark and read the report.

Tutorials are Jupyter notebooks or annotated Python scenes, run in CI where possible.
**TODO:** which training events of the doctoral network (schools, workshops) they should support.

### 2.6 Citation: `CITATION.cff`

A `CITATION.cff` at the repository root (GitHub shows a "Cite this repository" button and
Zenodo reads it). It includes the authors with their ORCIDs, the licence, the repository URL,
the DOI (concept DOI, after the first Zenodo release), the AURIS funding acknowledgement and
the grant agreement number (**TODO**).

### 2.7 Releases, DOI, archiving

| Step | Tool | What it gives | Who / when |
|---|---|---|---|
| Versioned releases | GitHub Releases, tags `vMAJOR.MINOR.PATCH` (SemVer); release notes state the compatible SOFA version | Reproducible versions | Maintainers, at least once per SOFA release |
| DOI | **Zenodo–GitHub integration**: each GitHub release is archived on Zenodo and gets a version DOI, plus one "concept DOI" for all versions | Citable software | Enable once in Zenodo (steps below) |
| Long-term archive | **Software Heritage** (Inria-backed, UNESCO-supported): archives the full Git history and gives intrinsic identifiers (SWHID) | Permanent access, even if GitHub or the org disappears | "Save code now" after each release, or automatic crawling |
| Research output | **HAL** software deposit (Inria/CNRS open archive), linked to Software Heritage | Visible in French research evaluation and Inria reports; links the software to the authors and labs | Deposit at the first major release, then for new major versions |

These four steps together make the commitment checkable: even without anyone maintaining the
GitHub org, the code stays citable (DOI), archived (SWHID) and listed in HAL.

**Steps for the user** (Claude does not create these accounts or records):

1. *Zenodo:* log in to zenodo.org with GitHub → *Account → GitHub* → turn on the AURIS repository (needs owner rights on the org; an org owner may have to approve the Zenodo OAuth app for the org) → publish a GitHub release → check the Zenodo record and its metadata → add the concept DOI to `CITATION.cff` and to the README badge.
2. *Software Heritage:* go to `archive.softwareheritage.org/save/` → enter the repository URL (type `git`) → wait for archiving → copy the SWHID of the release into the README and the HAL deposit.
3. *HAL:* `hal.science` → *Deposit* → document type *Software* → give the SWHID (HAL then fetches the code from Software Heritage) → fill in metadata (authors, Inria DEFROST / Université de Lille affiliations, licence, AURIS project and grant number) → submit for moderation.

### 2.8 Maintenance after the project

"Maintain access" must be defined precisely, otherwise it cannot be checked. Proposal (**TODO**,
to be agreed with DEFROST management):

- **Guaranteed** (no time limit): the repository stays public or is transferred to an Inria org; releases stay on Zenodo; the code stays in Software Heritage and HAL.
- **Best effort** (TODO: *N* years after the end of the project): one compatibility check per SOFA release; answers to issues; security fixes for the CI.
- **Named contacts** in `MAINTAINERS.md`, with a permanent position holder as the last-resort contact.

---

## 3. Data sharing (options and questions for the consortium)

This section does **not** take decisions. It lists options and the questions the consortium
must answer, to fill "[repository to be confirmed]" and "[partner(s) to be confirmed]".

### 3.1 Which resources

| Resource | Likely sensitivity | Likely producer |
|---|---|---|
| OCT datasets | Depends on origin (phantom, cadaveric temporal bone, patient) | **TODO** |
| US datasets | Same | **TODO** |
| CT / µCT and segmented anatomical models | Patient CT is personal data; cadaveric specimens need donor consent; synthetic models are open | **TODO** |
| Digital-twin models and parameters (DC14) | Low if derived from open or synthetic data; otherwise same as their source | DC14 host: **TODO** |
| Navigation protocols | Low (methods), unless they embed clinical data | **TODO** |
| Experimental measurements for validation (insertion forces, …) | Low (phantom); moderate (cadaver) | **TODO** |

### 3.2 Repository options

| Option | Strengths | Limits | Fits best for |
|---|---|---|---|
| **Zenodo** (CERN, EU-funded) | Free, DOI per version, GitHub integration, known to EU reviewers, can restrict access to files with an access request | 50 GB per record by default (more on request); generic metadata; access control is basic | Open models, protocols, small and medium open datasets, digital-twin parameter sets |
| **Recherche Data Gouv** (French national, Dataverse-based) | National, institutional backing; many French institutions have an institutional space (check which one applies to Inria and Université de Lille); curation support; DOI; restricted files with access requests; strong French support network (data workshops) | Mainly for French institutions: non-French partners would deposit through a French partner | Data produced by French partners; datasets that need curation |
| **Partner's institutional repository** | Close to the data producer; local ethics and DPO support; may already have approvals for clinical data | Heterogeneous; persistence after the project depends on the partner | Patient-derived data that cannot leave the producer's institution |
| **Controlled-access platform** (e.g. a hospital data platform or a domain-specific repository) | Formal data access committee, data use agreements | Heavier procedures | Sensitive clinical OCT/US/CT data |

A **mixed model** is likely: open resources on Zenodo (or Recherche Data Gouv), sensitive data
at the producing partner under controlled access, all listed in one catalogue (e.g. a page in
the simulator documentation built from `data/registry.yaml`).

### 3.3 FAIR principles and licences

- **Findable:** DOI per dataset version; rich metadata; listed in the AURIS data catalogue.
- **Accessible:** open by default; for sensitive data, the metadata stays open and access to the files goes through a documented procedure.
- **Interoperable:** open formats (§4.2); documented units and coordinate frames; JSON Schema for parameters.
- **Reusable:** clear licence; provenance (acquisition device and protocol, segmentation method, software version used); README per dataset.
- **Suggested licences:** CC-BY-4.0 for models, protocols and open datasets; CC0 for metadata; a specific data use agreement (DUA) for controlled-access data.

### 3.4 Patient-derived data: anonymisation, consent, access

- Under GDPR, pseudonymised data is still personal data. Data can only be shared openly if it is truly **anonymised**, which is hard for imaging (e.g. a head CT can allow face reconstruction, so it needs *defacing*; DICOM headers need cleaning).
- Questions for each data producer:
  - Is there an ethics approval and an informed consent that cover **sharing and reuse** (not only the original study)?
  - Does a Data Protection Impact Assessment (DPIA) exist? Who is the controller, and which DPO is involved?
  - Can derived products (segmented meshes, statistical shape models, identified parameters) be shared openly even if the raw images cannot? This is often the most useful route for the simulator.
  - Are transfers outside the EU/EEA involved (non-EU partners)?
- Recommendation for the simulator: rely first on **synthetic**, **phantom** and **derived** (non-identifying) models, so that the open software never depends on restricted data to run.

### 3.5 Link with the Data Management Plan and the consortium agreement

- Horizon Europe requires a **Data Management Plan (DMP)**, delivered early in the project and updated during it, following the principle "as open as possible, as closed as necessary". The answers to §3 belong in the DMP. **TODO:** DMP deliverable number and due date; who writes it.
- The open-science obligations come from the grant agreement (Horizon Europe Model Grant Agreement, open-science article and annex; to be checked against the signed AURIS GA).
- The **consortium agreement** defines ownership and access rights for background and results. It must allow (i) open release of the simulator under LGPL and (ii) open release of the datasets and models listed in the DMP, or say which ones are excluded. **TODO:** check the relevant clauses.

### 3.6 Questions to send to the consortium

1. Which partner(s) manage the data repository ("[partner(s) to be confirmed]")?
2. Which repository ("[repository to be confirmed]"), or which mixed model?
3. For each dataset type in §3.1: who produces it, origin (phantom / cadaveric / patient), approvals, and whether it can be open, restricted or not shared.
4. Licence for open datasets and models (CC-BY-4.0 proposed).
5. Who validates anonymisation (DPO, ethics committee)?
6. Retention period after the project, and who pays for it if it is not free.

---

## 4. Interface between DC14 (digital twin) and DC15 (simulator)

### 4.1 Principle

The digital twin (DC14) and the simulator (DC15) exchange **files with a versioned schema**
first; a live coupling (streaming during a simulation) can come later if the use cases need it
(**TODO** with DC14).

```
DC14 digital twin                         DC15 simulator
-----------------                         --------------
patient/specimen anatomy  ── meshes ──▶   scene builder (auris_sim)
identified parameters     ── case.yaml ─▶ materials, contacts, instrument
                                          │
                          ◀── results ──  forces, trajectories, metrics
model update / calibration                (HDF5/CSV + metrics.json)
```

### 4.2 Formats

| Content | Format | Notes |
|---|---|---|
| Surface meshes (bony labyrinth, scala walls, round window) | **STL** (binary) or **OBJ** | STL has no units and no fields: units and frame go in the parameter file |
| Volume meshes (deformable tissues) | **VTK** (`.vtu` XML or legacy `.vtk`) | Preferred: can carry fields (material IDs, fibre directions, labels) |
| Volume meshes from Gmsh | **MSH** (Gmsh format; check which version SOFA's `MeshGmshLoader` reads) | Accepted; converted to VTK if needed (`meshio`) |
| Instrument geometry (electrode array, tools) | Parameters in YAML (lengths, diameters, stiffness profile) + optional STL for visualisation | |
| Scene and case parameters | **YAML** (human-written) or **JSON** (machine-written), validated by a **JSON Schema** in `schemas/` | Field `schema_version` in every file |
| Time series results | **HDF5** (large) or **CSV** (small) | One column/dataset per quantity, units in metadata |
| Metrics | **JSON** (`metrics.json`) | Fixed keys defined by the benchmark protocol |

**Conventions** (proposed):

- **Units:** SI in exchange files (m, kg, s, N, Pa), with an explicit `units` block. A scene may rescale internally (e.g. to mm) through one documented factor.
- **Coordinate frame:** a cochlear frame based on the consensus cochlear coordinate system (Verbist et al., *Otol Neurotol* 2010; check the reference), so that angular insertion depth is comparable across anatomies. Each mesh comes with its rigid transform to this frame.
- **Provenance:** each referenced file has a DOI (or local path) and a SHA-256 checksum.

Example `case.yaml` (illustrative, values are placeholders):

```yaml
schema_version: 0.1
units: {length: m, mass: kg, time: s, force: N, pressure: Pa}
anatomy:
  id: synthetic-spiral-001          # or a DC14 anatomy ID
  source: {type: synthetic, generator: auris_sim.geometry.spiral_duct, seed: 0}
  frame: cochlear_consensus
  meshes:
    scala_tympani_wall: {file: st_wall.stl, sha256: "<...>"}
instrument:
  type: electrode_array
  model: cosserat                   # Cosserat rod (Frames2Strain)
  length: 0.025                     # placeholder
  radius: 0.0003                    # placeholder
  young_modulus: 1.0e8              # placeholder (uniform sections)
  sections:                         # optional: explicit non-uniform profile
    - {length: 0.0012, young_modulus: 3.0e8}
    - ...
strategy:
  insertion_speed: 0.001            # m/s, placeholder
  insertion_depth: 0.020            # m, tip depth beyond the entrance
contact:
  friction: 0.1                     # placeholder
simulation:
  dt: 0.001
  duration: 30.0
outputs: [insertion_force, tip_trajectory, contact_forces, metrics]
```

### 4.3 Responsibilities

| | DC14 | DC15 |
|---|---|---|
| Owns | Anatomy reconstruction, parameter identification, twin update | Physics models, instrument models, scene builder, metrics |
| Delivers | Meshes + `case.yaml` following the schema | Results + metrics following the schema |
| Shared | JSON Schema in this repository; changes by pull request reviewed by both | Same |

**TODO:** confirm with DC14 and both supervisors; DC14 host institution; where the digital twin code lives (same org or elsewhere).

### 4.4 Benchmark protocol

Purpose: compare **robotic instruments** and **cochlear-implantation strategies** in a
reproducible way, and validate the simulator against experiments.

**Benchmark definition** (`benchmarks/<name>/benchmark.yaml`):

- a set of **anatomies** (synthetic first, then DC14 anatomies when available);
- a set of **instruments** (electrode arrays, robotic insertion tools);
- a set of **strategies** (insertion speed and profile, insertion angle and axis, depth, stylet use, robotic vs manual-like profile, …);
- fixed simulation settings and random seeds;
- the list of metrics and their definitions.

**Metrics** (proposed; definitions to be agreed with clinical partners, **TODO**):

| Family | Metric | Unit |
|---|---|---|
| Insertion force | Peak insertion force; mean force; force vs insertion depth curve; insertion work (integral) | N, N, N vs mm, J |
| Trauma indicators | Max contact force and pressure on the lateral wall; contact force on the basilar membrane region (surrogate); scalar translocation event (crossing of the basilar membrane surface) and depth at which it happens; tip fold-over / buckling event | N, Pa, bool + mm |
| Final electrode position | Angular insertion depth (in the cochlear frame); linear insertion depth; scalar location of each contact; distance to the modiolus (or a wrapping factor); coverage of the cochlear duct | deg, mm, label, mm, % |
| Computation | Real-time factor; time per step; number of contacts | –, ms, – |
| Validation | Error between simulated and measured force-vs-depth curves (RMSE, peak error) on phantoms or specimens | N |

**Outputs per run:** `results/<benchmark>/<case>/<run_id>/` with `metrics.json`,
time series (HDF5/CSV) and a `manifest.json` (simulator version and git SHA or DOI, SOFA
version, plugin versions, parameter-file hash, machine, date). A report script turns a set of
runs into tables and plots for the documentation.

**Validation data:** experimental insertion forces, OCT/US observations of insertions on
phantoms or specimens. **TODO:** which partner produces them and under which access conditions.

---

## 5. Repository layout (proposed)

```
auris-simulator/
├── CMakeLists.txt                  # SOFA plugin "AurisSimulator"
├── AurisSimulatorConfig.cmake.in
├── src/AurisSimulator/             # C++ components (config.h.in, init.cpp, components/)
├── python/auris_sim/               # Python package: scene builder, geometry, metrics, io, benchmark
│   ├── geometry/                   #   synthetic geometries (spiral duct, …), mesh files
│   ├── scene/                      #   SofaPython3 scene builders
│   ├── metrics/                    #   metric definitions (pure numpy, no SOFA)
│   ├── io/                         #   case.yaml loading + schema validation
│   ├── schemas/                    #   JSON Schemas (case; later benchmark, metrics, manifest)
│   ├── results.py                  #   run outputs: metrics.json, timeseries.csv, manifest.json
│   └── data/                       #   registry access + checked downloads
├── pyproject.toml                  # pip-installable package (pure-Python parts work without SOFA)
├── scenes/                         # runnable example scenes (runSofa / python)
├── tutorials/                      # training material (notebooks / annotated scenes)
├── benchmarks/                     # benchmark definitions
├── data/registry.yaml              # external datasets: DOI, licence, checksum, access
├── tests/                          # pytest: unit (no SOFA) + scene smoke tests (SOFA)
├── docs/                           # MkDocs site (this design note lives here)
├── .github/workflows/              # CI, docs deployment, SOFA master job
├── CITATION.cff
├── LICENSE                         # LGPL-2.1-or-later (+ LICENSES/ for REUSE)
├── MAINTAINERS.md
├── CONTRIBUTING.md
└── README.md
```

---

## 6. Roadmap

DC14/DC15 start dates, durations and secondments are **TODO**. The roadmap is therefore
expressed relative to the **DC15 start (month M0)**, and also relative to SOFA releases.

| Phase | When | Content | Exit criterion |
|---|---|---|---|
| 0. Foundations | Now → DC15 M0 | This design note; repository skeleton; CI; docs site; licence confirmed; AURIS org created | CI green on SOFA master + pinned Cosserat, then on v26.12; docs online |
| 1. Baseline simulator | M0 → M6 | Synthetic cochlea-like geometry; Cosserat electrode insertion with guide; contact/friction; insertion force and first metrics; tutorials 1–3 | First release `v0.1.0` + Zenodo DOI |
| 2. Digital-twin interface v1 | M6 → M18 | `case.yaml` schema agreed with DC14; first real (derived, shareable) anatomies; benchmark v1; tutorials 4–6 | Release `v0.x` with benchmark v1; HAL deposit |
| 3. Hybrid simulation and robotics | M18 → M30 | "Hybrid" features (TODO definition); robotic instruments (SoftRobots); validation against experimental data | Validation report; publication(s) |
| 4. Consolidation and training | M30 → end of DC15 | Training material for network events; stable API; final benchmark results | Release `v1.0.0`; SWHID + HAL; maintenance plan agreed |
| After the project | — | Maintenance as in §2.8 | Repository public and archived |

Every release is aligned with the pinned SOFA version; the SOFA pin is updated after each SOFA
release (June/December).

---

## 7. Proposed rewrite of the P2 paragraph (for reports)

> **Research resources.** Inria will release the DC15 hybrid ear-surgery simulator as open-source
> software (LGPL-2.1-or-later, built on the SOFA framework) in a public GitHub repository of the
> AURIS network, with continuous integration, online documentation and training tutorials.
> Each release will receive a DOI through Zenodo and will be archived in Software Heritage and
> deposited in HAL, so that the simulator remains citable and accessible after the end of the
> project; Inria will keep the repository available and, as far as possible, compatible with new
> SOFA releases. Together with the DC14 digital twin, through a documented exchange format and a
> shared benchmark protocol, the simulator will support the testing and comparison of robotic
> instruments and cochlear-implantation strategies. The digital twin, OCT/US datasets,
> anatomical models and navigation protocols will be shared through [repository], managed by
> [partner(s)], following the FAIR principles and the project's Data Management Plan, and in
> line with IP, ethical and data-protection requirements.

---

## 8. Open questions and TODO list

**Project facts (not to be invented):**

- [ ] AURIS grant agreement number (for `CITATION.cff`, HAL, acknowledgements).
- [ ] DC14: title, host institution, supervisors, start date, duration.
- [ ] DC15: title, supervisors, start date, duration, secondments.
- [ ] Meaning of "hybrid" in "hybrid ear-surgery simulator" (§1.1).
- [ ] Partners producing OCT, US, CT/µCT, anatomical models, navigation protocols, validation measurements (§3.1).
- [ ] Repository and data manager for "[repository to be confirmed]" / "[partner(s) to be confirmed]" (§3.6).
- [ ] DMP deliverable number, due date and author (§3.5).
- [ ] Training events of the network that tutorials should support (§2.5).

**Decisions to confirm:**

- [x] AURIS GitHub org name: `eu-auris` (2026-11-13).
- [ ] Owners of the `eu-auris` org (≥ 2 permanent Inria staff) (§2.1).
- [ ] LGPL-2.1-or-later confirmed by Inria's IP office and compatible with the consortium agreement (§2.2).
- [ ] Contribution policy: DCO or CLA (§2.2).
- [ ] Copyright holder(s) in SPDX headers: the skeleton uses "AURIS simulator contributors"; Inria's IP office may require e.g. "Inria" or the joint DEFROST partners (§2.2).
- [ ] Licence of SoftRobots.Inverse, if needed (§1.1).
- [ ] Switch the blocking CI to SOFA v26.12 + Cosserat v26.12 when released, after checking that Cosserat v26.12 contains `Frames2StrainCosseratMapping` (§2.3).
- [ ] Agreement of the rights holders before publishing the calibrated electrode-array profile and the specimen-derived cochlea meshes (§1.2, §3).
- [ ] Mirror on `gitlab.inria.fr`: yes or no (§2.1).
- [ ] Post-project maintenance level and duration (§2.8).
- [ ] Unit system and cochlear coordinate frame, with DC14 (§4.2).
- [ ] Metric definitions, with clinical partners (§4.4).
- [ ] Live coupling DC14 ↔ DC15: needed or not (§4.1).
