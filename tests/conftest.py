"""Shared fixtures: a tiny synthetic AMD uProf PCM data set and isolated state."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import quare.data_retriever as data_retriever
import quare.utils as utils

PCM_TEMPLATE = """\
System:,TestSystem
Number of Sockets :,2
Number of CCDs :,16
Number of Core Complexes(CCX) :,16
Number of Cores :,128
Number of Threads :,256
SMT Enabled in HW:,1
SMT Enabled by OS :,1
Number of Threads sharing L3:,16

CPU Topology
Socket, CCD, CCX, Core(s)
0,0,0,0-7

Core P0 state frequency (MHz):,2250
Multiplex interval for core (ms):,16
Multiplex interval for l3 (ms):,16
Multiplex interval for df (ms):,16
Measured DF Frequency (MHz):,1600
Multiplex interval (ms):,16
Version:,4.2

CORE METRICS
Metric,Core-0,Core-1
L2 Access (pti),{access0},{access1}
L2 Miss (pti),{miss0},{miss1}

L3 METRICS
Metric,CCX-0
L3 Miss %,{l3}
"""

# (task size, date directory, L2 Access per core, L2 Miss per core, L3 Miss %)
RUNS = [
    ("small", "20260101_120000", (100, 100), (20, 40), 10),
    ("small", "20260101_130000", (100, 100), (10, 30), 20),
    ("mid", "20260101_140000", (100, 100), (50, 50), 30),
]


def write_raw_data(raw_dir: Path) -> None:
    """Write the raw tree below *raw_dir*.

    Layout: ``<session>/<machine>/<use_case>/<size>/<date>/<profiler>/``.
    """
    for size, date, access, miss, l3 in RUNS:
        run_dir = raw_dir / "Session1" / "ROME_128" / "motorBike" / size / date
        profiler_dir = run_dir / "AMDuProfPCM"
        profiler_dir.mkdir(parents=True)
        (profiler_dir / "run.csv").write_text(
            PCM_TEMPLATE.format(
                access0=access[0],
                access1=access[1],
                miss0=miss[0],
                miss1=miss[1],
                l3=l3,
            )
        )


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    """Create raw data and a settings file in *tmp_path*; reset global state."""
    write_raw_data(tmp_path / "raw_data")
    settings = {
        "raw_data_directory_path": "raw_data",
        "preprocessed_data_directory_path": "preprocessed_data",
        "db_path": "quare.sqlite3",
        "output_directory_path": "output",
        "task_sizes": {"small": 100, "mid": 10000},
        "metric_names": [],
        "analyses_names": [],
        "session_name_contains": "Session1",
        "machine_name": "ROME_128",
        "use_case_name": "motorBike",
        "sizes_to_get": ["small", "mid"],
        "repetition_name_contains": "Session1",
    }
    (tmp_path / "settings.json").write_text(json.dumps(settings))

    def reset() -> None:
        utils.close_db_session()
        utils._settings_cache = None
        utils._settings_path_override = None
        data_retriever.DataRetrieversManager.retrievers.clear()

    reset()
    utils.set_settings_path(tmp_path / "settings.json")
    yield tmp_path
    reset()
