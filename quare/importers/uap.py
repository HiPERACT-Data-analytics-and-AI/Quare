"""
Importer for the UAP OpenFOAM measurements (simpleFoam and pimpleFoam).

The source tree has one directory per platform, one per mesh size and one per
run below it::

    <source>/<platform dir>/<size>/<run>/<files>

The runs are told apart by their name; every one becomes a run directory
``<date>_<role>[-<label>]`` of the raw layout (the date is the start time of
the solver log):

========================  =====================  ============================
Source run                Tag                    Used for
========================  =====================  ============================
``run_1n1r``, ``1n2r``,   ``counters-<label>``   timing; the uProf PCM file of
``1n4r``                                         ``1n4r`` (cache ratios)
``run_1n5r``              ``topdown-1n5r``       top-down counters
``run_1n6r``              ``trace-1n6r``         MPI trace
``run_likL2``, ``L3``,    ``likwid``             LIKWID groups L2, L3, NUMA
``liknuma``                                      (one run)
``run_PROF_*``            ``profile``            OpenFOAM MPI profiling per
                                                 step (MilanX)
``run_PROFend_*``         ``profile-end``        control run of the profiling
========================  =====================  ============================

The label (``1n2r``) is the run name without ``run_``; the settings
``fvops_time_run`` / ``fvops_steps_run`` select by it.  The solver logs are
stored as ``run.simpleFoam.log`` (from ``log.mySimpleFoam``) and
``run.pimpleFoam.log`` (from ``log.myPimpleFoam``), the mesh log as
``run.renumberMesh.log`` (UAP has no ``checkMesh`` log; the cells come from
``Mesh region0 size:``).  The LIKWID files of pimpleFoam form a
second run, tagged ``likwid-pimpleFoam``.

Authors: Marcin Lawenda, Łukasz Szustak
"""

from __future__ import annotations

from argparse import Namespace
from datetime import datetime
from pathlib import Path

from .motorbike2024 import _copy, _RunWriter, load_mapping, log_start_time

TIMING_RUNS = ("1n1r", "1n2r", "1n4r")
PCM_RUN = "1n4r"
TOPDOWN_RUN = "1n5r"
TRACE_RUN = "1n6r"
LIKWID_RUNS = {"L2": "likL2", "L3": "likL3", "NUMA": "liknuma"}
SOLVER_LOGS = {"log.mySimpleFoam": "simpleFoam", "log.myPimpleFoam": "pimpleFoam"}
PCM_FILE = "prof.AMD.mySimpleFoam.csv"
MPI_SUMMARY = Path("mpi.trace/AMDuProf-mySimpleFoam-HPC_MPI/mpi/lwt/mpi-summary.csv")
LIKWID_FILE = "prof.{solver}.lik.{group}.txt"
LIKWID_SOLVERS = {"mySimpleFoam": "likwid", "myPimpleFoam": "likwid-pimpleFoam"}
"""Solver name in the file names -> tag of the LIKWID run of that solver."""
PROFILE_RUNS = {"run_PROF_*": "profile", "run_PROFend_*": "profile-end"}
"""Glob of the source run -> tag (the runs carry a date in their name)."""
FALLBACK_TIME = datetime(2024, 1, 1)


def _import_run(
    run_path: Path, tag: str, writer: _RunWriter, counter_file: str | None = None
) -> Path | None:
    """
    Import the logs (and optionally the PCM file) of one run.

    :returns: The new run directory, or ``None`` if the source run has no
        solver log.
    """
    logs = [run_path / name for name in SOLVER_LOGS if (run_path / name).exists()]
    if not logs:
        return None
    run_dir = writer.run_dir(log_start_time(logs[0]), tag, FALLBACK_TIME)
    for path in logs:
        _copy(path, run_dir / "OpenFOAMlogs" / f"run.{SOLVER_LOGS[path.name]}.log")
    mesh = run_path / "log.renumberMesh"
    if mesh.exists():
        _copy(mesh, run_dir / "OpenFOAMlogs" / "run.renumberMesh.log")
    if counter_file and (run_path / counter_file).exists():
        _copy(run_path / counter_file, run_dir / "AMDuProfPCM" / counter_file)
    return run_dir


def _import_likwid(
    size_path: Path, writer: _RunWriter, solver: str = "mySimpleFoam"
) -> bool:
    """Import the LIKWID files of *solver* of the L2, L3 and NUMA runs as one run."""
    files = {
        group: size_path / f"run_{run}" / LIKWID_FILE.format(solver=solver, group=group)
        for group, run in LIKWID_RUNS.items()
    }
    files = {group: path for group, path in files.items() if path.exists()}
    if not files:
        return False
    first = size_path / f"run_{LIKWID_RUNS['L2']}" / f"log.{solver}"
    start = log_start_time(first) if first.exists() else None
    run_dir = writer.run_dir(start, LIKWID_SOLVERS[solver], FALLBACK_TIME)
    for group, path in files.items():
        _copy(path, run_dir / "LIKWID" / f"{group}.txt")
    return True


def import_uap(
    source: Path,
    raw_data_path: Path,
    mapping: dict,
    machines: list[str] | None = None,
) -> dict[str, int]:
    """
    Convert the UAP tree below *source* into the raw data layout.

    :param source: Root directory that contains the platform directories.
    :param raw_data_path: Target root of the raw data tree (created if needed).
    :param mapping: Mapping read by :func:`~.motorbike2024.load_mapping`
        (``session``, ``use_case``, ``sizes``, ``machines`` with ``source``).
    :param machines: Names of the machines to import; all of the mapping when
        ``None``.
    :returns: Number of runs imported per role (``counters``, ``topdown``,
        ``trace``, ``likwid``, ``likwid-pimpleFoam``, ``profile``).
    :raises ValueError: If a requested machine is not in the mapping.
    """
    selected = machines or list(mapping["machines"])
    unknown = [name for name in selected if name not in mapping["machines"]]
    if unknown:
        raise ValueError(f"not in the mapping: {', '.join(unknown)}")

    counts = dict.fromkeys(
        ("counters", "topdown", "trace", *LIKWID_SOLVERS.values(), "profile"), 0
    )
    for machine_name in selected:
        platform = source / mapping["machines"][machine_name]["source"]
        used: set[str] = set()  # run names must be unique across the sizes
        for size in mapping["sizes"]:
            size_path = platform / size
            target = (
                raw_data_path
                / mapping["session"]
                / machine_name
                / mapping["use_case"]
                / size
            )
            writer = _RunWriter(target, used)
            for label in TIMING_RUNS:
                counter = PCM_FILE if label == PCM_RUN else None
                if _import_run(
                    size_path / f"run_{label}", f"counters-{label}", writer, counter
                ):
                    counts["counters"] += 1
            if _import_run(
                size_path / f"run_{TOPDOWN_RUN}",
                f"topdown-{TOPDOWN_RUN}",
                writer,
                PCM_FILE,
            ):
                counts["topdown"] += 1
            trace_path = size_path / f"run_{TRACE_RUN}"
            if (trace_path / MPI_SUMMARY).exists():
                run_dir = _import_run(trace_path, f"trace-{TRACE_RUN}", writer)
                if run_dir is not None:
                    _copy(
                        trace_path / MPI_SUMMARY,
                        run_dir / "AMDuProfMPI" / "mpi-summary.csv",
                    )
                    counts["trace"] += 1
            for solver, role in LIKWID_SOLVERS.items():
                if _import_likwid(size_path, writer, solver):
                    counts[role] += 1
            for pattern, tag in PROFILE_RUNS.items():
                for profile_path in sorted(size_path.glob(pattern)):
                    if _import_run(profile_path, tag, writer):
                        counts["profile"] += 1
    return counts


def run(args: Namespace, raw_data_path: Path) -> None:
    """
    Run the importer for the parsed command-line arguments.

    :param args: Parsed arguments (``source``, ``map``, ``machine``).
    :param raw_data_path: Target raw data directory from the settings.
    """
    mapping = load_mapping(args.map)
    counts = import_uap(args.source, raw_data_path, mapping, args.machine)
    print(
        "Imported "
        + ", ".join(f"{count} {role} run(s)" for role, count in counts.items())
        + f" into {raw_data_path}"
    )
