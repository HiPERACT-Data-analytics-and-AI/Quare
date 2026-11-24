"""Import and analyses of the UAP measurements (Rome subset, two sizes).

The expected numbers are the results of the original UAP scripts
(``uap_common.py``, ``fvops.py``, ``likwid.py``) run on the full files.
"""

from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

import pytest
from sqlalchemy import select

import quare.data_retriever as data_retriever
import quare.utils as utils
from quare.create_db import create_db
from quare.importers.uap import import_uap
from quare.models import Repetition
from quare.preprocess import preprocess
from quare.utils import get_db_session

DATA = Path(__file__).parent / "data" / "UAP"
MAPPING = {
    "session": "UAP",
    "use_case": "UAP",
    "sizes": ["uxlow", "ulow"],
    "machines": {"ROME_128": {"source": "Rome"}},
}
CELLS = {"uxlow": 36248, "ulow": 139937}

EXPECTED_FVOPS = [1914687.1252204587, 4809079.919678715]
EXPECTED_L3 = [9.9340625, 9.833125]
EXPECTED_L2 = {
    "L2 miss ratio (total)": [21.647816022733686, 22.944247490214085],
    "L2 miss ratio from L1DC": [19.595003894193326, 14.008925377710401],
    "L2 miss ratio from HWPF": [47.830380840688846, 49.40791523839202],
    "L2 hit ratio (total)": [77.93690523238674, 75.94912743227957],
    "L2 hit ratio from L1DC": [82.22084403034586, 85.65892793268492],
    "L2 hit ratio from HWPF": [52.169619159311154, 50.599875350576504],
}
# (min, mid-range, max) as get_mpi_ratio of fvops.py returns them
EXPECTED_MPI = {
    "min": [57.38369098712446, 54.28664079822617],
    "mid-range": [81.40227467811158, 75.10720620842572],
    "max": [105.42085836909871, 95.92777161862529],
}
EXPECTED_CLOCK = {
    "min": [2786.07, 2756.83],
    "max": [2817.78, 2795.3],
    "avg": [2805.41, 2777.09],
}
# simpleFoam values of likwid.get_volume_bandwidth: sum/avg volume, sum/avg bandwidth
EXPECTED_LIKWID = {
    "L2": {
        "data volume": ([8298.6978, 15020.7425], [64.8336, 117.3496]),
        "bandwidth": ([539999.5412, 685976.9265], [4218.7464, 5359.1947]),
    },
    "L3": {
        "data volume": ([2162.189, 4628.9362], [16.8921, 36.1636]),
        "bandwidth": ([131252.2621, 208913.5112], [1025.4083, 1632.1368]),
    },
    "Memory": {
        "data volume": ([4487.7398, 10936.2744], [35.0605, 85.4396]),
        "bandwidth": ([272616.1203, 474637.2296], [2129.8134, 3708.1034]),
    },
}


@pytest.fixture
def imported(tmp_path: Path):
    """Import the subset, write settings (with the UAP FVOPS runs) and reset."""
    import_uap(DATA, tmp_path / "raw_data", MAPPING)
    settings = {
        "raw_data_directory_path": "raw_data",
        "preprocessed_data_directory_path": "preprocessed_data",
        "db_path": "quare.sqlite3",
        "output_directory_path": "output",
        "task_sizes": CELLS,
        "metric_names": [],
        "analyses_names": [],
        "session_name_contains": "UAP",
        "machine_name": "ROME_128",
        "use_case_name": "UAP",
        "sizes_to_get": ["uxlow", "ulow"],
        "fvops_time_run": "1n2r",
        "fvops_steps_run": "1n4r",
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


def _analyses() -> dict[str, list]:
    from quare.data_retriever import DataRetrieversManager

    preprocess(Namespace())
    create_db(Namespace())
    settings = utils.load_settings()
    retriever = DataRetrieversManager.get_retriever("OpenFOAMlogs")
    ids = retriever.get_repetitions(
        settings["session_name_contains"],
        settings["machine_name"],
        settings["use_case_name"],
        settings["sizes_to_get"],
        "",
    )
    return {
        key.name: values
        for key, values in retriever.get_analyses(
            ids, retriever.discover_analysis_keys([])
        ).items()
    }


def test_import_counts_and_run_names(tmp_path: Path) -> None:
    counts = import_uap(DATA, tmp_path, MAPPING)
    assert counts == {"counters": 6, "topdown": 2, "trace": 2, "likwid": 2}
    base = tmp_path / "UAP/ROME_128/UAP/uxlow"
    names = sorted(p.name.split("_", 2)[2] for p in base.iterdir())
    assert names == [
        "counters-1n1r",
        "counters-1n2r",
        "counters-1n4r",
        "likwid",
        "topdown-1n5r",
        "trace-1n6r",
    ]
    (counter,) = (p for p in base.iterdir() if p.name.endswith("counters-1n4r"))
    assert (counter / "AMDuProfPCM/prof.AMD.mySimpleFoam.csv").exists()
    assert (counter / "OpenFOAMlogs/run.pimpleFoam.log").exists()
    with pytest.raises(ValueError):
        import_uap(DATA, tmp_path, MAPPING, ["NOPE_1"])


def test_all_runs_are_loaded(imported: Path) -> None:
    _analyses()
    assert len(get_db_session().execute(select(Repetition)).scalars().all()) == 12


def test_analyses_match_the_original_scripts(imported: Path) -> None:
    data = _analyses()
    assert data["FVOPS"] == pytest.approx(EXPECTED_FVOPS, rel=1e-12)
    assert data["L3 miss ratio"] == pytest.approx(EXPECTED_L3, rel=1e-12)
    for name, expected in EXPECTED_L2.items():
        assert data[name] == pytest.approx(expected, rel=1e-12), name
    for kind, expected in EXPECTED_MPI.items():
        key = "MPI ratio (mid-range)" if kind == "mid-range" else f"MPI ratio ({kind})"
        assert data[key] == pytest.approx(expected, rel=1e-12), kind
    for kind, expected in EXPECTED_CLOCK.items():
        assert data[f"Clock frequency ({kind})"] == pytest.approx(expected, rel=1e-12)
    for group, metrics in EXPECTED_LIKWID.items():
        for metric, (total, mean) in metrics.items():
            name = f"{group} {metric}"
            assert data[f"{name} (sum)"] == pytest.approx(total, rel=1e-12), name
            assert data[f"{name} (avg)"] == pytest.approx(mean, rel=1e-12), name


def test_fvops_without_run_selection_uses_the_median(imported: Path) -> None:
    """Without the UAP settings FVOPS is the median over the timing runs."""
    settings_path = imported / "settings.json"
    settings = json.loads(settings_path.read_text())
    del settings["fvops_time_run"], settings["fvops_steps_run"]
    settings_path.write_text(json.dumps(settings))
    utils._settings_cache = None
    data = _analyses()
    assert all(value is not None for value in data["FVOPS"])
    assert data["FVOPS"] != pytest.approx(EXPECTED_FVOPS, rel=1e-12)


def test_plot_writes_summary(imported: Path) -> None:
    from quare.plot import plot

    preprocess(Namespace())
    create_db(Namespace())
    plot(Namespace())
    out = imported / "output/UAP/ROME_128/UAP/analyses/OpenFOAMlogs"
    assert (out / "Summary.png").stat().st_size > 10_000
