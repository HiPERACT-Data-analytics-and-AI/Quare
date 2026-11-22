"""
Importer for the 2026 multi-node OpenFOAM motorBike measurements with power.

The source tree has one directory per platform and one directory per run
configuration below it; the mesh sizes are directories of the configuration::

    <source>/<platform dir>/<prefix>_<N>_nodes_<R>_MPI_<P>_PER_NODE_<C>_PER_CCX/<size>/

(``N`` nodes, ``R`` MPI ranks in total, ``P`` ranks per node, ``C`` ranks per
CCX).  Every configuration becomes one Quare *machine* named
``<platform>_<N>N_<C>PCCX_<R>``; the trailing rank count is read by Quare as
the core count, so the x axis (cells per rank) is the cells per MPI rank.

Per size four kinds of runs are imported, each with a *tag* on its date
directory (``<date>_<tag>``):

``counters``
    Timing runs: every ``log.simpleFoam*`` except the MPI trace and power runs
    (``.uProfMPI``, ``.power_A``, ``.power_B``); byte-identical copies of a
    log are imported once.
``topdown``
    The counter file ``prof.AMD.ALL_<size>_ipc_2.csv``.
``trace``
    ``log.simpleFoam.uProfMPI`` and the ``mpi-summary.csv`` of the MPI trace
    (``AMDuProf-simpleFoam-HPC_MPI/mpi/lwt/``, else ``mpi-summary-<size>.csv``).
``power``
    ``log.simpleFoam.power_B`` and the ``timechart.csv`` of every node
    (``POWER_<n>_B/*/timechart.csv``).

The mapping file is JSON with ``session``, ``use_case``, ``sizes`` and
``platforms`` (platform name used in the machine name -> ``source`` directory
and run ``prefix``).

Authors: Marcin Lawenda, Łukasz Szustak
"""

from __future__ import annotations

import hashlib
import json
import re
from argparse import Namespace
from datetime import datetime
from pathlib import Path

from .motorbike2024 import (
    COUNTERS,
    SOLVER_LOG,
    TOPDOWN,
    TRACE,
    _copy,
    _RunWriter,
    _size_dir,
    log_start_time,
    profile_time,
)

POWER = "power"
ROLES: tuple[str, ...] = (COUNTERS, TOPDOWN, TRACE, POWER)

EXCLUDED_LOGS = (".uProfMPI", ".power_A", ".power_B")
MPI_TRACE_LOG = "log.simpleFoam.uProfMPI"
POWER_LOG = "log.simpleFoam.power_B"
TOPDOWN_FILE = "prof.AMD.ALL_{size}_ipc_2.csv"
MPI_SUMMARY = Path("AMDuProf-simpleFoam-HPC_MPI/mpi/lwt/mpi-summary.csv")
MPI_SUMMARY_FALLBACK = "mpi-summary-{size}.csv"
_FALLBACK_DATE = datetime(2026, 1, 1)
_POWER_DIR = re.compile(r"^POWER_(\d+)_B$")


def load_mapping(path: Path) -> dict:
    """
    Read and validate a mapping file.

    :raises ValueError: If a key is missing or a platform has no ``source`` or
        ``prefix``.
    """
    mapping = json.loads(path.read_text())
    for key in ("session", "use_case", "sizes", "platforms"):
        if key not in mapping:
            raise ValueError(f"{path}: missing key '{key}'")
    for name, platform in mapping["platforms"].items():
        for key in ("source", "prefix"):
            if key not in platform:
                raise ValueError(f"{path}: platform '{name}' has no '{key}'")
    return mapping


def find_configurations(
    source: Path, platform: str, spec: dict
) -> dict[str, tuple[Path, dict[str, int]]]:
    """
    Find the run configurations of one platform.

    :returns: ``{machine name: (configuration directory, parameters)}`` where
        the parameters are ``nodes``, ``ranks``, ``per_node`` and ``ccx``.
        Directories that do not match the run naming (``Broken_...``) are
        ignored.
    """
    pattern = re.compile(
        rf"^{re.escape(spec['prefix'])}_(?P<nodes>\d+)_nodes_(?P<ranks>\d+)_MPI_"
        r"(?P<per_node>\d+)_PER_NODE_(?P<ccx>\d+)_PER_CCX$"
    )
    found: dict[str, tuple[Path, dict[str, int]]] = {}
    for directory in sorted((source / spec["source"]).glob("*")):
        match = pattern.match(directory.name)
        if match is None or not directory.is_dir():
            continue
        values = {k: int(v) for k, v in match.groupdict().items()}
        name = (
            f"{platform}_{values['nodes']}N_{values['ccx']}PCCX_{values['ranks']}"
        )
        found[name] = (directory, values)
    return found


def _import_counters(size_dir: Path, writer: _RunWriter) -> int:
    """Timing runs; identical copies of a log are imported once."""
    mesh_log = size_dir / "log.checkMesh"
    seen: set[str] = set()
    imported = 0
    for log_path in sorted(size_dir.glob("log.simpleFoam*")):
        match = SOLVER_LOG.match(log_path.name)
        if match is None or log_path.name.endswith(EXCLUDED_LOGS):
            continue
        digest = hashlib.md5(log_path.read_bytes()).hexdigest()
        if digest in seen:
            continue
        seen.add(digest)
        run_name = match.group("run").lstrip("._") or "run"
        run_dir = writer.run_dir(log_start_time(log_path), COUNTERS, _FALLBACK_DATE)
        logs = run_dir / "OpenFOAMlogs"
        _copy(mesh_log, logs / f"{run_name}.checkMesh.log")
        _copy(log_path, logs / f"{run_name}.{match.group('solver')}.log")
        imported += 1
    return imported


def _import_topdown(size_dir: Path, size: str, writer: _RunWriter) -> int:
    counter_file = size_dir / TOPDOWN_FILE.format(size=size)
    if not counter_file.exists():
        return 0
    run_dir = writer.run_dir(profile_time(counter_file), TOPDOWN, _FALLBACK_DATE)
    _copy(counter_file, run_dir / "AMDuProfPCM" / counter_file.name)
    return 1


def _import_solver_run(
    size_dir: Path, log_name: str, tag: str, writer: _RunWriter
) -> Path | None:
    """Copy checkMesh and solver log of a special run; return its directory."""
    log_path = size_dir / log_name
    if not log_path.exists():
        return None
    run_dir = writer.run_dir(log_start_time(log_path), tag, _FALLBACK_DATE)
    _copy(size_dir / "log.checkMesh", run_dir / "OpenFOAMlogs" / "run.checkMesh.log")
    _copy(log_path, run_dir / "OpenFOAMlogs" / "run.simpleFoam.log")
    return run_dir


def _import_trace(size_dir: Path, size: str, writer: _RunWriter) -> int:
    summary = size_dir / MPI_SUMMARY
    if not summary.exists():
        summary = size_dir / MPI_SUMMARY_FALLBACK.format(size=size)
    if not summary.exists() or not (size_dir / MPI_TRACE_LOG).exists():
        return 0
    run_dir = _import_solver_run(size_dir, MPI_TRACE_LOG, TRACE, writer)
    assert run_dir is not None
    _copy(summary, run_dir / "AMDuProfMPI" / "mpi-summary.csv")
    return 1


def _import_power(size_dir: Path, writer: _RunWriter) -> int:
    charts = {
        int(m.group(1)): next(iter(sorted(d.glob("*/timechart.csv"))), None)
        for d in size_dir.iterdir()
        if d.is_dir() and (m := _POWER_DIR.match(d.name))
    }
    charts = {n: c for n, c in charts.items() if c is not None}
    if not charts:
        return 0
    run_dir = _import_solver_run(size_dir, POWER_LOG, POWER, writer)
    if run_dir is None:
        return 0
    for node, chart in sorted(charts.items()):
        _copy(chart, run_dir / "AMDuProfTimechart" / f"node{node}.csv")
    return 1


def import_motorbike_2026(
    source: Path,
    raw_data_path: Path,
    mapping: dict,
    machines: list[str] | None = None,
) -> dict[str, int]:
    """
    Convert the 2026 motorBike tree below *source* into the raw data layout.

    :param machines: Machine names (``<platform>_<N>N_<C>PCCX_<R>``) to import;
        all configurations found when ``None``.
    :returns: Number of runs imported per role.
    :raises ValueError: If a requested machine is not found.
    """
    configurations: dict[str, tuple[Path, dict[str, int]]] = {}
    for platform, spec in mapping["platforms"].items():
        configurations |= find_configurations(source, platform, spec)
    selected = machines or list(configurations)
    unknown = [name for name in selected if name not in configurations]
    if unknown:
        raise ValueError(f"not found in the source tree: {', '.join(unknown)}")

    counts = dict.fromkeys(ROLES, 0)
    for machine in selected:
        directory, _ = configurations[machine]
        for size in mapping["sizes"]:
            size_dir = _size_dir(directory, size)
            if size_dir is None:
                continue
            writer = _RunWriter(
                raw_data_path
                / mapping["session"]
                / machine
                / mapping["use_case"]
                / size
            )
            counts[COUNTERS] += _import_counters(size_dir, writer)
            counts[TOPDOWN] += _import_topdown(size_dir, size, writer)
            counts[TRACE] += _import_trace(size_dir, size, writer)
            counts[POWER] += _import_power(size_dir, writer)
    return counts


def run(args: Namespace, raw_data_path: Path) -> None:
    """Run the importer for the parsed command-line arguments."""
    mapping = load_mapping(args.map)
    counts = import_motorbike_2026(args.source, raw_data_path, mapping, args.machine)
    print(
        "Imported "
        + ", ".join(f"{count} {role} run(s)" for role, count in counts.items())
        + f" into {raw_data_path}"
    )
