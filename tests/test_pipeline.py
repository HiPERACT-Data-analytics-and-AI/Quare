"""End-to-end test of the three pipeline steps on synthetic PCM data.

This pins the behaviour of the original pipeline so later changes (new
extensions, data-model changes) can be checked against it.
"""

from __future__ import annotations

import csv
from argparse import Namespace
from pathlib import Path

from sqlalchemy import select

from quare.create_db import create_db
from quare.models import Repetition
from quare.plot import plot
from quare.preprocess import preprocess
from quare.utils import get_db_session


def _results(path: Path) -> dict[str, list[str]]:
    with path.open() as f:
        return {row[0]: row[1:] for row in csv.reader(f)}


def test_preprocess_splits_blocks(workspace: Path) -> None:
    preprocess(Namespace())
    out = (
        workspace
        / "preprocessed_data/Session1/ROME_128/motorBike/small"
        / "20260101_120000/AMDuProfPCM"
    )
    names = sorted(p.name for p in out.glob("*.csv"))
    assert names == [
        "run.core_metrics.csv",
        "run.further_machine_info.csv",
        "run.l3_metrics.csv",
        "run.machine_cpu_topology.csv",
        "run.machine_info.csv",
    ]


def test_create_db_loads_repetitions(workspace: Path) -> None:
    preprocess(Namespace())
    create_db(Namespace())
    session = get_db_session()
    reps = session.execute(select(Repetition)).scalars().all()
    assert len(reps) == 3
    assert all(r.data_consistent for r in reps)
    assert {r.name.split(".")[-1] for r in reps} == {"Session1"}


def test_create_db_is_idempotent(workspace: Path) -> None:
    preprocess(Namespace())
    create_db(Namespace())
    create_db(Namespace())
    assert len(get_db_session().execute(select(Repetition)).scalars().all()) == 3


def test_plot_writes_expected_values(workspace: Path) -> None:
    preprocess(Namespace())
    create_db(Namespace())
    plot(Namespace())
    base = workspace / "output/Session1/ROME_128/motorBike"
    metrics = _results(base / "profiler_metrics/AMDuProfPCM/results.csv")
    # x axis: task size / number of cores (100/128, 10000/128)
    assert [float(v) for v in metrics["Cells per rank (size) | number | "]] == [
        100 / 128,
        10000 / 128,
    ]
    # mean over both repetitions and both cores of "small": (20+40+10+30)/4
    assert [float(v) for v in metrics["L2 Miss (pti) |  | core"]] == [25.0, 50.0]
    assert [float(v) for v in metrics["L3 Miss % |  | ccx"]] == [15.0, 30.0]
    # metrics and analyses are kept apart
    assert "L2 miss ratio (total) | % | core" not in metrics
    analyses = _results(base / "analyses/AMDuProfPCM/results.csv")
    assert [float(v) for v in analyses["L2 miss ratio (total) | % | core"]] == [
        25.0,
        50.0,
    ]
    assert "L2 Miss (pti) |  | core" not in analyses
    # every extension writes into its own folder
    assert (base / "analyses/AMDuProfMPI/results.csv").exists()
    assert (base / "profiler_metrics/AMDuProfPCM/INFO.png").exists()
