"""
Figures of the UAP scripts: solver timing, LIKWID, clock and PTI.

Pure plotting functions that work on values already read from the database;
they reproduce ``timing_comp.py``, ``likwid.py`` and ``pti.py`` of the UAP
analysis scripts.  Every figure has one colour per machine.

Authors: Marcin Lawenda, Łukasz Szustak
"""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
from matplotlib import pyplot as plt

PTI_MIN_MEAN = 2.0
"""Counters with a mean up to this many events per thousand instructions are
not drawn (``pti.py``)."""

PTI_SKIPPED = ("DC Access (pti)",)
"""Counters that ``pti.py`` leaves out of the figure."""

LIKWID_ROWS = (
    ("sum", "data volume", "total {title} data volume for all cores"),
    ("avg", "data volume", "avg {title} data volume for 1 core"),
    ("sum", "bandwidth", "total {title} bandwidth for all cores"),
    ("avg", "bandwidth", "avg {title} bandwidth for 1 core"),
)
"""(statistic, quantity, panel title) of the rows of the LIKWID figure."""


def _save(fig, png_filename: Path) -> None:
    png_filename.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(png_filename.as_posix(), dpi=200)
    plt.close(fig)


def make_solver_timing_plot(
    times: dict[str, dict[str, list[list[float]]]],
    sizes: list[str],
    labels: dict[str, str],
    png_filename: Path,
) -> None:
    """
    One row per size, simpleFoam on the left and pimpleFoam on the right.

    :param times: ``{solver: {machine: [times of the runs per size]}}`` with
        the solvers ``simpleFoam`` and ``pimpleFoam``; one point per run.
    :param sizes: Size names, one row each.
    :param labels: Display name per machine (default: the machine name).
    :param png_filename: Destination file; parent folders are created.

    The vertical range of a row is 1.3 times the largest pimpleFoam time of
    the first machine, for both columns, as in ``timing_comp.py``.
    """
    generator = np.random.default_rng(0)
    fig, axes = plt.subplots(
        len(sizes), 2, figsize=(12, 2.6 * len(sizes) + 1), layout="constrained"
    )
    axes = np.atleast_2d(axes)
    for row, size in enumerate(sizes):
        reference = next(iter(times["pimpleFoam"].values()))[row]
        top = max(reference, default=0) * 1.3
        for column, solver in enumerate(("simpleFoam", "pimpleFoam")):
            axis = axes[row][column]
            machines = list(times[solver])
            for position, machine in enumerate(machines):
                values = times[solver][machine][row]
                jitter = generator.uniform(-0.15, 0.15, len(values))
                axis.scatter(position + jitter, values, alpha=0.5, linewidth=1, s=25)
            axis.set_xticks(range(len(machines)))
            axis.set_xticklabels(
                [labels.get(m, m) for m in machines], fontsize=7, rotation=20
            )
            axis.set_ylim(0, top if top else None)
            axis.set_ylabel("Execution time [s]")
            axis.set_title(f"{solver}, size: {size}", loc="right")
    _save(fig, png_filename)


def make_likwid_plot(
    data: dict[str, dict[str, dict[str, list[float | None]]]],
    sizes: list[str],
    labels: dict[str, str],
    title: str,
    png_filename: Path,
) -> None:
    """
    Data volume and bandwidth of one LIKWID group against the size.

    One column per solver, as in ``likwid.py``.

    :param data: ``{solver: {machine: {"<statistic> <quantity>": values per
        size}}}`` with the keys of :data:`LIKWID_ROWS` (``sum data volume``).
    :param sizes: Size names of the x axis.
    :param labels: Display name per machine.
    :param title: Group name used in the panel titles (``L2``).
    :param png_filename: Destination file; parent folders are created.
    """
    x = list(range(len(sizes)))
    fig, axes = plt.subplots(
        4, len(data), figsize=(7 * len(data), 9), squeeze=False, layout="constrained"
    )
    for column, (solver, per_machine) in enumerate(data.items()):
        for row, (statistic, quantity, pattern) in enumerate(LIKWID_ROWS):
            axis = axes[row][column]
            for index, (machine, series) in enumerate(per_machine.items()):
                values = series.get(f"{statistic} {quantity}", [])
                points = [(i, v) for i, v in zip(x, values) if v is not None]
                if not points:
                    continue
                colour = f"C{index}"
                axis.plot(
                    [p[0] for p in points],
                    [p[1] for p in points],
                    colour,
                    linestyle="dashed",
                    linewidth=0.4,
                )
                axis.plot(
                    [p[0] for p in points],
                    [p[1] for p in points],
                    colour + ".",
                    markersize=6,
                    label=labels.get(machine, machine),
                )
            axis.set_xticks(x)
            axis.set_xticklabels(sizes, fontsize=8)
            axis.set_title(f"{solver}: " + pattern.format(title=title), fontsize=8)
            axis.legend(loc="upper left", fontsize=6)
    _save(fig, png_filename)


def make_clock_plot(
    clock: dict[str, list[float | None]],
    sizes: list[str],
    labels: dict[str, str],
    png_filename: Path,
) -> None:
    """
    Average clock frequency of every machine against the size.

    :param clock: ``{machine: average clock in MHz per size}``.
    """
    x = list(range(len(sizes)))
    fig, axis = plt.subplots(1, 1, figsize=(7, 5), layout="constrained")
    for index, (machine, values) in enumerate(clock.items()):
        points = [(i, v) for i, v in zip(x, values) if v is not None]
        if not points:
            continue
        axis.plot(
            [p[0] for p in points],
            [p[1] for p in points],
            color="k",
            linestyle="dashed",
            linewidth=0.4,
        )
        axis.plot(
            [p[0] for p in points],
            [p[1] for p in points],
            f"C{index}o",
            markersize=8,
            label=labels.get(machine, machine),
        )
    axis.set_xticks(x)
    axis.set_xticklabels(sizes, fontsize=8)
    axis.set_xlabel("Size")
    axis.set_ylim(0, 4000)
    axis.set_ylabel("Ave freq [MHz]")
    axis.yaxis.get_major_formatter().set_scientific(False)  # pyright: ignore
    axis.legend(loc="lower right", fontsize=8)
    axis.set_title("Ave freq of CPUs", fontsize=12)
    _save(fig, png_filename)


def pti_series(
    values: list[dict[str, float]],
) -> dict[str, list[float | None]]:
    """
    The counters of :func:`make_pti_plot` that are drawn.

    :param values: Per size the ``(pti)`` counters of the run.
    :returns: ``{counter: value per size}`` for the counters whose mean over
        the sizes is above :data:`PTI_MIN_MEAN`, in order of first appearance.
    """
    names: list[str] = []
    for per_size in values:
        names += [n for n in per_size if n not in names and n not in PTI_SKIPPED]
    series: dict[str, list[float | None]] = {}
    for name in names:
        row = [per_size.get(name) for per_size in values]
        found = [v for v in row if v is not None]
        if found and sum(found) / len(found) > PTI_MIN_MEAN:
            series[name] = row
    return series


def make_pti_plot(
    entries: list[tuple[str, list[float], list[float | None], dict[str, list]]],
    png_filename: Path,
    mpi_volume: bool = False,
) -> None:
    """
    One panel per machine: FVOPS (left) and the PTI counters (right).

    :param entries: ``(title, cells per rank, left values, pti_series)`` per
        machine; the left values are FVOPS, or with *mpi_volume* the MPI
        volume per cell, step and rank [B] (``pti.py --mpi``).
    :param png_filename: Destination file; parent folders are created.
    :param mpi_volume: Left axis is the MPI volume instead of FVOPS.
    """
    legend = "MPI volume per cell per step per core" if mpi_volume else "FVOPS"
    fig, axes = plt.subplots(
        1, len(entries), figsize=(7 * len(entries), 5), squeeze=False
    )
    fig.subplots_adjust(left=0.06, right=0.95, wspace=0.45, bottom=0.12)
    for axis, (title, x, fvops, series) in zip(axes[0], entries):
        right = axis.twinx()
        points = [(a, b) for a, b in zip(x, fvops) if b is not None]
        axis.semilogx(
            [p[0] for p in points],
            [p[1] for p in points],
            "bo",
            linestyle="dashed",
            linewidth=0.4,
            label=legend,
        )
        colours = plt.get_cmap("rainbow")(np.linspace(0, 1, max(len(series), 1)))
        for colour, (name, row) in zip(colours, series.items()):
            pairs = [(a, b) for a, b in zip(x, row) if b is not None]
            right.semilogx(
                [p[0] for p in pairs],
                [p[1] for p in pairs],
                color=colour,
                marker=".",
                linestyle="dashed",
                linewidth=0.4,
                label=name,
            )
        axis.set_xlabel("Cells per rank")
        axis.set_ylabel("MPI volume traffic [B]" if mpi_volume else "FVOPS")
        axis.yaxis.get_major_formatter().set_scientific(False)  # pyright: ignore
        right.set_ylim(0, 35)
        right.set_ylabel("PTI")
        axis.set_title(title)
        axis.legend(loc="upper left", fontsize=7)
        right.legend(loc="upper right", fontsize=5)
    _save(fig, png_filename)


def make_mpi_profile_plot(
    profiles: list[dict[str, list[float]] | None],
    sizes: list[str],
    png_filename: Path,
) -> None:
    """
    MPI time step by step, one panel per size (``mpi_profiling.py``).

    :param profiles: Per size the series of the profiling run (``steps``,
        ``reduce``, ``all-all``, ``other``), or ``None`` without one.
    :param sizes: Size names, titles of the panels.
    :param png_filename: Destination file; parent folders are created.

    As in the script the last two entries of each series are dropped, the
    total MPI time is ``reduce + all-all + other`` and its share of the run
    time is taken at the step before the last one.
    """
    fig, axes = plt.subplots(
        nrows=len(sizes), ncols=1, figsize=(6, 3.3 * len(sizes)), layout="constrained"
    )
    for axis, size, profile in zip(np.atleast_1d(axes), sizes, profiles):
        axis.set_title(f"size:{size}", x=0.5, y=0.9, fontsize=12)
        axis.set_ylabel("Incremental time [s]")
        axis.set_xlabel("Subsequent time steps")
        if not profile:
            continue
        total = [
            a + b + c
            for a, b, c in zip(profile["reduce"], profile["all-all"], profile["other"])
        ]
        steps, reduce_, all_all, total = (
            v[:-2]
            for v in (profile["steps"], profile["reduce"], profile["all-all"], total)
        )
        percent = f"{total[-2] / steps[-2] * 100.0:2.0f}%" if len(total) > 1 else ""
        for values, label in (
            (steps, "Iterations runtime"),
            (reduce_, "MPI Reduce"),
            (all_all, "MPI All-All"),
            (total, f"Total MPI (around {percent} of runtime"),
        ):
            axis.plot(values, linestyle="dashed", linewidth=1, label=label)
        axis.legend(loc="upper left", fontsize=8)
    _save(fig, png_filename)


def write_mpi_tables(
    data: dict[str, dict[str, list]],
    sizes: list[str],
    labels: dict[str, str],
    calls: tuple[str, ...],
    folder: Path,
) -> None:
    """
    The tables of ``mpi_summary.py`` as CSV files in *folder*.

    *data* maps a machine to its analyses.  ``MPI time.csv`` has min, avg and
    max rank time [s] per size, ``MPI calls.csv`` the share of the selected
    MPI functions in the MPI time [%] and ``MPI volume.csv`` the total volume
    of all ranks [GB].  A table without any value is not written; a missing
    value is left empty.  Numbers have two decimals as in the script.
    """

    def cell(values: list, index: int) -> str:
        value = values[index] if index < len(values) else None
        return "" if value is None else f"{value:.2f}"

    def has(*names: str) -> bool:
        return any(
            v is not None for d in data.values() for n in names for v in d.get(n, [])
        )

    folder.mkdir(parents=True, exist_ok=True)
    stats = ("min", "avg", "max")
    if has(*(f"MPI time ({s})" for s in stats)):
        rows = [["machine"] + [f"{size} {s}" for size in sizes for s in stats]]
        for machine, d in data.items():
            row = [labels.get(machine, machine)]
            for i in range(len(sizes)):
                row += [cell(d.get(f"MPI time ({s})", []), i) for s in stats]
            rows.append(row)
        _write_csv(folder / "MPI time.csv", rows)
    names = [f"{c} share of MPI time" for c in calls]
    if has(*names):
        rows = [["machine", "function"] + list(sizes)]
        for machine, d in data.items():
            for call, name in zip(calls, names):
                rows.append(
                    [labels.get(machine, machine), call]
                    + [cell(d.get(name, []), i) for i in range(len(sizes))]
                )
        _write_csv(folder / "MPI calls.csv", rows)
    if has("MPI volume (aggregate)"):
        rows = [["machine"] + list(sizes)]
        for machine, d in data.items():
            values = d.get("MPI volume (aggregate)", [])
            rows.append(
                [labels.get(machine, machine)]
                + [cell(values, i) for i in range(len(sizes))]
            )
        _write_csv(folder / "MPI volume.csv", rows)


def _write_csv(path: Path, rows: list[list[str]]) -> None:
    with open(path, "w", newline="") as csv_file:
        csv.writer(csv_file).writerows(rows)
