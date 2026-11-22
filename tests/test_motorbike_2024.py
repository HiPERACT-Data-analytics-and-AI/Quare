"""Import and loading of the 2024 motorBike measurements (Genoa 128 subset).

The expected numbers are the results of the original analysis scripts
(``128_uProfAMD_AOCC.py``) run on the same files.
"""

from __future__ import annotations

import json
import statistics
from argparse import Namespace
from pathlib import Path

import pytest
from sqlalchemy import select, text

import quare.data_retriever as data_retriever
import quare.utils as utils
from quare.create_db import create_db
from quare.importers.motorbike2024 import import_motorbike_2024
from quare.models import Machine, Repetition, TaskSizesDict
from quare.preprocess import preprocess
from quare.utils import get_db_session

DATA = Path(__file__).parent / "data" / "motorBike_2024"
MAPPING = {
    "session": "Motorbike2024",
    "use_case": "motorBike",
    "sizes": ["xsmall", "small"],
    "machines": {
        "GENOA_128": {
            "source": "128_GENOA",
            "counters": "C_AOCC_9554_Sumup",
            "trace": "C_AOCC_9554_Sumup_Trace_12_30_2023_00_45_41",
            "topdown": "Zen4_AOCC_9554_Sumup02_06_2024_15_04_14",
        }
    },
}
CELLS = {"xsmall": 167555, "small": 355474}

# Results of the original scripts for (xsmall, small).
EXPECTED_FVOPS = [12630092.803030303, 18518148.167539265]
EXPECTED_L3 = [15.795625000000001, 17.494374999999998]
EXPECTED_MPI_MEAN_TIME = [2.493163359375, 3.370784375]
EXPECTED_BACKEND_MEMORY = [23.426328125, 23.791171875]
EXPECTED_FRONTEND = [13.3359375, 11.889765625]
EXPECTED_RETIRING = [52.311171875, 52.246640625]
EXPECTED_MPI_RATIO = {
    "min": [59.48749999999999, 48.04750593824229],
    "avg": [82.01195261101974, 80.06613717339668],
    "max": [89.88125, 88.81828978622327],
}
EXPECTED_L2 = {
    "L2 miss ratio (total)": [17.779421262754205, 19.21423495179479],
    "L2 miss ratio from L1DC": [9.997724539219192, 9.972381140264353],
    "L2 miss ratio from HWPF": [21.67532655899392, 24.824290299869933],
    "L2 hit ratio (total)": [81.48669948431012, 79.97184118427934],
    "L2 hit ratio from L1DC": [88.62399635926275, 88.35349948488634],
    "L2 hit ratio from HWPF": [78.33064578054213, 75.1786928868895],
}


@pytest.fixture
def imported(tmp_path: Path) -> Path:
    """Import the subset, write settings and reset the global state."""
    raw = tmp_path / "raw_data"
    import_motorbike_2024(DATA, raw, MAPPING)
    settings = {
        "raw_data_directory_path": "raw_data",
        "preprocessed_data_directory_path": "preprocessed_data",
        "db_path": "quare.sqlite3",
        "output_directory_path": "output",
        "task_sizes": CELLS,
        "metric_names": [],
        "analyses_names": [],
        "session_name_contains": "Motorbike2024",
        "machine_name": "GENOA_128",
        "use_case_name": "motorBike",
        "sizes_to_get": ["xsmall", "small"],
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


def _run_dirs(root: Path, size: str) -> list[str]:
    base = root / "raw_data/Motorbike2024/GENOA_128/motorBike" / size
    return sorted(p.name for p in base.iterdir())


def test_import_creates_one_directory_per_run(imported: Path) -> None:
    assert _run_dirs(imported, "xsmall") == [
        "20231228_174709_counters",
        "20231228_174712_counters",
        "20231228_174716_counters",
        "20231229_233032_counters",
        "20231229_233032_trace",
        "20231229_233039_counters",
        "20240206_150427_topdown",
    ]
    run = imported / "raw_data/Motorbike2024/GENOA_128/motorBike/xsmall"
    # the counter file belongs to the run uProfALL1 only
    assert (run / "20231228_174712_counters/AMDuProfPCM").is_dir()
    assert not (run / "20231228_174716_counters/AMDuProfPCM").exists()
    assert (run / "20231229_233032_trace/AMDuProfMPI/mpi-summary.csv").exists()


def test_import_counts_and_unknown_machine(tmp_path: Path) -> None:
    counts = import_motorbike_2024(DATA, tmp_path, MAPPING)
    assert counts == {"counters": 10, "trace": 2, "topdown": 2}
    with pytest.raises(ValueError, match="not in the mapping"):
        import_motorbike_2024(DATA, tmp_path, MAPPING, ["NOPE_1"])


def _load(root: Path) -> None:
    preprocess(Namespace())
    create_db(Namespace())


def test_machine_and_sizes(imported: Path) -> None:
    _load(imported)
    session = get_db_session()
    machine = session.execute(select(Machine)).scalar_one()
    assert (machine.name, machine.num_of_cores) == ("GENOA_128", 128)
    sizes = {t.name: t.size for t in session.execute(select(TaskSizesDict)).scalars()}
    assert sizes == CELLS
    assert len(session.execute(select(Repetition)).scalars().all()) == 14


def _metric(session, table: str, repetition_id: int, name: str) -> list[float]:
    return [
        row[0]
        for row in session.execute(
            text(
                f'SELECT m.value FROM "{table}_metrics" m '
                f'JOIN "{table}_metrics_dict" d ON d.id = m.metric '
                "WHERE m.repetition = :r AND d.name = :n ORDER BY m.processing_unit_idx"
            ),
            {"r": repetition_id, "n": name},
        )
    ]


def _repetitions(session, size: str, tag: str) -> list[int]:
    return [
        row[0]
        for row in session.execute(
            select(Repetition.id)
            .join(TaskSizesDict, TaskSizesDict.id == Repetition.task_size)
            .where(TaskSizesDict.name == size, Repetition.name.contains(f"_{tag}."))
            .order_by(Repetition.name)
        )
    ]


def test_openfoam_logs_loaded(imported: Path) -> None:
    _load(imported)
    session = get_db_session()
    runs = _repetitions(session, "xsmall", "counters")
    assert len(runs) == 5
    for run in runs:
        assert _metric(session, "OpenFOAMlogs", run, "cells") == [167555.0]
        assert _metric(session, "OpenFOAMlogs", run, "ranks") == [128.0]
        assert _metric(session, "OpenFOAMlogs", run, "simpleFoam time steps") == [200.0]
    # the run of 2023-12-28 17:47:09 (log.simpleFoam.src)
    first = runs[0]
    assert _metric(session, "OpenFOAMlogs", first, "simpleFoam total time") == [
        3.466814887
    ]


def test_fvops_from_the_database_matches_the_original_script(
    imported: Path,
) -> None:
    """Median of five time stepping windows, as in the original script."""
    _load(imported)
    session = get_db_session()
    fvops = []
    for size in ("xsmall", "small"):
        windows, steps, cells = [], 0, 0.0
        for run in _repetitions(session, size, "counters"):
            first = _metric(session, "OpenFOAMlogs", run, "simpleFoam first step time")
            last = _metric(session, "OpenFOAMlogs", run, "simpleFoam last step time")
            windows.append(last[0] - first[0])
            n = _metric(session, "OpenFOAMlogs", run, "simpleFoam time steps")
            steps = n[0] - 1
            cells = _metric(session, "OpenFOAMlogs", run, "cells")[0]
        median = sorted(windows)[2]
        fvops.append(cells / (median / steps))
    assert fvops == pytest.approx(EXPECTED_FVOPS, rel=1e-12)


def test_counters_trace_and_topdown_are_kept_apart(imported: Path) -> None:
    _load(imported)
    session = get_db_session()
    l3, mpi_time, backend = [], [], []
    for size in ("xsmall", "small"):
        counter_runs = [
            r
            for r in _repetitions(session, size, "counters")
            if _metric(session, "AMDuProfPCM", r, "L3 Miss %")
        ]
        assert len(counter_runs) == 1  # only the first counter file is imported
        values = _metric(session, "AMDuProfPCM", counter_runs[0], "L3 Miss %")
        assert len(values) == 16  # one per CCX
        l3.append(statistics.fmean(values))

        (trace,) = _repetitions(session, size, "trace")
        times = _metric(session, "AMDuProfMPI", trace, "MPI Time(seconds)")
        assert len(times) == 128  # one per rank
        mpi_time.append(statistics.fmean(times))

        (topdown,) = _repetitions(session, size, "topdown")
        values = _metric(session, "AMDuProfPCM", topdown, "Backend_Bound.Memory")
        assert len(values) == 128
        backend.append(statistics.fmean(values))
    assert l3 == pytest.approx(EXPECTED_L3, rel=1e-12)
    assert mpi_time == pytest.approx(EXPECTED_MPI_MEAN_TIME, rel=1e-12)
    assert backend == pytest.approx(EXPECTED_BACKEND_MEMORY, rel=1e-12)


def test_loading_twice_does_not_duplicate(imported: Path) -> None:
    _load(imported)
    create_db(Namespace())
    session = get_db_session()
    assert len(session.execute(select(Repetition)).scalars().all()) == 14
    (run,) = _repetitions(session, "xsmall", "trace")
    assert len(_metric(session, "AMDuProfMPI", run, "MPI Time(seconds)")) == 128


def test_machine_info_flags_are_parsed(imported: Path) -> None:
    _load(imported)
    session = get_db_session()
    rows = session.execute(
        text(
            "SELECT DISTINCT smt_enabled_in_hw, smt_enabled_in_os, "
            "num_of_threads_sharing_l3 FROM AMDuProfPCM_machine_info"
        )
    ).all()
    assert rows == [(0, 0, 8)]


def test_analyses_match_the_original_script(imported: Path) -> None:
    """The registered analyses reproduce the numbers of the original script."""
    from quare.data_retriever import DataRetrieversManager

    _load(imported)
    settings = utils.load_settings()
    retriever = DataRetrieversManager.get_retriever("OpenFOAMlogs")
    ids = retriever.get_repetitions(
        settings["session_name_contains"],
        settings["machine_name"],
        settings["use_case_name"],
        settings["sizes_to_get"],
        "",
    )
    data = {
        key.name: values
        for key, values in retriever.get_analyses(
            ids, retriever.discover_analysis_keys([])
        ).items()
    }
    assert data["FVOPS"] == pytest.approx(EXPECTED_FVOPS, rel=1e-12)
    assert data["L3 miss ratio"] == pytest.approx(EXPECTED_L3, rel=1e-12)
    assert data["Backend Bound Memory"] == pytest.approx(
        EXPECTED_BACKEND_MEMORY, rel=1e-12
    )
    assert data["Frontend Bound"] == pytest.approx(EXPECTED_FRONTEND, rel=1e-12)
    assert data["Retiring"] == pytest.approx(EXPECTED_RETIRING, rel=1e-12)
    for name, expected in EXPECTED_L2.items():
        assert data[name] == pytest.approx(expected, rel=1e-12), name
    for kind, expected in EXPECTED_MPI_RATIO.items():
        assert data[f"MPI ratio ({kind})"] == pytest.approx(expected, rel=1e-12)


def test_plot_writes_summary(imported: Path) -> None:
    from quare.plot import plot

    _load(imported)
    plot(Namespace())
    out = imported / "output/Motorbike2024/GENOA_128/motorBike/analyses/OpenFOAMlogs"
    assert (out / "Summary.png").stat().st_size > 10_000
    assert (out / "Plot FVOPS | cells-s | run.png").exists()
