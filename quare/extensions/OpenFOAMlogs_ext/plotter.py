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

Repetition names without a tag are treated as timing and counter runs.

Registered analyses
-------------------
=============================== =========================================
Name                            Definition
=============================== =========================================
FVOPS                           cells / (median window time / (steps-1))
L3 miss ratio                   mean over CCXs of ``L3 Miss %``
L2 ... ratio (six)              ratio of the means over cores of the pti
                                counters, in percent
Backend Bound Memory,           mean over cores of the top-down value
Frontend Bound, Retiring
MPI ratio (min/avg/max)         per-rank MPI time / last cumulative
                                ``ExecutionTime`` of the traced run
=============================== =========================================

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
from .comparison import RunTimes, make_timing_plot, median_run, write_speedup
from .models import OpenFOAMlogs_metrics, OpenFOAMlogs_metrics_dict

SOLVER = "simpleFoam"
TAG_TIMING = "counters"
TAG_TRACE = "trace"
TAG_TOPDOWN = "topdown"
_ALL_TAGS = (TAG_TIMING, TAG_TRACE, TAG_TOPDOWN)

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
            UniqueMetricKey("MPI ratio (min)", "%", "rank"): self._mpi_ratio(min),
            UniqueMetricKey("MPI ratio (avg)", "%", "rank"): self._mpi_ratio(
                statistics.fmean
            ),
            UniqueMetricKey("MPI ratio (max)", "%", "rank"): self._mpi_ratio(max),
        }
        for name in _L2_RATIOS:
            analytics[UniqueMetricKey(name, "%", "core")] = self._l2_ratio(name)
        for name, counter in _TOPDOWN.items():
            analytics[UniqueMetricKey(name, "%", "core")] = self._topdown(counter)
        self.AVAILABLE_ANALYTICS |= analytics

    # -- helpers -----------------------------------------------------------

    def _with_tag(self, repetition_ids: list[int], tag: str) -> list[int]:
        """Return the repetitions of *repetition_ids* that carry *tag*.

        Repetitions without any known tag count as timing (``counters``) runs.
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
            tagged = [t for t in _ALL_TAGS if run.endswith(f"_{t}")]
            if (tagged[0] if tagged else TAG_TIMING) == tag:
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

    def _first_with_values(
        self,
        metrics: type[MetricsBase],
        metrics_dict: type[MetricsDictBase],
        repetitions: list[int],
        names: list[str],
    ) -> dict[str, list[float]] | None:
        """Values of *names* in the first repetition that has all of them."""
        for repetition in repetitions:
            found = {
                n: self._values(metrics, metrics_dict, repetition, n) for n in names
            }
            if all(found.values()):
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
            for run in self._with_tag(ids, TAG_TIMING):
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
            if not windows or steps <= 0:
                return None
            windows.sort()
            median = windows[(len(windows) - 1) // 2]
            return cells / (median / steps) if median > 0 else None

        return self._per_size(repetition_ids, fvops)

    def run_times(self, ids: list[int]) -> RunTimes:
        """
        Times of all timing runs of one task size (see :data:`RunTimes`).

        A run counts only with a ``Total Time`` line; the lists are sorted
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
            if not (first and last and whole):
                continue
            steps.append(last[0] - first[0])
            total.append(whole[0])
            all_steps.append(last[0])
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
            repetition_ids, lambda ids: median_run(self.run_times(ids)[key])
        )

    def _calc_l3(self, repetition_ids: RepetitionIDs) -> list[MetricValue]:
        def l3(ids: list[int]) -> MetricValue:
            found = self._first_with_values(
                AMDuProfPCM_metrics,
                AMDuProfPCM_metrics_dict,
                self._with_tag(ids, TAG_TIMING),
                ["L3 Miss %"],
            )
            return statistics.fmean(found["L3 Miss %"]) if found else None

        return self._per_size(repetition_ids, l3)

    def _l2_ratio(self, name: str) -> Callable[[RepetitionIDs], list[MetricValue]]:
        numerator, denominator = _L2_RATIOS[name]

        def ratio(ids: list[int]) -> MetricValue:
            found = self._first_with_values(
                AMDuProfPCM_metrics,
                AMDuProfPCM_metrics_dict,
                self._with_tag(ids, TAG_TIMING),
                [numerator, denominator],
            )
            if not found:
                return None
            den = statistics.fmean(found[denominator])
            return statistics.fmean(found[numerator]) / den * 100.0 if den else None

        return lambda repetition_ids: self._per_size(repetition_ids, ratio)

    def _topdown(self, counter: str) -> Callable[[RepetitionIDs], list[MetricValue]]:
        def mean(ids: list[int]) -> MetricValue:
            found = self._first_with_values(
                AMDuProfPCM_metrics,
                AMDuProfPCM_metrics_dict,
                self._with_tag(ids, TAG_TOPDOWN),
                [counter],
            )
            return statistics.fmean(found[counter]) if found else None

        return lambda repetition_ids: self._per_size(repetition_ids, mean)

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
                # ExecutionTime, not the time stepping window (as in the script)
                last = self._values(
                    OpenFOAMlogs_metrics,
                    OpenFOAMlogs_metrics_dict,
                    run,
                    f"{SOLVER} last step time",
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
            self.make_comparison_plot(
                entries,
                use_case_dir.parent.parent / info["Use case"] / "Comparison.png",
            )

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
            times[machine] = [median_run(r["steps"]) for r in runs[machine]]
        labels = settings.get("machine_labels", {})
        make_timing_plot(
            runs, settings["sizes_to_get"], labels, folder / "Timing comparison.png"
        )
        write_speedup(times, labels, folder / "Speedup.csv", folder / "Speedup.png")

    @staticmethod
    def make_comparison_plot(
        entries: list[tuple[str, list[float], dict[str, list[MetricValue]]]],
        png_filename: Path,
    ) -> None:
        """
        One panel per machine: FVOPS (left axis, blue) and the ratios in
        percent (right axis) against the cells per rank.

        :param entries: ``(title, x range, analyses)`` per machine.
        :param png_filename: Destination file; parent folders are created.
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
            axis.set_ylabel("FVOPS")
            axis.yaxis.get_major_formatter().set_scientific(False)  # pyright: ignore
            for name in (
                "L2 miss ratio (total)",
                "L2 miss ratio from L1DC",
                "L2 miss ratio from HWPF",
                "L3 miss ratio",
                "MPI ratio (avg)",
                "Backend Bound Memory",
                "Frontend Bound",
            ):
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
