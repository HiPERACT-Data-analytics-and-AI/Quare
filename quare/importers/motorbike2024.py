"""
Importer for the 2024 single-node OpenFOAM motorBike measurements.

The source tree has one directory per platform and measurement campaign
("variant"), and one directory per mesh size below it::

    <source>/<platform dir>/<variant>/<size>/0/<files>

Three kinds of variants are recognised, each becoming a *tag* on the imported
runs (the tag is appended to the date directory, ``<date>_<tag>``):

``counters``
    Timing and AMD uProf PCM counters.  Every ``log.simpleFoam*`` file is one
    timing run.  The counter file ``prof.AMD.ALL_<size>1.csv`` belongs to the
    run ``log.simpleFoam.uProfALL1``; the second counter file is not imported,
    as in the original analysis scripts.
``trace``
    AMD uProf MPI trace: ``log.simpleFoam.MPItrace0`` and the
    ``mpi-summary.csv`` of ``mpi.trace0``.
``topdown``
    Top-down counters (``prof.AMD.ALL_<size>_ipc_2.csv``); the solver logs of
    this variant are not used.

The result is written in the raw layout::

    <raw>/<session>/<machine>/<use_case>/<size>/<date>_<tag>/
        OpenFOAMlogs/<run>.checkMesh.log, <run>.<solver>.log
        AMDuProfPCM/<counter file>
        AMDuProfMPI/mpi-summary.csv

The run date comes from the date and time in the OpenFOAM log banner (or the
profile time of a counter file).  If two runs of the same kind get the same
second, the later one is moved forward by whole seconds so that every run
directory is unique.

Authors: Marcin Lawenda, Łukasz Szustak
"""

from __future__ import annotations

import json
import re
import shutil
from argparse import Namespace
from datetime import datetime, timedelta
from pathlib import Path

COUNTERS = "counters"
TRACE = "trace"
TOPDOWN = "topdown"
ROLES: tuple[str, ...] = (COUNTERS, TRACE, TOPDOWN)

SOLVER_LOG = re.compile(r"^log\.(?P<solver>simpleFoam|pimpleFoam)(?P<run>.*)$")
PCM_COUNTER_RUN = "uProfALL1"
PCM_COUNTER_FILE = "prof.AMD.ALL_{size}1.csv"
PCM_TOPDOWN_FILE = "prof.AMD.ALL_{size}_ipc_2.csv"
MPI_TRACE_LOG = "log.simpleFoam.MPItrace0"
MPI_SUMMARY = Path("mpi.trace0/AMDuProf-simpleFoam-HPC_MPI/mpi/lwt/mpi-summary.csv")

_LOG_DATE = re.compile(r"^Date\s*:\s*(\w+ \d+ \d{4})")
_LOG_TIME = re.compile(r"^Time\s*:\s*(\d+:\d+:\d+)")
_PROFILE_TIME = re.compile(r"^Profile Time:\s*(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})")


def load_mapping(path: Path) -> dict:
    """
    Read and validate an import mapping file.

    The file is JSON with the keys ``session``, ``use_case``, ``sizes`` (list)
    and ``machines``.  ``machines`` maps the machine name used in Quare
    (a trailing ``_<cores>`` gives the core count) to an object with the key
    ``source`` (platform directory) and any of the roles ``counters``,
    ``trace`` and ``topdown`` naming the variant directory.  The optional
    ``trace_logs`` maps a size name to the solver log of the traced run when it
    is not ``log.simpleFoam.MPItrace0``.

    :param path: Path to the JSON file.
    :type path: pathlib.Path
    :returns: The parsed mapping.
    :rtype: dict
    :raises ValueError: If a required key is missing or a machine has no
        ``source``.
    """
    mapping = json.loads(path.read_text())
    for key in ("session", "use_case", "sizes", "machines"):
        if key not in mapping:
            raise ValueError(f"{path}: missing key '{key}'")
    for name, machine in mapping["machines"].items():
        if "source" not in machine:
            raise ValueError(f"{path}: machine '{name}' has no 'source'")
    return mapping


def _size_dir(variant_dir: Path, size: str) -> Path | None:
    """
    Return the directory that holds the files of *size* in a variant.

    :param variant_dir: Variant directory.
    :type variant_dir: pathlib.Path
    :param size: Mesh size name, e.g. ``"xsmall"``.
    :type size: str
    :returns: ``<variant>/<size>/0`` if it exists, else ``<variant>/<size>``,
        or ``None`` if neither exists.
    :rtype: pathlib.Path or None
    """
    for candidate in (variant_dir / size / "0", variant_dir / size):
        if candidate.is_dir():
            return candidate
    return None


def log_start_time(log_path: Path) -> datetime | None:
    """
    Read the start date and time from the banner of an OpenFOAM log.

    :param log_path: Path to the log file.
    :type log_path: pathlib.Path
    :returns: The start time, or ``None`` if the banner has no date and time.
    :rtype: datetime.datetime or None
    """
    date_text = time_text = None
    with log_path.open(errors="replace") as log:
        for line_number, line in enumerate(log):
            if line_number > 500:
                break
            if date_text is None and (match := _LOG_DATE.match(line)):
                date_text = match.group(1)
            elif time_text is None and (match := _LOG_TIME.match(line)):
                time_text = match.group(1)
            if date_text and time_text:
                return datetime.strptime(
                    f"{date_text} {time_text}", "%b %d %Y %H:%M:%S"
                )
    return None


def profile_time(counter_path: Path) -> datetime | None:
    """
    Read the ``Profile Time`` of an AMD uProf PCM counter file.

    :param counter_path: Path to the counter CSV.
    :type counter_path: pathlib.Path
    :returns: The profile time, or ``None`` if the file has none.
    :rtype: datetime.datetime or None
    """
    with counter_path.open(errors="replace") as report:
        for line in report:
            if match := _PROFILE_TIME.match(line):
                return datetime.strptime(match.group(1), "%Y/%m/%d %H:%M:%S")
    return None


class _RunWriter:
    """Creates run directories below one ``<session>/<machine>/<use_case>/<size>``."""

    def __init__(self, size_path: Path) -> None:
        self._size_path = size_path
        self._used: set[str] = set()

    def run_dir(self, start: datetime | None, tag: str, fallback: datetime) -> Path:
        """
        Return a new, unique run directory ``<date>_<tag>``.

        :param start: Start time of the run, or ``None``.
        :type start: datetime.datetime or None
        :param tag: Role tag appended to the date.
        :type tag: str
        :param fallback: Time to use when *start* is ``None``.
        :type fallback: datetime.datetime
        :rtype: pathlib.Path
        """
        moment = start or fallback
        name = f"{moment:%Y%m%d_%H%M%S}_{tag}"
        while name in self._used:
            moment += timedelta(seconds=1)
            name = f"{moment:%Y%m%d_%H%M%S}_{tag}"
        self._used.add(name)
        return self._size_path / name


def _copy(source: Path, destination: Path) -> None:
    """
    Copy a file, creating the destination directory.

    :param source: File to copy.
    :type source: pathlib.Path
    :param destination: Target file path.
    :type destination: pathlib.Path
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def _import_counters(size_dir: Path, size: str, writer: _RunWriter) -> int:
    """
    Import the timing runs and the counter file of the ``counters`` variant.

    :param size_dir: Directory with the files of one size.
    :type size_dir: pathlib.Path
    :param size: Mesh size name.
    :type size: str
    :param writer: Run directory allocator.
    :type writer: _RunWriter
    :returns: Number of runs imported.
    :rtype: int
    """
    mesh_log = size_dir / "log.checkMesh"
    imported = 0
    for log_path in sorted(size_dir.glob("log.simpleFoam*")):
        match = SOLVER_LOG.match(log_path.name)
        if match is None:
            continue
        solver = match.group("solver")
        run_name = match.group("run").lstrip("._") or "run"
        run_dir = writer.run_dir(
            log_start_time(log_path), COUNTERS, datetime(2024, 1, 1)
        )
        logs_dir = run_dir / "OpenFOAMlogs"
        _copy(mesh_log, logs_dir / f"{run_name}.checkMesh.log")
        _copy(log_path, logs_dir / f"{run_name}.{solver}.log")
        if run_name == PCM_COUNTER_RUN:
            counter_file = size_dir / PCM_COUNTER_FILE.format(size=size)
            _copy(counter_file, run_dir / "AMDuProfPCM" / counter_file.name)
        imported += 1
    return imported


def _import_trace(
    size_dir: Path, writer: _RunWriter, log_name: str = MPI_TRACE_LOG
) -> int:
    """
    Import the MPI trace run of the ``trace`` variant.

    :param size_dir: Directory with the files of one size.
    :type size_dir: pathlib.Path
    :param writer: Run directory allocator.
    :type writer: _RunWriter
    :param log_name: Solver log of the traced run.  It is
        ``log.simpleFoam.MPItrace0`` unless the mapping names another one
        (``trace_logs``), for example when ``mpi.trace0`` holds the trace of a
        later run.
    :type log_name: str
    :returns: ``1`` if the run was imported, else ``0``.
    :rtype: int
    """
    log_path = size_dir / log_name
    summary = size_dir / MPI_SUMMARY
    if not log_path.exists() or not summary.exists():
        return 0
    run_dir = writer.run_dir(log_start_time(log_path), TRACE, datetime(2024, 1, 1))
    _copy(size_dir / "log.checkMesh", run_dir / "OpenFOAMlogs" / "run.checkMesh.log")
    _copy(log_path, run_dir / "OpenFOAMlogs" / "run.simpleFoam.log")
    _copy(summary, run_dir / "AMDuProfMPI" / "mpi-summary.csv")
    return 1


def _import_topdown(size_dir: Path, size: str, writer: _RunWriter) -> int:
    """
    Import the top-down counter file of the ``topdown`` variant.

    :param size_dir: Directory with the files of one size.
    :type size_dir: pathlib.Path
    :param size: Mesh size name.
    :type size: str
    :param writer: Run directory allocator.
    :type writer: _RunWriter
    :returns: ``1`` if the file was imported, else ``0``.
    :rtype: int
    """
    counter_file = size_dir / PCM_TOPDOWN_FILE.format(size=size)
    if not counter_file.exists():
        return 0
    run_dir = writer.run_dir(profile_time(counter_file), TOPDOWN, datetime(2024, 1, 1))
    _copy(counter_file, run_dir / "AMDuProfPCM" / counter_file.name)
    return 1


def import_motorbike_2024(
    source: Path,
    raw_data_path: Path,
    mapping: dict,
    machines: list[str] | None = None,
) -> dict[str, int]:
    """
    Convert the 2024 motorBike tree below *source* into the raw data layout.

    :param source: Root directory that contains the platform directories.
    :type source: pathlib.Path
    :param raw_data_path: Target root of the raw data tree (created if needed).
    :type raw_data_path: pathlib.Path
    :param mapping: Mapping read by :func:`load_mapping`.
    :type mapping: dict
    :param machines: Names of the machines to import; all machines of the
        mapping when ``None``.
    :type machines: list[str] or None
    :returns: Number of runs imported per role (``counters``, ``trace``,
        ``topdown``).
    :rtype: dict[str, int]
    :raises ValueError: If a requested machine is not in the mapping.
    """
    selected = machines or list(mapping["machines"])
    unknown = [name for name in selected if name not in mapping["machines"]]
    if unknown:
        raise ValueError(f"not in the mapping: {', '.join(unknown)}")

    counts = dict.fromkeys(ROLES, 0)
    for machine_name in selected:
        machine = mapping["machines"][machine_name]
        for size in mapping["sizes"]:
            size_path = (
                raw_data_path
                / mapping["session"]
                / machine_name
                / mapping["use_case"]
                / size
            )
            writer = _RunWriter(size_path)
            for role in ROLES:
                if role not in machine:
                    continue
                size_dir = _size_dir(source / machine["source"] / machine[role], size)
                if size_dir is None:
                    continue
                if role == COUNTERS:
                    counts[role] += _import_counters(size_dir, size, writer)
                elif role == TRACE:
                    counts[role] += _import_trace(
                        size_dir,
                        writer,
                        machine.get("trace_logs", {}).get(size, MPI_TRACE_LOG),
                    )
                else:
                    counts[role] += _import_topdown(size_dir, size, writer)
    return counts


def run(args: Namespace, raw_data_path: Path) -> None:
    """
    Run the importer for the parsed command-line arguments.

    :param args: Parsed arguments (``source``, ``map``, ``machine``).
    :type args: argparse.Namespace
    :param raw_data_path: Target raw data directory from the settings.
    :type raw_data_path: pathlib.Path
    """
    mapping = load_mapping(args.map)
    counts = import_motorbike_2024(args.source, raw_data_path, mapping, args.machine)
    print(
        "Imported "
        + ", ".join(f"{count} {role} run(s)" for role, count in counts.items())
        + f" into {raw_data_path}"
    )
