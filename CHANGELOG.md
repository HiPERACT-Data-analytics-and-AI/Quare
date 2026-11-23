# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added

- End-to-end tests on a synthetic AMD uProf PCM data set (`tests/`) and a
  test step in CI
- Łukasz Szustak added as author (`CITATION.cff`, package metadata)
- `OpenFOAMlogs_ext`: parser, models and loader for `checkMesh` and
  `simpleFoam`/`pimpleFoam` logs (cells, ranks, number of time steps, first and
  last step time, total time) stored as run-level metrics
- `quare import-data` with the `motorbike-2024` layout: converts the 2024
  single-node motorBike measurements into the raw layout
  (`examples/motorbike_2024_import.json`)
- Date directories may carry a tag after the timestamp
  (`YYYYMMDD_HHMMSS_<tag>`); the tag is part of the repetition name
- Test data and tests for the import and loading of the 2024 measurements; the
  loaded values equal the results of the original analysis scripts
- OpenFOAM analyses (`OpenFOAMlogs_ext/plotter.py`): FVOPS, L3 and L2 ratios,
  top-down values (Backend Bound Memory, Frontend Bound, Retiring) and MPI
  ratios (min/avg/max), selected by the run tags `counters`, `trace` and
  `topdown`; plus a combined `Summary.png` (FVOPS and ratios); results equal
  the original scripts to 1e-12
- Import of all seven 2024 platforms (Rome, Milan, Milan X, Genoa 128/192,
  Genoa X, Bergamo); `trace_logs` in the import mapping selects the log of the
  traced run when `mpi.trace0` belongs to another run (Bergamo `xsmall`).
  Tests on `xsmall` data of Rome, Genoa 192 and Bergamo 256 reproduce the
  original scripts to 1e-12
- Optional setting `compare_machines`: `Comparison.png` with one panel per
  machine
- Optional setting `predicted_fvops` (`{machine: {label, cells_per_rank,
  fvops}}`): predicted points drawn as red stars on the panel of that machine
  in `Comparison.png`, as in `128_uProfAMD_AOCC_hipic.py`. The values are
  input, not computed: in the script they are hard-coded and no script derives
  them
- With `compare_machines`: `Timing comparison.png` (all runs per machine and
  size, as `timingComp.py`) and the pairwise speed-up ranges `Speedup.csv` /
  `Speedup.png` (as `speddup.py`, computed from unrounded times); optional
  setting `machine_labels` for display names; new analyses `Time stepping
  time` and `Total time` (median of the timing runs)
- 2026 multi-node data: `quare import-data --layout motorbike-2026`
  (`examples/motorbike_2026_import.json`) turns every run configuration into a
  machine `<platform>_<N>N_<C>PCCX_<R>` (nodes, ranks per CCX, ranks) with
  `counters`, `topdown`, `trace` and `power` runs
- `AMDuProfTimechart_ext`: node power traces of the uProf timechart
- New analyses `CVOPTS`, `Aggregate node power`, `Average node power`,
  `Aggregate energy`, `MPI volume (aggregate)` and `MPI volume (per rank)`;
  they equal `app_info.py`, `en_info.py` and `mpi_info.py` of the dataset
  scripts to 1e-12 on the test data
- PCM files with a `System (Aggregated)` row are loaded (processing unit
  `system`); analyses use the aggregate when present, as `uProf_info.py`
- OpenFOAM logs with `Total time = <s>` (2026 runs) are parsed
- `quare export-dataset`: builds the machine-learning input table of the
  motorBike study (hardware, application, power, MPI volume and uProf PCM
  features per configuration and mesh size) from the database. Output style
  `legacy` is byte-identical to `build_dataset_power.py` (checked against a row
  of the real dataset), `--style csv` writes a plain CSV; `--no-power` gives the
  `build_dataset.py` columns. Hardware table: `quare/data/cpu_features.json`

### Fixed

- `quare import-data` no longer registers its shared arguments once per importer
- Plot file names no longer break on units that contain `/`
- `quare create-db` failed on a clean install: extension modules are now
  imported as regular package modules, so SQLAlchemy can resolve the
  annotations of the ORM models
- `plot` mixed metrics and analyses in each other's output; they are now
  queried separately
- `plot` wrote the analyses of all extensions into one folder and they
  overwrote each other; they now go to `analyses/<profiler>/`
- A repetition can now be shared by several extensions: the second extension
  used to skip a repetition that the first one had created
- AMD uProf PCM machine info: `SMT Enabled in HW/OS` was always `True`
  (`bool("False")`), and an empty `System:` value violated the NOT NULL
  constraint
- `repetition_name_contains` is optional, as the settings reference implies
- README described the raw data layout in the wrong order

### Removed

- Two stray files that were never importable
  (`fvops_aocc_analyzer.py.`, `plotter_BACKUP.py.`); they stay in the git history

---

## [0.1.0] — 2026-06-20

Initial public release.

### Added

- Three-step CLI pipeline: `preprocess-data`, `create-db`, `plot`
- `--config PATH` argument on all subcommands; settings path also resolved
  from `QUARE_SETTINGS` environment variable with in-process caching
- Plugin/extension architecture: profiler extensions are discovered
  automatically from `quare/extensions/*_ext/` directories
- **AMDuProfPCM_ext** — AMD uProf Performance Counter Monitor extension
  (preprocessor, ORM models, loader, plotter with six L2 cache ratio analyses)
- **AMDuProfMPI_ext** — AMD uProf MPI profiler extension
- **OpenFOAMlogs_ext** — stub extension (work in progress)
- Shared `AMDuProfDataRetriever` base class for AMD hardware metadata
- Full Sphinx RST API documentation across all 21 source modules
- MIT License

### Fixed

- `UnboundLocalError` in `DataRetrieversManager.init_retriever` when the
  extension module's spec or loader was `None`
- Cache hits returning stale data for all-zero metric series (truthiness
  check `if metric:` replaced with `if metric is not None:`)
- `Plotter.make_all` passing `[""]` instead of `[]` for analyses/metrics,
  silently preventing all analyses from running
- Key collision in `InMemoryMetricsDict` and `UniqueMetricKey.__hash__`
  (now uses null-byte separator and tuple hash)
- Division by zero in all six AMDuProfPCM L2 ratio calculations;
  introduced `_safe_ratio()` helper returning `None` for zero/None
  denominators
- `task_size_size` overwrite: numeric fallback now only runs when the
  settings lookup returned `None`
- Session leak on error paths — `close_db_session()` now called in
  `try/finally` in `create_db`, `plot`, and `main`
- `split_multi_block_csv` order-dependency caused by a shared file handle;
  file is now fully read into memory before splitting
- `mkdir()` → `mkdir(parents=True, exist_ok=True)` in preprocessed data
  path creation
- Absolute import in `AMDuProfPCM_ext/plotter.py` replaced with relative
  import
- Bare `print(e)` in preprocessor replaced with `logging.debug`

### Changed

- `_create_db_engine` renamed to `create_db_engine` (public)
- `plt.cla()` / `plt.clf()` calls removed after `plt.close()` (redundant)
- Removed unused dependencies: `tensorflow`, `tensorflow-probability`,
  `tensorflow-transform`, `prettytable`, `seaborn`, `tk`
- Added missing runtime dependencies: `pandas`, `numpy`, `matplotlib`
- `pyproject.toml`: filled description, authors, license, homepage,
  repository, keywords, classifiers; fixed `python ~3.10` → `^3.10`
- `settings.json` default paths changed to portable relative defaults
