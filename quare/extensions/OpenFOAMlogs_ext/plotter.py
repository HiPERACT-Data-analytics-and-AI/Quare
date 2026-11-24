"""
Analyses of OpenFOAM benchmark runs (FVOPS and related ratios).

:class:`OpenFOAMAnalyzer` combines the run-level values taken from the
OpenFOAM logs with the counters of the AMD uProf extensions.  The measurement
campaigns of one task size are told apart by the tag that follows the time
stamp of the repetition directory (see :mod:`quare.importers.motorbike2024`):

``counters``
    The timing runs.  Their solver logs give FVOPS; the run that has an AMD
    uProf PCM file gives the cache ratios.
``trace``
    The run with the MPI trace: the MPI times of all ranks and the run time of
    the traced run.
``topdown``
    The run with the Zen 4 top-down counters.

``likwid``, ``likwid-pimpleFoam``
    The run with the LIKWID statistics of the L2, L3 and NUMA groups, for
    simpleFoam and (UAP) pimpleFoam.

``power``
    The run with the AMD uProf power timecharts (2026 data): the node power
    traces and the log of the run, which gives the time stepping window.

A tag may carry a label (``counters-1n2r``).  The settings
``fvops_time_run`` and ``fvops_steps_run`` select the labelled timing run whose
window, and the one whose step count, FVOPS uses; the UAP scripts take the time
of run ``1n2r`` and the steps of run ``1n4r``.  Without them FVOPS uses the
median of all timing runs.

Repetition names without a tag are treated as timing and counter runs.  In the
2026 data the PCM file belongs to the ``topdown`` run, so the cache ratios look
in the timing runs first and then in the top-down run.

Registered analyses
-------------------
=============================== =========================================
Name                            Definition
=============================== =========================================
FVOPS                           cells / (median window time / (steps-1))
L3 miss ratio                   mean over CCXs of ``L3 Miss %``
L2 ... ratio (six)              ratio of the means over cores of the pti
                                counters, in percent
Backend Bound Memory,           system aggregate of the top-down value
                                (mean over cores if the file has none)
Frontend Bound, Retiring
MPI ratio (min/avg/max)         per-rank MPI time / last cumulative
                                ``ExecutionTime`` of the traced run
MPI ratio (mid-range)           (min + max) / 2 of the rank times over the
                                same run time: what the UAP scripts plot
                                as the "avg" ratio
CVOPTS                          cells per rank (rounded to 2 decimals) /
                                average step time of the lower median run
Aggregate / average node power  mean of the last ``int(window/0.1) - 1``
                                samples of each node trace [W]
Aggregate energy                sum over nodes of power * window [kWh]
MPI volume (aggregate/per rank) sum / mean of the per-rank volumes [GB]
Clock frequency (min/max/avg)   mean over the LIKWID groups of the min / max
                                / avg over threads of ``Clock [MHz]``,
                                rounded to 2 decimals
L2/L3 data volume, L2/L3        ``sum`` over all threads or ``avg`` per thread
bandwidth, Memory data volume,  of the LIKWID metric (memory = NUMA group
Memory bandwidth (sum/avg)      total)
pimpleFoam <name of the         the same from the ``likwid-pimpleFoam`` run
Clock / LIKWID analyses>        (UAP)
=============================== =========================================

Two settings replace behaviour of the original scripts that looks like a
flaw; the defaults reproduce the scripts:

``median_of_even_runs`` (``lower``/``average``)
    The median of an even number of runs is the lower middle value in the
    scripts; ``average`` takes the mean of the two (FVOPS and the timing
    outputs; the run chosen for ``CVOPTS`` stays the lower median).
``mpi_ratio_basis`` (``last_step``/``total_time``)
    The MPI ratios divide by the last ``ExecutionTime`` of the traced run.
    The MPI times of the profiler cover the whole run, so the ratio can pass
    100% (the UAP maximum does); ``total_time`` divides by the ``Total Time``
    line of the log instead.

``FVOPS`` follows the original analysis script: the window of a run is the
last minus the first ``ExecutionTime`` of its time stepping, the value of a
task size is the median of the windows of its timing runs (the lower median
when their number is even), and the solver is ``simpleFoam``.

Authors: Marcin Lawenda, Łukasz Szustak
"""

from __future__ import annotations

import statistics
from collections.abc import Callable
from functools import partial
from pathlib import Path
from typing import Any

from matplotlib import pyplot as plt
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...data_retriever import (
    DataRetriever,
    DataRetrieversManager,
    MetricValue,
    RepetitionIDs,
    UniqueMetricKey,
)
from ...models import MetricsBase, MetricsDictBase, Repetition
from ...plotter import Plotter
from ...utils import load_settings
from ..AMDuProfMPI_ext.models import AMDuProfMPI_metrics, AMDuProfMPI_metrics_dict
from ..AMDuProfPCM_ext.models import AMDuProfPCM_metrics, AMDuProfPCM_metrics_dict
from ..AMDuProfTimechart_ext.models import (
    AMDuProfTimechart_metrics,
    AMDuProfTimechart_metrics_dict,
)
from ..LIKWID_ext.models import LIKWID_metrics, LIKWID_metrics_dict
from .comparison import RunTimes, make_timing_plot, median_run, write_speedup
from .figures import (
    LIKWID_ROWS,
    make_clock_plot,
    make_likwid_plot,
    make_pti_plot,
    make_solver_timing_plot,
    pti_series,
)
from .models import OpenFOAMlogs_metrics, OpenFOAMlogs_metrics_dict

SOLVER = "simpleFoam"
TAG_TIMING = "counters"
TAG_TRACE = "trace"
TAG_TOPDOWN = "topdown"
TAG_POWER = "power"
TAG_LIKWID = "likwid"
_ALL_TAGS = (TAG_TIMING, TAG_TRACE, TAG_TOPDOWN, TAG_POWER, TAG_LIKWID)
POWER_SAMPLE_INTERVAL = 0.1
"""Sampling interval of the uProf timechart in seconds."""

# L2 analyses: name -> (numerator counter, denominator counter)
_L2_RATIOS: dict[str, tuple[str, str]] = {
    "L2 miss ratio (total)": ("L2 Miss (pti)", "L2 Access (pti)"),
    "L2 miss ratio from L1DC": (
        "L2 Miss from DC Miss (pti)",
        "L2 Access from DC Miss (pti)",
    ),
    "L2 miss ratio from HWPF": (
        "L2 Miss from HWPF (pti)",
        "L2 Access from HWPF (pti)",
    ),
    "L2 hit ratio (total)": ("L2 Hit (pti)", "L2 Access (pti)"),
    "L2 hit ratio from L1DC": (
        "L2 Hit from DC Miss (pti)",
        "L2 Access from DC Miss (pti)",
    ),
    "L2 hit ratio from HWPF": (
        "L2 Hit from HWPF (pti)",
        "L2 Access from HWPF (pti)",
    ),
}
# LIKWID analyses: name -> (group, LIKWID metric names tried in turn, unit)
_LIKWID_METRICS: dict[str, tuple[str, list[str], str]] = {
    "L2 data volume": ("L2", ["L2 data volume [GBytes]"], "GBytes"),
    "L2 bandwidth": ("L2", ["L2 bandwidth [MBytes/s]"], "MBytes/s"),
    "L3 data volume": (
        "L3",
        ["L3 data volume [GBytes]", "L3 access data volume [GBytes]"],
        "GBytes",
    ),
    "L3 bandwidth": (
        "L3",
        ["L3 bandwidth [MBytes/s]", "L3 access bandwidth [MBytes/s]"],
        "MBytes/s",
    ),
    "Memory data volume": ("NUMA", ["Total data volume [GBytes]"], "GBytes"),
    "Memory bandwidth": ("NUMA", ["Total bandwidth [MBytes/s]"], "MBytes/s"),
}
_LIKWID_GROUPS = ("L2", "L3", "NUMA")
DEFAULT_SERIES = (
    "L2 miss ratio (total)",
    "L2 miss ratio from L1DC",
    "L2 miss ratio from HWPF",
    "L3 miss ratio",
    "MPI ratio (avg)",
    "Backend Bound Memory",
    "Frontend Bound",
)
"""Analyses on the right axis of the comparison figure."""
_TOPDOWN = {
    "Backend Bound Memory": "Backend_Bound.Memory",
    "Frontend Bound": "Frontend_Bound",
    "Retiring": "Retiring",
}


class OpenFOAMAnalyzer(DataRetriever):
    """Data retriever with the OpenFOAM benchmark analyses (see module doc)."""

    def __init__(
        self,
        db_session: Session,
        metrics_table: type[MetricsBase],
        metrics_dict_table: type[MetricsDictBase],
    ) -> None:
        """Register the analyses; arguments as in :class:`DataRetriever`."""
        super().__init__(db_session, metrics_table, metrics_dict_table)
        analytics: dict[UniqueMetricKey, Callable[[RepetitionIDs], list[MetricValue]]]
        analytics = {
            UniqueMetricKey("FVOPS", "cells/s", "run"): self._calc_fvops,
            UniqueMetricKey("L3 miss ratio", "%", "ccx"): self._calc_l3,
            UniqueMetricKey("Time stepping time", "s", "run"): self._timing("steps"),
            UniqueMetricKey("Total time", "s", "run"): self._timing("total"),
            UniqueMetricKey("CVOPTS", "cells/rank/s", "run"): self._calc_cvopts,
            UniqueMetricKey("Aggregate node power", "W", "node"): self._power("sum"),
            UniqueMetricKey("Average node power", "W", "node"): self._power("mean"),
            UniqueMetricKey("Aggregate energy", "kWh", "node"): self._power("energy"),
            UniqueMetricKey("MPI volume (aggregate)", "GB", "rank"): self._volume(
                False
            ),
            UniqueMetricKey("MPI volume (per rank)", "GB", "rank"): self._volume(True),
            UniqueMetricKey("MPI ratio (min)", "%", "rank"): self._mpi_ratio(min),
            UniqueMetricKey("MPI ratio (avg)", "%", "rank"): self._mpi_ratio(
                statistics.fmean
            ),
            UniqueMetricKey("MPI ratio (max)", "%", "rank"): self._mpi_ratio(max),
            UniqueMetricKey("MPI ratio (mid-range)", "%", "rank"): self._mpi_ratio(
                lambda times: (min(times) + max(times)) / 2.0
            ),
        }
        for solver, prefix in (("simpleFoam", ""), ("pimpleFoam", "pimpleFoam ")):
            for statistic in ("min", "max", "avg"):
                analytics[
                    UniqueMetricKey(
                        f"{prefix}Clock frequency ({statistic})", "MHz", "thread"
                    )
                ] = self._clock(statistic, solver)
            for name, (group, metrics, unit) in _LIKWID_METRICS.items():
                for statistic in ("sum", "avg"):
                    analytics[
                        UniqueMetricKey(f"{prefix}{name} ({statistic})", unit, "thread")
                    ] = self._likwid(group, metrics, statistic, solver)
        for name in _L2_RATIOS:
            analytics[UniqueMetricKey(name, "%", "core")] = self._l2_ratio(name)
        for name, counter in _TOPDOWN.items():
            analytics[UniqueMetricKey(name, "%", "core")] = self._topdown(counter)
        self.AVAILABLE_ANALYTICS |= analytics

    # -- helpers -----------------------------------------------------------

    def _with_tag(
        self, repetition_ids: list[int], tag: str, label: str | None = None
    ) -> list[int]:
        """Return the repetitions of *repetition_ids* that carry *tag*.

        The tag is the text after the time stamp of the run directory; it is
        ``<role>`` or ``<role>-<label>`` (``counters-1n2r``).  Repetitions
        without a known role count as timing (``counters``) runs.  With
        *label*, only the runs with that label are returned.
        """
        if not repetition_ids:
            return []
        rows = self._db_session.execute(
            select(Repetition.id, Repetition.name)
            .where(Repetition.id.in_(repetition_ids))
            .order_by(Repetition.name)
        ).all()
        selected = []
        for row in rows:
            run = row.name.rpartition(".")[0]  # drop the session suffix
            text = run.split("_", 2)[2] if run.count("_") >= 2 else ""
            role, _, run_label = text.partition("-")
            if (role if role in _ALL_TAGS else TAG_TIMING) != tag:
                continue
            if label is None or run_label == label:
                selected.append(row.id)
        return selected

    def _values(
        self,
        metrics: type[MetricsBase],
        metrics_dict: type[MetricsDictBase],
        repetition: int,
        name: str,
    ) -> list[float]:
        """All values of metric *name* of one repetition, by processing unit."""
        stmt = (
            select(metrics.value)
            .join(metrics_dict, metrics_dict.id == metrics.metric)  # type: ignore
            .where(metrics.repetition == repetition, metrics_dict.name == name)
            .order_by(metrics.processing_unit_idx)
        )
        return [row[0] for row in self._db_session.execute(stmt)]

    def _pcm_means(
        self, repetitions: list[int], names: list[str]
    ) -> dict[str, float] | None:
        """
        PCM values of *names* in the first repetition that has all of them.

        The value of a counter is the system aggregate when the file has one
        (newer uProf files), else the mean over the cores or CCXs, as in the
        original scripts.
        """
        for repetition in repetitions:
            found: dict[str, float] = {}
            for name in names:
                rows = self._db_session.execute(
                    select(
                        AMDuProfPCM_metrics.value,
                        AMDuProfPCM_metrics_dict.processing_unit,
                    )
                    .join(
                        AMDuProfPCM_metrics_dict,
                        AMDuProfPCM_metrics_dict.id == AMDuProfPCM_metrics.metric,
                    )
                    .where(
                        AMDuProfPCM_metrics.repetition == repetition,
                        AMDuProfPCM_metrics_dict.name == name,
                    )
                    .order_by(AMDuProfPCM_metrics.processing_unit_idx)
                ).all()
                if not rows:
                    break
                system = [r[0] for r in rows if r[1] == "system"]
                found[name] = (
                    system[0] if system else statistics.fmean(r[0] for r in rows)
                )
            if len(found) == len(names):
                return found
        return None

    def _per_size(
        self, repetition_ids: RepetitionIDs, func: Callable[[list[int]], MetricValue]
    ) -> list[MetricValue]:
        return [func(ids) for ids in repetition_ids.values()]

    # -- analyses ----------------------------------------------------------

    def _calc_fvops(self, repetition_ids: RepetitionIDs) -> list[MetricValue]:
        def fvops(ids: list[int]) -> MetricValue:
            windows: list[float] = []
            steps = cells = 0.0
            settings = load_settings()
            time_run = settings.get("fvops_time_run")
            steps_run = settings.get("fvops_steps_run")
            for run in self._with_tag(ids, TAG_TIMING, time_run):
                get = partial(
                    self._values, OpenFOAMlogs_metrics, OpenFOAMlogs_metrics_dict, run
                )
                first, last = get(f"{SOLVER} first step time"), get(
                    f"{SOLVER} last step time"
                )
                n_steps, n_cells = get(f"{SOLVER} time steps"), get("cells")
                if not (first and last and n_steps and n_cells):
                    continue
                windows.append(last[0] - first[0])
                steps, cells = n_steps[0] - 1, n_cells[0]
            if steps_run:
                for run in self._with_tag(ids, TAG_TIMING, steps_run):
                    counted = self._values(
                        OpenFOAMlogs_metrics,
                        OpenFOAMlogs_metrics_dict,
                        run,
                        f"{SOLVER} time steps",
                    )
                    if counted:
                        steps = counted[0] - 1
            if not windows or steps <= 0:
                return None
            median = median_run(windows, self._median_mode())
            return cells / (median / steps) if median else None

        return self._per_size(repetition_ids, fvops)

    @staticmethod
    def _mpi_basis() -> str:
        """Metric of the run time of the MPI ratios (setting ``mpi_ratio_basis``)."""
        basis = load_settings().get("mpi_ratio_basis", "last_step")
        if basis not in ("last_step", "total_time"):
            raise ValueError("mpi_ratio_basis must be 'last_step' or 'total_time'")
        return "total time" if basis == "total_time" else "last step time"

    @staticmethod
    def _median_mode() -> str:
        """Setting ``median_of_even_runs``: ``lower`` (scripts) or ``average``."""
        return load_settings().get("median_of_even_runs", "lower")

    def run_times(self, ids: list[int]) -> RunTimes:
        """
        Times of all timing runs of one task size (see :data:`RunTimes`).

        A run counts with its time-stepping window; the lists derived from the
        ``Total Time`` line only have the runs that have one. The lists are sorted
        independently of each other, as in the original script.
        """
        steps, total, all_steps, pct, delay = [], [], [], [], []
        for run in self._with_tag(ids, TAG_TIMING):
            get = partial(
                self._values, OpenFOAMlogs_metrics, OpenFOAMlogs_metrics_dict, run
            )
            first = get(f"{SOLVER} first step time")
            last = get(f"{SOLVER} last step time")
            whole = get(f"{SOLVER} total time")
            if not (first and last):
                continue
            steps.append(last[0] - first[0])
            all_steps.append(last[0])
            if whole:  # the UAP logs have no "Total Time" line
                total.append(whole[0])
                pct.append(last[0] / whole[0] * 100.0)
                delay.append(whole[0] - last[0])
        return {
            "steps": sorted(steps),
            "total": sorted(total),
            "all_steps": sorted(all_steps),
            "pct": sorted(pct),
            "delay": sorted(delay),
        }

    def _timing(self, key: str) -> Callable[[RepetitionIDs], list[MetricValue]]:
        return lambda repetition_ids: self._per_size(
            repetition_ids,
            lambda ids: median_run(self.run_times(ids)[key], self._median_mode()),
        )

    def _counter_runs(self, ids: list[int]) -> list[int]:
        """Timing runs first, then the top-down run (it has the cache counters
        in the 2026 data, where there is no separate counter run)."""
        return self._with_tag(ids, TAG_TIMING) + self._with_tag(ids, TAG_TOPDOWN)

    def _calc_l3(self, repetition_ids: RepetitionIDs) -> list[MetricValue]:
        def l3(ids: list[int]) -> MetricValue:
            found = self._pcm_means(self._counter_runs(ids), ["L3 Miss %"])
            return found["L3 Miss %"] if found else None

        return self._per_size(repetition_ids, l3)

    def _l2_ratio(self, name: str) -> Callable[[RepetitionIDs], list[MetricValue]]:
        numerator, denominator = _L2_RATIOS[name]

        def ratio(ids: list[int]) -> MetricValue:
            found = self._pcm_means(self._counter_runs(ids), [numerator, denominator])
            if not found or not found[denominator]:
                return None
            return found[numerator] / found[denominator] * 100.0

        return lambda repetition_ids: self._per_size(repetition_ids, ratio)

    def _topdown(self, counter: str) -> Callable[[RepetitionIDs], list[MetricValue]]:
        def mean(ids: list[int]) -> MetricValue:
            found = self._pcm_means(self._with_tag(ids, TAG_TOPDOWN), [counter])
            return found[counter] if found else None

        return lambda repetition_ids: self._per_size(repetition_ids, mean)

    def solver_times(self, ids: list[int], solver: str) -> list[float]:
        """
        Sorted time-stepping windows of *solver* in all runs of one task size.

        Unlike :meth:`run_times` this takes every run that has a log of the
        solver (timing, trace and top-down runs), as ``timing_comp.py`` does
        with its five runs.
        """
        windows = []
        runs = [
            run
            for tag in (TAG_TIMING, TAG_TRACE, TAG_TOPDOWN)
            for run in self._with_tag(ids, tag)
        ]
        for run in runs:
            get = partial(
                self._values, OpenFOAMlogs_metrics, OpenFOAMlogs_metrics_dict, run
            )
            first, last = get(f"{solver} first step time"), get(
                f"{solver} last step time"
            )
            if first and last:
                windows.append(last[0] - first[0])
        return sorted(windows)

    def pti_values(self, ids: list[int]) -> dict[str, float]:
        """
        The ``(pti)`` counters of the first counter run of one task size that
        has any, as in :meth:`_pcm_means`.
        """
        for run in self._counter_runs(ids):
            names = [
                row[0]
                for row in self._db_session.execute(
                    select(AMDuProfPCM_metrics_dict.name)
                    .join(
                        AMDuProfPCM_metrics,
                        AMDuProfPCM_metrics.metric == AMDuProfPCM_metrics_dict.id,
                    )
                    .where(
                        AMDuProfPCM_metrics.repetition == run,
                        AMDuProfPCM_metrics_dict.name.like("%(pti)"),
                    )
                    .distinct()
                    .order_by(AMDuProfPCM_metrics_dict.id)
                )
            ]
            found = {}
            for name in names:
                value = self._pcm_means([run], [name])
                if value:
                    found.update(value)
            if found:
                return found
        return {}

    def timing_record(self, ids: list[int]) -> dict[str, float | None] | None:
        """
        The application features of one task size, as ``app_info.py``.

        The run is the lower median of the timing runs sorted by their last
        ``ExecutionTime`` (so all values come from one real run); the cells per
        rank are rounded to two decimals first, as in the script.  Keys:
        ``cells``, ``ranks``, ``cellsPerRank``, ``totalTime``,
        ``firstStepTime``, ``allStepsTime``, ``allStepsTime_m1``, ``lenSteps``,
        ``avgOneSetepTime`` and ``CVOPTS``.  ``None`` without timing runs.
        """
        records: list[dict[str, float | None]] = []
        for run in self._with_tag(ids, TAG_TIMING):
            get = partial(
                self._values, OpenFOAMlogs_metrics, OpenFOAMlogs_metrics_dict, run
            )
            first, last = get(f"{SOLVER} first step time"), get(
                f"{SOLVER} last step time"
            )
            n_steps, cells, ranks = (
                get(f"{SOLVER} time steps"),
                get("cells"),
                get("ranks"),
            )
            if not (first and last and n_steps and cells and ranks):
                continue
            total = get(f"{SOLVER} total time")
            per_rank = round(cells[0] / ranks[0], 2)
            average = (last[0] - first[0]) / (n_steps[0] - 1)
            records.append(
                {
                    "cells": int(cells[0]),
                    "ranks": int(ranks[0]),
                    "cellsPerRank": per_rank,
                    "totalTime": total[0] if total else None,
                    "firstStepTime": first[0],
                    "allStepsTime": last[0],
                    "allStepsTime_m1": last[0] - first[0],
                    "lenSteps": int(n_steps[0]),
                    "avgOneSetepTime": average,
                    "CVOPTS": per_rank / average,
                }
            )
        if not records:
            return None
        records.sort(key=lambda r: r["allStepsTime"] or 0.0)
        return records[(len(records) - 1) // 2]

    def _calc_cvopts(self, repetition_ids: RepetitionIDs) -> list[MetricValue]:
        """``CVOPTS`` of :meth:`timing_record` per task size."""

        def cvopts(ids: list[int]) -> MetricValue:
            record = self.timing_record(ids)
            return record["CVOPTS"] if record else None

        return self._per_size(repetition_ids, cvopts)

    def power_value(self, ids: list[int], kind: str) -> MetricValue:
        """
        Power or energy of the ``power`` run, as ``en_info.py``.

        The window is the last minus the first ``ExecutionTime`` of the power
        run log; the average power of a node is the mean of the last
        ``int(window / 0.1) - 1`` samples of its trace (100 ms sampling).
        *kind*: ``sum`` (all nodes), ``mean`` (per node) or ``energy`` (sum of
        the node energies in kWh).
        """
        for run in self._with_tag(ids, TAG_POWER):
            get = partial(
                self._values, OpenFOAMlogs_metrics, OpenFOAMlogs_metrics_dict, run
            )
            first, last = get(f"{SOLVER} first step time"), get(
                f"{SOLVER} last step time"
            )
            traces = self._node_traces(run)
            if not (first and last and traces):
                continue
            window = last[0] - first[0]
            samples = int(window / POWER_SAMPLE_INTERVAL) - 1
            averages = []
            for trace in traces:
                tail = trace[int(len(trace) - samples) :]
                averages.append(sum(tail) / len(tail))
            if kind == "sum":
                return sum(averages)
            if kind == "mean":
                return sum(averages) / len(averages)
            return sum((a / 1000.0) * (window / 3600.0) for a in averages)
        return None

    def _power(self, kind: str) -> Callable[[RepetitionIDs], list[MetricValue]]:
        """Analysis wrapper of :meth:`power_value`."""
        return lambda repetition_ids: self._per_size(
            repetition_ids, lambda ids: self.power_value(ids, kind)
        )

    def _node_traces(self, run: int) -> list[list[float]]:
        """Power samples of every node of a run, in node order."""
        names = [
            row[0]
            for row in self._db_session.execute(
                select(AMDuProfTimechart_metrics_dict.name).distinct()
            )
        ]
        traces = []
        for name in sorted(names, key=lambda n: int(n.split()[1])):
            values = self._values(
                AMDuProfTimechart_metrics, AMDuProfTimechart_metrics_dict, run, name
            )
            if values:
                traces.append(values)
        return traces

    def volume_value(self, ids: list[int], per_rank: bool) -> MetricValue:
        """MPI volume in GB (1e9 bytes) of the trace run: total or per rank."""
        for run in self._with_tag(ids, TAG_TRACE):
            values = self._values(
                AMDuProfMPI_metrics, AMDuProfMPI_metrics_dict, run, "Volume(Bytes)"
            )
            if values:
                total = sum(values) / 1000 / 1000 / 1000
                return total / len(values) if per_rank else total
        return None

    def _volume(self, per_rank: bool) -> Callable[[RepetitionIDs], list[MetricValue]]:
        """Analysis wrapper of :meth:`volume_value`."""
        return lambda repetition_ids: self._per_size(
            repetition_ids, lambda ids: self.volume_value(ids, per_rank)
        )

    def _likwid_value(self, run: int, name: str, statistic: str) -> float | None:
        """Statistic (``sum``/``min``/``max``/``avg``) of one LIKWID metric."""
        row = self._db_session.execute(
            select(LIKWID_metrics.value)
            .join(
                LIKWID_metrics_dict,
                LIKWID_metrics_dict.id == LIKWID_metrics.metric,
            )
            .where(
                LIKWID_metrics.repetition == run,
                LIKWID_metrics_dict.name == name,
                LIKWID_metrics_dict.processing_unit == statistic,
            )
        ).first()
        return None if row is None else row[0]

    def _likwid_runs(self, ids: list[int], solver: str) -> list[int]:
        """The LIKWID runs of *solver*: ``likwid`` (simpleFoam, no label) or
        ``likwid-pimpleFoam``."""
        label = "" if solver == SOLVER else solver
        return self._with_tag(ids, TAG_LIKWID, label)

    def clock_value(
        self, ids: list[int], statistic: str, solver: str = SOLVER
    ) -> MetricValue:
        """
        Clock frequency in MHz as in ``freqRange.py``.

        The ``Clock [MHz]`` statistic of every LIKWID group (L2, L3, NUMA) is
        averaged and rounded to two decimals.
        """
        for run in self._likwid_runs(ids, solver):
            values = [
                self._likwid_value(run, f"{group} Clock [MHz]", statistic)
                for group in _LIKWID_GROUPS
            ]
            found = [v for v in values if v is not None]
            if found:
                return round(sum(found) / len(found), 2)
        return None

    def _clock(
        self, statistic: str, solver: str = SOLVER
    ) -> Callable[[RepetitionIDs], list[MetricValue]]:
        """Analysis wrapper of :meth:`clock_value`."""
        return lambda repetition_ids: self._per_size(
            repetition_ids, lambda ids: self.clock_value(ids, statistic, solver)
        )

    def likwid_value(
        self,
        ids: list[int],
        group: str,
        metrics: list[str],
        statistic: str,
        solver: str = SOLVER,
    ) -> MetricValue:
        """Statistic of the first of *metrics* that the LIKWID run of *group* has."""
        for run in self._likwid_runs(ids, solver):
            for metric in metrics:
                value = self._likwid_value(run, f"{group} {metric}", statistic)
                if value is not None:
                    return value
        return None

    def _likwid(
        self, group: str, metrics: list[str], statistic: str, solver: str = SOLVER
    ) -> Callable[[RepetitionIDs], list[MetricValue]]:
        """Analysis wrapper of :meth:`likwid_value`."""
        return lambda repetition_ids: self._per_size(
            repetition_ids,
            lambda ids: self.likwid_value(ids, group, metrics, statistic, solver),
        )

    def pcm_features(self, ids: list[int], names: list[str]) -> dict[str, float] | None:
        """
        System values of PCM counters from the top-down run (``uProf_info.py``).

        The aggregate of the file when it has one, else the mean over the
        cores; ``None`` when the run lacks one of the counters.
        """
        return self._pcm_means(self._with_tag(ids, TAG_TOPDOWN), names)

    def _mpi_ratio(
        self, reduce: Callable[[list[float]], float]
    ) -> Callable[[RepetitionIDs], list[MetricValue]]:
        def ratio(ids: list[int]) -> MetricValue:
            for run in self._with_tag(ids, TAG_TRACE):
                times = self._values(
                    AMDuProfMPI_metrics,
                    AMDuProfMPI_metrics_dict,
                    run,
                    "MPI Time(seconds)",
                )
                # the run time of the traced run is the LAST cumulative
                # ExecutionTime, not the time stepping window (as in the
                # script); with mpi_ratio_basis "total_time" it is the Total
                # Time of the run, which the MPI times of the profiler cover
                last = self._values(
                    OpenFOAMlogs_metrics,
                    OpenFOAMlogs_metrics_dict,
                    run,
                    f"{SOLVER} {self._mpi_basis()}",
                )
                if times and last and last[0] > 0:
                    return reduce(times) / last[0] * 100.0
            return None

        return lambda repetition_ids: self._per_size(repetition_ids, ratio)


def _points(
    x_range: list[float], data: dict[str, list[MetricValue]], name: str
) -> tuple[list[float], list[float]]:
    """The (x, value) pairs of analysis *name* that have a value."""
    pairs = [(x, v) for x, v in zip(x_range, data.get(name, [])) if v is not None]
    return [p[0] for p in pairs], [p[1] for p in pairs]


class OpenFOAMPlotter(Plotter):
    """Generic plots plus the combined FVOPS / ratios figure of the scripts."""

    def _collect(
        self, machine: str
    ) -> tuple[list[float], dict[str, list[MetricValue]], dict[str, str]]:
        """x range, analyses and result info of one machine of the settings."""
        settings = load_settings()
        retriever = DataRetrieversManager.get_retriever(self._profiler_name)
        ids = retriever.get_repetitions(
            settings["session_name_contains"],
            machine,
            settings["use_case_name"],
            settings["sizes_to_get"],
            settings.get("repetition_name_contains", ""),
        )
        x_range, _ = retriever.get_x_range_and_labels(settings["sizes_to_get"], machine)
        data = {
            key.name: values
            for key, values in retriever.get_analyses(
                ids, retriever.discover_analysis_keys([])
            ).items()
        }
        return x_range, data, retriever.get_result_info(ids)

    def make_all(self) -> None:
        """Write the generic output, ``Summary.png`` and, if configured,
        ``Comparison.png``.

        ``Summary.png`` (in the analyses folder) shows the configured machine.
        The optional setting ``compare_machines`` (list of machine names)
        adds ``<output>/<session>/<use case>/Comparison.png``: one panel per
        machine, as in the original scripts.
        """
        super().make_all()
        settings = load_settings()
        x_range, data, info = self._collect(settings["machine_name"])
        use_case_dir = (
            Path(settings["output_directory_path"])
            / info["Session"]
            / info["Machine name"]
            / info["Use case"]
        )
        self.make_comparison_plot(
            [(info["Machine name"], x_range, data)],
            use_case_dir / "analyses" / self._profiler_name / "Summary.png",
        )
        machines = settings.get("compare_machines", [])
        if machines:
            self._make_timing_outputs(
                machines, use_case_dir.parent.parent / info["Use case"]
            )
            entries = []
            for machine in machines:
                x, values, _ = self._collect(machine)
                entries.append((machine, x, values))
            folder = use_case_dir.parent.parent / info["Use case"]
            self.make_comparison_plot(
                entries,
                folder / "Comparison.png",
                settings.get("predicted_fvops", {}),
                settings.get("comparison_series"),
            )
            self._make_machine_figures(machines, entries, folder)

    def _make_timing_outputs(self, machines: list[str], folder: Path) -> None:
        """``Timing comparison.png``, ``Speedup.csv`` and ``Speedup.png``."""
        settings = load_settings()
        retriever = DataRetrieversManager.get_retriever(self._profiler_name)
        assert isinstance(retriever, OpenFOAMAnalyzer)
        runs: dict[str, list[RunTimes]] = {}
        times: dict[str, list[float | None]] = {}
        for machine in machines:
            ids = retriever.get_repetitions(
                settings["session_name_contains"],
                machine,
                settings["use_case_name"],
                settings["sizes_to_get"],
                settings.get("repetition_name_contains", ""),
            )
            runs[machine] = [retriever.run_times(i) for i in ids.values()]
            times[machine] = [
                median_run(r["steps"], retriever._median_mode()) for r in runs[machine]
            ]
        labels = settings.get("machine_labels", {})
        make_timing_plot(
            runs, settings["sizes_to_get"], labels, folder / "Timing comparison.png"
        )
        write_speedup(times, labels, folder / "Speedup.csv", folder / "Speedup.png")

    def _make_machine_figures(
        self,
        machines: list[str],
        entries: list[tuple[str, list[float], dict[str, list[MetricValue]]]],
        folder: Path,
    ) -> None:
        """
        The figures of the UAP scripts, each written only when the data exist:
        ``Solver timing comparison.png`` (simpleFoam and pimpleFoam),
        ``LIKWID L2/L3/Memory.png`` (a column per solver), ``Clock frequency
        [pimpleFoam].png`` and, with the
        setting ``pti_sizes``, ``PTI.png``.
        """
        settings = load_settings()
        sizes = settings["sizes_to_get"]
        labels = settings.get("machine_labels", {})
        retriever = DataRetrieversManager.get_retriever(self._profiler_name)
        assert isinstance(retriever, OpenFOAMAnalyzer)

        def has(values: list[MetricValue]) -> bool:
            return any(v is not None for v in values)

        for prefix, suffix in (("", ""), ("pimpleFoam ", " pimpleFoam")):
            clock = {
                m: d.get(f"{prefix}Clock frequency (avg)", []) for m, _, d in entries
            }
            if any(has(v) for v in clock.values()):
                make_clock_plot(
                    clock, sizes, labels, folder / f"Clock frequency{suffix}.png"
                )
        for group in ("L2", "L3", "Memory"):
            by_solver = {
                solver: {
                    m: {
                        f"{stat} {quantity}": d.get(
                            f"{prefix}{group} {quantity} ({stat})", []
                        )
                        for stat, quantity, _ in LIKWID_ROWS
                    }
                    for m, _, d in entries
                }
                for solver, prefix in (
                    ("simpleFoam", ""),
                    ("pimpleFoam", "pimpleFoam "),
                )
            }
            by_solver = {
                solver: series
                for solver, series in by_solver.items()
                if any(has(v) for rows in series.values() for v in rows.values())
            }
            if by_solver:
                make_likwid_plot(
                    by_solver, sizes, labels, group, folder / f"LIKWID {group}.png"
                )

        times: dict[str, dict[str, list[list[float]]]] = {
            "simpleFoam": {},
            "pimpleFoam": {},
        }
        for machine in machines:
            ids = retriever.get_repetitions(
                settings["session_name_contains"],
                machine,
                settings["use_case_name"],
                sizes,
                settings.get("repetition_name_contains", ""),
            )
            for solver in times:
                times[solver][machine] = [
                    retriever.solver_times(i, solver) for i in ids.values()
                ]
        if any(t for per_size in times["pimpleFoam"].values() for t in per_size):
            make_solver_timing_plot(
                times, sizes, labels, folder / "Solver timing comparison.png"
            )

        pti_sizes = settings.get("pti_sizes")
        if pti_sizes:
            panels = []
            for machine, x_range, data in entries:
                ids = retriever.get_repetitions(
                    settings["session_name_contains"],
                    machine,
                    settings["use_case_name"],
                    pti_sizes,
                    settings.get("repetition_name_contains", ""),
                )
                chosen = [sizes.index(s) for s in pti_sizes]
                values = [retriever.pti_values(i) for i in ids.values()]
                panels.append(
                    (
                        labels.get(machine, machine),
                        [x_range[i] for i in chosen],
                        [data.get("FVOPS", [])[i] for i in chosen],
                        pti_series(values),
                    )
                )
            make_pti_plot(panels, folder / "PTI.png")

    @staticmethod
    def make_comparison_plot(
        entries: list[tuple[str, list[float], dict[str, list[MetricValue]]]],
        png_filename: Path,
        predicted: dict[str, dict[str, Any]] | None = None,
        series: list[str] | None = None,
    ) -> None:
        """
        One panel per machine: FVOPS (left axis, blue) and the ratios in
        percent (right axis) against the cells per rank.

        :param entries: ``(title, x range, analyses)`` per machine.
        :param png_filename: Destination file; parent folders are created.
        :param predicted: Optional ``{machine: {"label", "cells_per_rank",
            "fvops"}}``. The points come from outside Quare (a model or an
            earlier run) and are drawn as red stars on the panel of that
            machine, as in the original ``128_uProfAMD_AOCC_hipic.py``.
        :param series: Analyses drawn on the right axis (default: the L2 and
            L3 miss ratios, ``MPI ratio (avg)`` and the top-down values). The
            UAP scripts use ``MPI ratio (mid-range)`` and the L2 hit ratios.
        """
        fig, axes = plt.subplots(
            1, len(entries), figsize=(7 * len(entries), 5), squeeze=False
        )
        fig.subplots_adjust(left=0.06, right=0.95, wspace=0.45, bottom=0.12)
        for axis, (title, x_range, data) in zip(axes[0], entries):

            right = axis.twinx()
            xs, ys = _points(x_range, data, "FVOPS")
            axis.semilogx(
                xs, ys, "bo", linestyle="dashed", linewidth=0.4, label="FVOPS"
            )
            if predicted and title in predicted:
                extra = predicted[title]
                axis.semilogx(
                    extra["cells_per_rank"],
                    extra["fvops"],
                    "r*",
                    markersize=8,
                    label=extra.get("label", "predicted FVOPS"),
                )
            axis.set_ylabel("FVOPS")
            axis.yaxis.get_major_formatter().set_scientific(False)  # pyright: ignore
            for name in series or DEFAULT_SERIES:
                xs, ys = _points(x_range, data, name)
                if ys:
                    right.semilogx(
                        xs,
                        ys,
                        marker="d",
                        linestyle="dashed",
                        linewidth=0.4,
                        label=name,
                    )
            right.set_ylim(0, 100)
            right.set_ylabel("Ratio [%]")
            axis.set_xlabel("Cells per rank")
            axis.set_title(title)
            axis.grid(alpha=0.3)
            axis.legend(loc="upper left", fontsize=7)
            right.legend(loc="upper right", fontsize=7)
        png_filename.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(png_filename.as_posix(), dpi=200)
        plt.close(fig)


__extension_data_retriever__: type[DataRetriever] = OpenFOAMAnalyzer
__extension_data_plotter__: type[Plotter] = OpenFOAMPlotter
__extension_metrics_table__ = OpenFOAMlogs_metrics
__extension_metrics_dict__ = OpenFOAMlogs_metrics_dict
