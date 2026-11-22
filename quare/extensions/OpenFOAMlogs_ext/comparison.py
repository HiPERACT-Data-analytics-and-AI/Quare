"""
Comparison of several machines: run times and pairwise speed-ups.

Pure functions that work on values already read from the database; they
reproduce ``timingComp.py`` and ``speddup.py`` of the original analysis
scripts.

Authors: Marcin Lawenda, Łukasz Szustak
"""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
from matplotlib import pyplot as plt

RunTimes = dict[str, list[float]]
"""Per size: sorted ``steps`` (time-stepping window), ``total`` (``Total
Time``), ``all_steps`` (last ``ExecutionTime``), ``pct`` (last
``ExecutionTime`` as percent of the total time) and ``delay`` of all runs.
Every list is sorted on its own, as in the original script."""


def median_run(values: list[float]) -> float | None:
    """Lower median of *values*; the middle one for the usual five runs."""
    if not values:
        return None
    return sorted(values)[(len(values) - 1) // 2]


def speedup_ranges(
    times: dict[str, list[float | None]],
) -> dict[tuple[str, str], tuple[float, float] | None]:
    """
    Min and max over the sizes of ``time[row] / time[column]``.

    Values above 1 mean that the *column* machine is faster.  Sizes for which
    one of the two times is missing are skipped; a pair without any common
    size gives ``None``.  The diagonal is not included.

    :param times: Time per size of every machine, in the order of the sizes.
    :returns: ``{(row machine, column machine): (min, max) or None}``.
    """
    result: dict[tuple[str, str], tuple[float, float] | None] = {}
    for row, row_times in times.items():
        for column, column_times in times.items():
            if row == column:
                continue
            ratios = [
                a / b
                for a, b in zip(row_times, column_times)
                if a is not None and b is not None and b > 0
            ]
            result[(row, column)] = (min(ratios), max(ratios)) if ratios else None
    return result


def speedup_table(
    times: dict[str, list[float | None]], labels: dict[str, str]
) -> list[list[str]]:
    """The speed-up ranges as a table of text cells (``1.23x - 2.34x``)."""
    ranges = speedup_ranges(times)
    header = [""] + [labels.get(name, name) for name in times]
    rows = [header]
    for row in times:
        cells = [labels.get(row, row)]
        for column in times:
            if row == column:
                cells.append("-")
                continue
            span = ranges[(row, column)]
            cells.append("n/a" if span is None else f"{span[0]:.2f}x - {span[1]:.2f}x")
        rows.append(cells)
    return rows


def write_speedup(
    times: dict[str, list[float | None]],
    labels: dict[str, str],
    csv_filename: Path,
    png_filename: Path,
) -> None:
    """Write the speed-up table as CSV and as a table image."""
    table = speedup_table(times, labels)
    csv_filename.parent.mkdir(parents=True, exist_ok=True)
    with open(csv_filename, "w", newline="") as csv_file:
        csv.writer(csv_file).writerows(table)
    size = (1.6 * len(table[0]) + 1.5, 0.5 * len(table) + 1)
    fig, axis = plt.subplots(figsize=size)
    axis.axis("off")
    shown = axis.table(table[1:], colLabels=table[0], loc="center", cellLoc="center")
    shown.auto_set_font_size(False)
    shown.set_fontsize(8)
    shown.scale(1, 1.4)
    axis.set_title("Speed-up of the column machine over the row machine", fontsize=10)
    fig.savefig(png_filename.as_posix(), dpi=200, bbox_inches="tight")
    plt.close(fig)


def make_timing_plot(
    runs: dict[str, list[RunTimes]],
    sizes: list[str],
    labels: dict[str, str],
    png_filename: Path,
) -> None:
    """
    One row per size, one point per run and machine.

    Left: time-stepping time in seconds.  Right: the last ``ExecutionTime`` as
    percent of the total time.  The jitter of the points uses a fixed seed, so
    the figure is reproducible.

    :param runs: For every machine and size the run times (:data:`RunTimes`).
    :param sizes: Size names, one row each.
    :param labels: Display name per machine (default: the machine name).
    :param png_filename: Destination file; parent folders are created.
    """
    generator = np.random.default_rng(0)
    fig, axes = plt.subplots(
        len(sizes), 2, figsize=(12, 2.6 * len(sizes) + 1), layout="constrained"
    )
    axes = np.atleast_2d(axes)
    names = list(runs)
    for row, size in enumerate(sizes):
        for column, (key, ylabel) in enumerate(
            (("steps", "Execution time [s]"), ("pct", "Percent of total time"))
        ):
            axis = axes[row][column]
            for position, name in enumerate(names):
                values = runs[name][row].get(key, [])
                jitter = generator.uniform(-0.15, 0.15, len(values))
                axis.scatter(position + jitter, values, alpha=0.5, linewidth=1, s=25)
            axis.set_xticks(range(len(names)))
            axis.set_xticklabels(
                [labels.get(n, n) for n in names], fontsize=7, rotation=20
            )
            axis.set_ylabel(ylabel)
            axis.set_title(f"simpleFoam, size: {size}", loc="right")
            axis.set_ylim(0, 100 if key == "pct" else None)
            if key == "steps":
                top = max(
                    (max(runs[n][row].get("steps", [0])) for n in names), default=0
                )
                axis.set_ylim(0, top * 1.3 if top else None)
    png_filename.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(png_filename.as_posix(), dpi=200)
    plt.close(fig)
