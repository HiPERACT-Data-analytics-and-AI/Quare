"""Timing comparison and speed-up tables (``timingComp.py``, ``speddup.py``)."""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path

import pytest

from quare.data_retriever import DataRetrieversManager
from quare.extensions.OpenFOAMlogs_ext.comparison import (
    median_run,
    speedup_ranges,
    speedup_table,
)

from .test_motorbike_2024 import _load, imported  # noqa: F401

# the time table of speddup.py (time stepping, median of 5 runs)
TIMES = {
    "rome128": [4.12, 6.25, 8.06, 28.10, 74.70, 144.95, 304.74, 1243.00],
    "milan128": [3.71, 5.15, 7.06, 24.28, 69.42, 133.85, 281.24, 1161.68],
    "genoa128": [2.64, 3.82, 5.11, 13.71, 35.32, 67.59, 137.12, 560.63],
    "bergamo256": [3.31, 4.04, 4.81, 11.47, 29.88, 55.71, 118.39, 498.73],
}
LABELS = {
    "rome128": "Rome (128c)",
    "milan128": "Milan (128c)",
    "genoa128": "Genoa (128c)",
    "bergamo256": "Bergamo (256c)",
}

# results of timingComp.py on the Genoa 128 subset (xsmall, small)
EXPECTED_RUNS = {
    "total": [
        [3.466814887, 3.543173843, 3.632405851, 5.645850846, 6.701413701],
        [4.857744689, 4.929328765, 5.04468754, 6.513525176, 7.25838547],
    ],
    "steps": [
        [2.49, 2.56, 2.64, 2.79, 2.95],
        [3.64, 3.68, 3.82, 4.03, 4.79],
    ],
    "pct": [
        [
            45.363562609876844,
            50.83379065944244,
            74.41989503606283,
            74.50946854373693,
            74.60620071553782,
        ],
        [
            63.56005217043472,
            67.50812588078213,
            76.68386874171091,
            77.19631722292024,
            77.90373474746465,
        ],
    ],
}


def test_speedup_matches_the_original_table() -> None:
    table = speedup_table(TIMES, LABELS)
    assert table[0] == ["", *LABELS.values()]
    by_row = {row[0]: row[1:] for row in table[1:]}
    # values printed by speddup.py for these platforms
    assert by_row["Rome (128c)"] == [
        "-",
        "1.07x - 1.21x",
        "1.56x - 2.22x",
        "1.24x - 2.60x",
    ]
    assert by_row["Genoa (128c)"] == [
        "0.45x - 0.64x",
        "0.48x - 0.74x",
        "-",
        "0.80x - 1.21x",
    ]
    assert by_row["Bergamo (256c)"][2] == "0.82x - 1.25x"


def test_speedup_skips_missing_sizes() -> None:
    ranges = speedup_ranges({"a": [2.0, None, 4.0], "b": [1.0, 3.0, 1.0], "c": [None] * 3})
    assert ranges[("a", "b")] == (2.0, 4.0)
    assert ranges[("a", "c")] is None


def test_median_run_is_the_lower_median() -> None:
    assert median_run([5, 1, 3, 2, 4]) == 3
    assert median_run([4, 1, 3, 2]) == 2
    assert median_run([]) is None


def test_run_times_match_the_original_script(imported: Path) -> None:  # noqa: F811
    _load(imported)
    from quare import utils

    settings = utils.load_settings()
    retriever = DataRetrieversManager.get_retriever("OpenFOAMlogs")
    ids = retriever.get_repetitions(
        settings["session_name_contains"],
        settings["machine_name"],
        settings["use_case_name"],
        settings["sizes_to_get"],
        "",
    )
    runs = [retriever.run_times(i) for i in ids.values()]
    for key, expected in EXPECTED_RUNS.items():
        for got, want in zip((r[key] for r in runs), expected):
            assert got == pytest.approx(want, rel=1e-12), key
    analyses = {
        k.name: v
        for k, v in retriever.get_analyses(
            ids, retriever.discover_analysis_keys([])
        ).items()
    }
    assert analyses["Time stepping time"] == pytest.approx([2.64, 3.82])
    assert analyses["Total time"] == pytest.approx([3.632405851, 5.04468754])
