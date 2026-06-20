# Contributing to Quare

Thank you for your interest in contributing. This guide covers everything you
need to get started — from setting up a dev environment to submitting a pull
request or adding a new profiler extension.

## Table of contents

- [Development setup](#development-setup)
- [Code style](#code-style)
- [Running the pre-commit hooks](#running-the-pre-commit-hooks)
- [Adding a new profiler extension](#adding-a-new-profiler-extension)
- [Submitting a pull request](#submitting-a-pull-request)
- [Reporting bugs and requesting features](#reporting-bugs-and-requesting-features)

---

## Development setup

### Prerequisites

- Python 3.10 or later
- [Poetry](https://python-poetry.org/) — dependency and build management
- `graphviz` system package — needed only for generating UML diagrams in the
  documentation

### Steps

```bash
git clone https://github.com/HiPERACT-Data-analytics-and-AI/Quare.git
cd Quare
poetry install          # installs runtime + dev dependencies
sudo apt install graphviz -y
pre-commit install      # register the git hooks
```

After this, every `git commit` will automatically run the quality checks
described below.

---

## Code style

Quare enforces a consistent style through automated tools — you do not need to
memorise rules; just run the hooks and let them fix things.

| Tool | Role |
|---|---|
| **black** | Code formatting (88-char lines) |
| **isort** | Import sorting (black-compatible profile) |
| **flake8** | Linting (with `flake8-bugbear`; max line length 88) |
| **pyupgrade** | Modernises syntax to Python 3.10+ |

### Docstrings

All public modules, classes, and functions must have Sphinx RST-format
docstrings. Use `:param name:`, `:type name:`, `:returns:`, `:rtype:`, and
`:raises ExcType:` tags. See any existing module for examples.

---

## Running the pre-commit hooks

To check all files at any time (not just on commit):

```bash
pre-commit run --all-files
```

To run a single hook by name:

```bash
pre-commit run black --all-files
```

Hooks that modify files (black, isort, mixed-line-ending) will apply changes
in place and exit with a non-zero code; simply `git add` the modified files
and re-run.

---

## Adding a new profiler extension

Each profiler lives in its own subdirectory under `quare/extensions/` with a
name ending in `_ext`. Quare discovers and loads extensions automatically at
runtime — no registration step is required.

### Required structure

```
quare/extensions/<profiler>_ext/
├── __init__.py
├── preprocessor.py
├── models.py
├── loader.py
└── plotter.py
```

### Module contracts

Each module must expose specific module-level attributes:

#### `preprocessor.py`

```python
__extension_data_preprocessor__: type[Preprocessor] = MyPreprocessor
```

Subclass `quare.preprocessor.Preprocessor` and override `preprocess()`.
Use `split_multi_block_csv()` if the profiler writes multiple logical
sections into a single CSV file.

#### `models.py`

Define two ORM models:

- A **metrics-dictionary** table (subclass `MetricsDictBase`) — one row per
  unique metric name/unit/processing-unit combination.
- A **metrics** table (subclass `MetricsBase`) — one row per individual
  measurement, foreign-keyed to the dictionary table via a `metric` column.

#### `loader.py`

Implement `ExtensionDataLoader` (see `quare/extension_abcs.py`) and expose
it as `__extension_data_loader__`.

#### `plotter.py`

Expose four module-level attributes:

```python
__extension_data_retriever__: type[DataRetriever] = ...
__extension_data_plotter__: type[Plotter] = ...
__extension_metrics_table__ = MyMetrics
__extension_metrics_dict__ = MyMetricsDict
```

Use the generic `Plotter` class unless you need custom plot logic. Subclass
`DataRetriever` to add derived analyses (see `AMDuProfPCM_ext` for examples).

### Reference implementation

`quare/extensions/AMDuProfPCM_ext/` is the most complete extension and is the
recommended starting point for new profiler integrations.

---

## Submitting a pull request

1. **Fork** the repository and create a branch from `main`:

   ```bash
   git checkout -b feature/my-new-extension
   ```

2. Make your changes. Ensure `pre-commit run --all-files` passes before pushing.

3. **Open a pull request** against `main`. In the PR description, explain:
   - What problem it solves or what profiler it adds
   - Any limitations or known gaps (stubs, WIP sections)
   - How it was tested (even manually)

4. A maintainer will review and merge. There is no formal review SLA; please
   allow a few working days.

---

## Reporting bugs and requesting features

Open an issue on GitHub:
<https://github.com/HiPERACT-Data-analytics-and-AI/Quare/issues>

For bugs, include:
- Quare version (`python -c "import quare; print(quare.__version__)"`)
- Python version and OS
- The full command you ran and the full error output
- A minimal reproducer if possible (anonymised data is fine)

For feature requests, describe the profiler tool, the data format, and the
analysis or visualisation you need.
