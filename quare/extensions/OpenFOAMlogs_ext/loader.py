"""
Loader for the OpenFOAM logs extension.

Parses ``<run>.checkMesh.log`` and ``<run>.<solver>.log`` files and stores the
values below as metrics with processing unit ``"run"``:

* from ``checkMesh``: ``cells`` and ``ranks``; from ``renumberMesh`` (UAP
  runs have no ``checkMesh`` log): ``cells`` from ``Mesh region0 size:``
* from a solver log (``simpleFoam`` or ``pimpleFoam``): ``<solver> time
  steps`` (number of ``ExecutionTime`` entries), ``<solver> first step time``
  and ``<solver> last step time`` (first and last cumulative ``ExecutionTime``,
  in seconds) and ``<solver> total time`` (the first ``Total Time: <s>`` or
  ``Total time = <s>`` line, if any).

A log with the built-in OpenFOAM MPI profiling (UAP MilanX ``PROF`` runs) also
yields per-step series with the processing unit ``"step"`` (index = step):
``<solver> execution time`` (cumulative ``ExecutionTime``) and the average
MPI times ``<solver> mpi reduce``, ``<solver> mpi all-all`` and
``<solver> mpi other`` in seconds.

The time stepping window used by the analysis scripts is
``last step time - first step time``.

Authors: Marcin Lawenda, Łukasz Szustak

Module-level attribute
----------------------
``ExtensionDataLoaderImpl``
    The :class:`~quare.extension_abcs.ExtensionDataLoader` implementation.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

from ...data_loader import DataLoader, MetricContext
from ...extension_abcs import ExtensionDataLoader
from ...models import MetricsBase
from ...utils import get_db_session
from .models import OpenFOAMlogs_metrics, OpenFOAMlogs_metrics_dict

SOLVERS: tuple[str, ...] = ("simpleFoam", "pimpleFoam")
"""Solvers whose logs are recognised, as part of the file name."""

PROCESSING_UNIT = "run"
"""Processing unit stored for all metrics of this extension."""

_CELLS = re.compile(r"^\s*cells:\s+(\d+)")
_REGION_SIZE = re.compile(r"^\s*Mesh region0 size:\s*(\d+)")
_RANKS = re.compile(r"^nProcs\s*:\s*(\d+)")
_EXECUTION_TIME = re.compile(r"^ExecutionTime = ([0-9.eE+-]+) s")
_PROFILE = re.compile(r"^\s*(reduce|all-all|other)\s*: avg = ([0-9.eE+-]+)s")
_TOTAL_TIME = re.compile(r"^Total [Tt]ime(?::|\s*=)\s*([0-9.eE+-]+)")


def parse_check_mesh(path: Path) -> dict[str, float]:
    """
    Read the mesh size and the number of MPI ranks from a ``checkMesh`` log.

    When a value occurs several times, the last occurrence is used.

    :param path: Path to the log file.
    :type path: pathlib.Path
    :returns: Mapping with the keys ``cells`` and ``ranks`` (only those found).
    :rtype: dict[str, float]
    """
    values: dict[str, float] = {}
    with path.open(errors="replace") as log:
        for line in log:
            if match := (_CELLS.match(line) or _REGION_SIZE.match(line)):
                values["cells"] = float(match.group(1))
            elif match := _RANKS.match(line):
                values["ranks"] = float(match.group(1))
    return values


def parse_solver_log(path: Path) -> dict[str, float]:
    """
    Read the time stepping data from a solver log.

    :param path: Path to the log file.
    :type path: pathlib.Path
    :returns: Mapping with ``time steps``, ``first step time``,
        ``last step time`` and, if present, ``total time``.  Empty when the
        log has no ``ExecutionTime`` lines.
    :rtype: dict[str, float]
    """
    times: list[float] = []
    total: float | None = None
    with path.open(errors="replace") as log:
        for line in log:
            if match := _EXECUTION_TIME.match(line):
                times.append(float(match.group(1)))
            elif total is None and (match := _TOTAL_TIME.match(line)):
                total = float(match.group(1))
    if not times:
        return {}
    values = {
        "time steps": float(len(times)),
        "first step time": times[0],
        "last step time": times[-1],
    }
    if total is not None:
        values["total time"] = total
    return values


def parse_mpi_profile(path: Path) -> dict[str, list[float]]:
    """
    Read the per-step series of a log with the built-in MPI profiling.

    :param path: Path to the solver log.
    :returns: ``{"execution time", "mpi reduce", "mpi all-all", "mpi other"}``
        with one value per occurrence in the log; empty when the log has no
        profiling lines.
    """
    series: dict[str, list[float]] = {
        "execution time": [],
        "mpi reduce": [],
        "mpi all-all": [],
        "mpi other": [],
    }
    with path.open(errors="replace") as log:
        for line in log:
            if match := _EXECUTION_TIME.match(line):
                series["execution time"].append(float(match.group(1)))
            elif match := _PROFILE.match(line):
                series[f"mpi {match.group(1)}"].append(float(match.group(2)))
    if not any(series[name] for name in series if name != "execution time"):
        return {}
    return series


def _series(
    data_loader: DataLoader,
    context: MetricContext,
    series: dict[str, list[float]],
    prefix: str,
) -> list[MetricsBase]:
    """Metric instances of per-step series (processing unit ``"step"``)."""
    return [
        data_loader.create_metric_instance(
            context, prefix + name, value, "s", index, "step"
        )
        for name, values in series.items()
        for index, value in enumerate(values)
    ]


def _metrics(
    data_loader: DataLoader,
    context: MetricContext,
    values: dict[str, float],
    prefix: str = "",
) -> list[MetricsBase]:
    """
    Turn parsed values into unsaved metric instances.

    :param data_loader: The data loader that resolves metric dictionary IDs.
    :type data_loader: quare.data_loader.DataLoader
    :param context: Repetition and file being loaded.
    :type context: quare.data_loader.MetricContext
    :param values: Parsed values, keyed by metric name without prefix.
    :type values: dict[str, float]
    :param prefix: Text put before each metric name, e.g. ``"simpleFoam "``.
    :type prefix: str
    :rtype: list[quare.models.MetricsBase]
    """
    seconds = ("first step time", "last step time", "total time")
    return [
        data_loader.create_metric_instance(
            context,
            prefix + name,
            value,
            "s" if name in seconds else "",
            None,
            PROCESSING_UNIT,
        )
        for name, value in values.items()
    ]


class Loaders:
    """Loader functions passed to :meth:`DataLoader.walk_through_data`."""

    @staticmethod
    def load_mesh(data_loader: DataLoader, context: MetricContext) -> list[MetricsBase]:
        """
        Load ``cells`` and ``ranks`` from a ``checkMesh`` log.

        :param data_loader: The data loader.
        :type data_loader: quare.data_loader.DataLoader
        :param context: Repetition and log file to read.
        :type context: quare.data_loader.MetricContext
        :returns: Unsaved metric instances; empty if the file does not exist.
        :rtype: list[quare.models.MetricsBase]
        """
        if not context.file_path.exists():
            return []
        return _metrics(data_loader, context, parse_check_mesh(context.file_path))

    @staticmethod
    def load_solver(
        solver: str,
    ) -> Callable[[DataLoader, MetricContext], list[MetricsBase]]:
        """
        Create the loader function for the log of one solver.

        :param solver: Solver name as used in the file name, e.g.
            ``"simpleFoam"``.
        :type solver: str
        :returns: A loader function for :meth:`DataLoader.walk_through_data`.
        :rtype: collections.abc.Callable
        """

        def load(data_loader: DataLoader, context: MetricContext) -> list[MetricsBase]:
            if not context.file_path.exists():
                return []
            prefix = f"{solver} "
            return _metrics(
                data_loader, context, parse_solver_log(context.file_path), prefix
            ) + _series(
                data_loader, context, parse_mpi_profile(context.file_path), prefix
            )

        return load


class ExtensionDataLoaderImpl(ExtensionDataLoader):
    """Loads the OpenFOAM log data of all preprocessed repetitions."""

    @staticmethod
    def load(data_dir_path: Path) -> None:
        """
        Load all ``OpenFOAMlogs`` directories below *data_dir_path*.

        :param data_dir_path: Root of the preprocessed-data tree.
        :type data_dir_path: pathlib.Path
        """
        file_suffixes: list[tuple[str, Callable[[DataLoader, MetricContext], list]]] = [
            ("checkMesh.log", Loaders.load_mesh)
        ] + [(f"{solver}.log", Loaders.load_solver(solver)) for solver in SOLVERS]
        data_loader = DataLoader(
            get_db_session(),
            data_dir_path,
            OpenFOAMlogs_metrics,
            OpenFOAMlogs_metrics_dict,
        )
        data_loader.walk_through_data("OpenFOAMlogs", file_suffixes)
        # runs without a checkMesh log (UAP) are found through renumberMesh
        file_suffixes[0] = ("renumberMesh.log", Loaders.load_mesh)
        data_loader.walk_through_data("OpenFOAMlogs", file_suffixes)
