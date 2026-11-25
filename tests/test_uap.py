"""Import and analyses of the UAP measurements (Rome subset, two sizes).

The expected numbers are the results of the original UAP scripts
(``uap_common.py``, ``fvops.py``, ``likwid.py``) run on the full files.
"""

from __future__ import annotations

import csv
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
# likwid.get_volume_bandwidth / get_clock of the original scripts for pimpleFoam
EXPECTED_PIMPLE_CLOCK = {
    "min": [2751.18, 2715.22],
    "max": [2781.76, 2746.77],
    "avg": [2767.23, 2731.46],
}
EXPECTED_PIMPLE_LIKWID = {
    "L2": {
        "data volume": ([28295.0504, 51752.0428], [221.0551, 404.3128]),
        "bandwidth": ([838481.2085, 1006827.0], [6550.6344, 7865.8355]),
    },
    "L3": {
        "data volume": ([9679.2918, 19991.5685], [75.6195, 156.1841]),
        "bandwidth": ([290114.3507, 412079.0641], [2266.5184, 3219.3677]),
    },
    "Memory": {
        "data volume": ([15282.8372, 38152.3555], [119.3972, 298.0653]),
        "bandwidth": ([453670.9968, 779913.8283], [3544.3047, 6093.0768]),
    },
}


@pytest.fixture
def imported(tmp_path: Path):
    """Import the subset, write settings (with the UAP FVOPS runs) and reset."""
    yield from _prepare(tmp_path, MAPPING, "ROME_128")


def _prepare(tmp_path: Path, mapping: dict, machine: str):
    import_uap(DATA, tmp_path / "raw_data", mapping)
    settings = {
        "raw_data_directory_path": "raw_data",
        "preprocessed_data_directory_path": "preprocessed_data",
        "db_path": "quare.sqlite3",
        "output_directory_path": "output",
        "task_sizes": CELLS,
        "metric_names": [],
        "analyses_names": [],
        "session_name_contains": "UAP",
        "machine_name": machine,
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
    assert counts == {
        "counters": 6,
        "topdown": 2,
        "trace": 2,
        "likwid": 2,
        "likwid-pimpleFoam": 2,
        "profile": 0,
    }
    base = tmp_path / "UAP/ROME_128/UAP/uxlow"
    names = sorted(p.name.split("_", 2)[2] for p in base.iterdir())
    assert names == [
        "counters-1n1r",
        "counters-1n2r",
        "counters-1n4r",
        "likwid",
        "likwid-pimpleFoam",
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
    assert len(get_db_session().execute(select(Repetition)).scalars().all()) == 14


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


def test_pimplefoam_likwid_equals_the_scripts(imported: Path) -> None:
    data = _analyses()
    for kind, expected in EXPECTED_PIMPLE_CLOCK.items():
        name = f"pimpleFoam Clock frequency ({kind})"
        assert data[name] == pytest.approx(expected, rel=1e-12), name
    for group, metrics in EXPECTED_PIMPLE_LIKWID.items():
        for metric, (total, mean) in metrics.items():
            name = f"pimpleFoam {group} {metric}"
            assert data[f"{name} (sum)"] == pytest.approx(total, rel=1e-12), name
            assert data[f"{name} (avg)"] == pytest.approx(mean, rel=1e-12), name
            # the simpleFoam values are not touched by the second run
            assert data[f"{group} {metric} (sum)"] != pytest.approx(total)


# mpi_summary.py on the test files (uxlow, ulow)
EXPECTED_MPI_TIME = {
    "min": [6.6852, 9.79331],
    "avg": [10.06824390625, 14.758967265625],
    "max": [12.28153, 17.30537],
}
EXPECTED_MPI_SHARE = {
    "MPI_Isend": [5.62609, 4.99755],
    "MPI_Irecv": [1.07149, 0.92435],
    "MPI_Waitall": [17.04519, 23.44336],
    "MPI_Scatter": [0.33444, 0.54413],
    "MPI_Allreduce": [45.49732, 46.19599],
}
EXPECTED_MPI_VOLUME = [84.374559262, 168.007151042]


def test_mpi_summary_analyses_equal_the_script(imported: Path) -> None:
    data = _analyses()
    for kind, expected in EXPECTED_MPI_TIME.items():
        assert data[f"MPI time ({kind})"] == pytest.approx(expected, rel=1e-12)
    for call, expected in EXPECTED_MPI_SHARE.items():
        assert data[f"{call} share of MPI time"] == pytest.approx(expected, rel=1e-12)
    assert data["MPI volume (aggregate)"] == pytest.approx(EXPECTED_MPI_VOLUME)
    # pti.py --mpi: (MPI_Recv + MPI_Irecv) / steps / cells / cores
    assert data["MPI receive volume per cell"] == pytest.approx(
        [15.067317387913358, 7.792616644565948], rel=1e-12
    )


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


def test_dateless_runs_get_unique_names_across_sizes(tmp_path: Path) -> None:
    """Runs without a date in the log must not share a repetition name."""
    from datetime import datetime

    from quare.importers.motorbike2024 import _RunWriter

    used: set[str] = set()
    fallback = datetime(2024, 1, 1)
    first = _RunWriter(tmp_path / "uxlow", used).run_dir(None, "trace-1n6r", fallback)
    second = _RunWriter(tmp_path / "ulow", used).run_dir(None, "trace-1n6r", fallback)
    assert first.name != second.name


# timing_comp.py (sorted windows of the five runs) and pti.get_metrics on the
# full files of the subset, mean over cores
EXPECTED_WINDOWS = {
    "simpleFoam": [
        [9.97, 11.27, 11.34, 11.37, 11.48],
        [16.48, 17.19, 17.3, 17.43, 17.84],
    ],
    "pimpleFoam": [
        [25.08, 25.49, 26.46, 27.26, 28.34],
        [37.94, 40.22, 40.86, 41.07, 42.33],
    ],
}
EXPECTED_PTI = {
    "L2 Access (pti)": [12.453984375, 16.505703125],
    "L2 Miss (pti)": [2.696015625, 3.787109375],
    "L2 Hit from DC Miss (pti)": [4.453671875, 7.857734375],
}


def test_solver_times_and_pti_equal_the_scripts(imported: Path) -> None:
    from quare.data_retriever import DataRetrieversManager
    from quare.extensions.OpenFOAMlogs_ext.plotter import OpenFOAMAnalyzer

    _analyses()
    retriever = DataRetrieversManager.get_retriever("OpenFOAMlogs")
    assert isinstance(retriever, OpenFOAMAnalyzer)
    ids = retriever.get_repetitions("UAP", "ROME_128", "UAP", ["uxlow", "ulow"], "")
    for solver, expected in EXPECTED_WINDOWS.items():
        found = [retriever.solver_times(i, solver) for i in ids.values()]
        for per_size, wanted in zip(found, expected):
            assert per_size == pytest.approx(wanted, abs=1e-6), solver
    values = [retriever.pti_values(i) for i in ids.values()]
    for name, expected in EXPECTED_PTI.items():
        assert [v[name] for v in values] == pytest.approx(expected, rel=1e-12), name


def test_pti_series_keeps_the_counters_above_two() -> None:
    from quare.extensions.OpenFOAMlogs_ext.figures import pti_series

    series = pti_series(
        [
            {"DC Access (pti)": 540.0, "A (pti)": 3.0, "B (pti)": 1.0},
            {"DC Access (pti)": 551.0, "A (pti)": 4.0, "B (pti)": 2.0},
        ]
    )
    assert series == {"A (pti)": [3.0, 4.0]}


def test_machine_figures_are_written(imported: Path) -> None:
    from quare.plot import plot

    settings_path = imported / "settings.json"
    settings = json.loads(settings_path.read_text())
    settings["compare_machines"] = ["ROME_128"]
    settings["pti_sizes"] = ["uxlow", "ulow"]
    settings["comparison_series"] = ["L3 miss ratio", "MPI ratio (mid-range)"]
    settings_path.write_text(json.dumps(settings))
    utils._settings_cache = None
    preprocess(Namespace())
    create_db(Namespace())
    plot(Namespace())
    folder = imported / "output/UAP/UAP"
    for name in (
        "Comparison",
        "Solver timing comparison",
        "LIKWID L2",
        "LIKWID L3",
        "LIKWID Memory",
        "Clock frequency",
        "Clock frequency pimpleFoam",
        "PTI",
        "PTI MPI volume",
    ):
        assert (folder / f"{name}.png").stat().st_size > 5_000, name
    rows = {
        name: list(csv.reader((folder / f"{name}.csv").open()))
        for name in ("MPI time", "MPI calls", "MPI volume")
    }
    # the formats of mpi_summary.py: two decimals
    assert rows["MPI time"][1][1:4] == ["6.69", "10.07", "12.28"]
    assert rows["MPI calls"][-1][1:] == ["MPI_Allreduce", "45.50", "46.20"]
    assert rows["MPI volume"][1][1:] == ["84.37", "168.01"]


# rank MPI times of the trace run divided by the Total Time of its log
EXPECTED_MPI_TOTAL_TIME = {
    "min": [36.68286394943057, 37.41742988929501],
    "mid-range": [52.03688566950751, 51.76814371200549],
    "max": [67.39090738958447, 66.11885753471596],
}


def _change_settings(path: Path, **values: str) -> None:
    settings = json.loads((path / "settings.json").read_text())
    settings.update(values)
    (path / "settings.json").write_text(json.dumps(settings))
    utils._settings_cache = None


def test_mpi_ratio_basis_total_time(imported: Path) -> None:
    _change_settings(imported, mpi_ratio_basis="total_time")
    data = _analyses()
    for kind, expected in EXPECTED_MPI_TOTAL_TIME.items():
        key = "MPI ratio (mid-range)" if kind == "mid-range" else f"MPI ratio ({kind})"
        assert data[key] == pytest.approx(expected, rel=1e-12), kind
        assert all(value < 100 for value in data[key])


def test_unknown_basis_is_rejected(imported: Path) -> None:
    _change_settings(imported, mpi_ratio_basis="wall")
    with pytest.raises(ValueError, match="mpi_ratio_basis"):
        _analyses()


def test_median_of_even_runs() -> None:
    from quare.extensions.OpenFOAMlogs_ext.comparison import median_run

    assert median_run([4.0, 1.0, 3.0, 2.0]) == 2.0
    assert median_run([4.0, 1.0, 3.0, 2.0], "average") == 2.5
    assert median_run([5.0, 1.0, 3.0], "average") == 3.0
    assert median_run([]) is None
    with pytest.raises(ValueError):
        median_run([1.0], "upper")


def test_average_median_equals_the_scripts_for_odd_runs(imported: Path) -> None:
    """The three timing runs of the subset: the setting changes nothing."""
    _change_settings(imported, median_of_even_runs="average")
    del_keys = json.loads((imported / "settings.json").read_text())
    for key in ("fvops_time_run", "fvops_steps_run"):
        del_keys.pop(key)
    (imported / "settings.json").write_text(json.dumps(del_keys))
    utils._settings_cache = None
    with_average = _analyses()["FVOPS"]
    _change_settings(imported, median_of_even_runs="lower")
    assert with_average == pytest.approx(_analyses()["FVOPS"], rel=1e-12)


MILANX = {**MAPPING, "machines": {"MILANX_128": {"source": "MilanX"}}}


@pytest.fixture
def milanx(tmp_path: Path):
    """The MilanX profiling runs (30 steps of ``uxlow`` and ``ulow``)."""
    yield from _prepare(tmp_path, MILANX, "MILANX_128")


# parse_profile of mpi_profiling.py on the test logs:
# (steps, reduce entries, sum of reduce, sum of all-all, last step time)
EXPECTED_PROFILE = {
    "uxlow": (30, 29, 5.098046875, 3.49, 0.87),
    "ulow": (30, 29, 10.097265625, 7.05328125, 1.64),
}


def test_mpi_profile_runs_equal_the_script(milanx: Path) -> None:
    from quare.extensions.OpenFOAMlogs_ext.plotter import TAG_TIMING, OpenFOAMAnalyzer

    preprocess(Namespace())
    create_db(Namespace())
    retriever = data_retriever.DataRetrieversManager.get_retriever("OpenFOAMlogs")
    assert isinstance(retriever, OpenFOAMAnalyzer)
    ids = retriever.get_repetitions("UAP", "MILANX_128", "UAP", ["uxlow", "ulow"], "")
    for size, (
        steps,
        reduce_n,
        reduce_sum,
        all_all_sum,
        last,
    ) in EXPECTED_PROFILE.items():
        # the profiling runs are not timing runs
        assert retriever._with_tag(ids[size], TAG_TIMING) == []
        profile = retriever.mpi_profile(ids[size])
        assert profile is not None
        assert (len(profile["steps"]), len(profile["reduce"])) == (steps, reduce_n)
        assert sum(profile["reduce"]) == pytest.approx(reduce_sum, rel=1e-12)
        assert sum(profile["all-all"]) == pytest.approx(all_all_sum, rel=1e-12)
        assert profile["steps"][-1] == pytest.approx(last)
        assert profile["steps"] == sorted(profile["steps"])


def test_mpi_profile_plot_is_written(milanx: Path) -> None:
    from quare.extensions.OpenFOAMlogs_ext.plotter import OpenFOAMPlotter

    _change_settings(milanx, compare_machines=["MILANX_128"])
    preprocess(Namespace())
    create_db(Namespace())
    OpenFOAMPlotter("OpenFOAMlogs").make_all()
    assert (milanx / "output/UAP/UAP/MPI profile MILANX_128.png").stat().st_size > 5_000


def test_profile_runs_are_imported_and_do_not_count_as_timing(tmp_path: Path) -> None:
    counts = import_uap(DATA, tmp_path / "raw_data", MILANX)
    assert counts["profile"] == 4
    names = sorted(p.name for p in (tmp_path / "raw_data").rglob("*_profile*"))
    assert len(names) == 4 and sum(n.endswith("profile-end") for n in names) == 2
