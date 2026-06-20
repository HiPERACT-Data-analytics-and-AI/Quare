# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
