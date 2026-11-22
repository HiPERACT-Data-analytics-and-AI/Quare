"""Other platforms of the 2024 motorBike measurements (size ``xsmall``).

Covers a machine without top-down run (Rome), the 192-core platform and the
256-core platform, whose ``xsmall`` MPI trace comes from a different log
(``trace_logs`` in the mapping).  The expected numbers are the results of the
original scripts (``128_/192_/256_uProfAMD_AOCC.py``) on the same files.
"""

from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

import pytest

import quare.data_retriever as data_retriever
import quare.utils as utils
from quare.create_db import create_db
from quare.data_retriever import DataRetrieversManager
from quare.importers.motorbike2024 import import_motorbike_2024, load_mapping
from quare.preprocess import preprocess

ROOT = Path(__file__).parent
DATA = ROOT / "data" / "motorBike_2024"
EXAMPLE_MAPPING = ROOT.parent / "examples" / "motorbike_2024_import.json"

EXPECTED = {
    "ROME_128": {
        "FVOPS": 8093069.174757281,
        "L3 miss ratio": 9.35,
        "L2": [
            32.00978970482915,
            19.96816320546252,
            55.489783071857445,
            66.87481133806445,
            79.58832092326705,
            44.493269417005614,
        ],
        "MPI": [54.26454352441614, 94.5256916799363, 109.9471337579618],
    },
    "GENOA_192": {
        "FVOPS": 11226749.158249157,
        "L3 miss ratio": 24.040833333333335,
        "L2": [
            19.311518742353503,
            12.775748963101277,
            23.069610343130677,
            80.0427999165279,
            85.86265016441662,
            76.94940276472956,
        ],
        "MPI": [63.89768786127167, 84.64248855973024, 93.34277456647399],
        "BB": [55.477656249999995, 10.992916666666666, 20.865885416666668],
    },
    "BERGAMO_256": {
        "FVOPS": 10073548.33836858,
        "L3 miss ratio": 31.244375,
        "L2": [
            19.20981704030187,
            13.342754105069313,
            22.457817617968455,
            80.12683514601898,
            85.31574505089775,
            77.54493490288188,
        ],
        "MPI": [66.68582677165354, 90.55908382545931, 98.096062992126],
        "BB": [62.2871875, 9.944375, 16.3743359375],
    },
}
L2_NAMES = [
    "L2 miss ratio (total)",
    "L2 miss ratio from L1DC",
    "L2 miss ratio from HWPF",
    "L2 hit ratio (total)",
    "L2 hit ratio from L1DC",
    "L2 hit ratio from HWPF",
]


@pytest.fixture
def machine_db(request, tmp_path: Path):
    """Import one machine with the example mapping and build the database."""
    machine: str = request.param
    mapping = load_mapping(EXAMPLE_MAPPING)
    mapping["sizes"] = ["xsmall"]
    import_motorbike_2024(DATA, tmp_path / "raw_data", mapping, [machine])
    settings = {
        "raw_data_directory_path": "raw_data",
        "preprocessed_data_directory_path": "preprocessed_data",
        "db_path": "quare.sqlite3",
        "output_directory_path": "output",
        "task_sizes": {"xsmall": 167555},
        "metric_names": [],
        "analyses_names": [],
        "session_name_contains": mapping["session"],
        "machine_name": machine,
        "use_case_name": mapping["use_case"],
        "sizes_to_get": ["xsmall"],
    }
    (tmp_path / "settings.json").write_text(json.dumps(settings))

    def reset() -> None:
        utils.close_db_session()
        utils._settings_cache = None
        utils._settings_path_override = None
        data_retriever.DataRetrieversManager.retrievers.clear()

    reset()
    utils.set_settings_path(tmp_path / "settings.json")
    preprocess(Namespace())
    create_db(Namespace())
    yield machine
    reset()


@pytest.mark.parametrize(
    "machine_db", ["ROME_128", "GENOA_192", "BERGAMO_256"], indirect=True
)
def test_analyses_match_the_original_scripts(machine_db: str) -> None:
    expected = EXPECTED[machine_db]
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
        key.name: values[0]
        for key, values in retriever.get_analyses(
            ids, retriever.discover_analysis_keys([])
        ).items()
    }
    assert data["FVOPS"] == pytest.approx(expected["FVOPS"], rel=1e-12)
    assert data["L3 miss ratio"] == pytest.approx(expected["L3 miss ratio"], rel=1e-12)
    for name, value in zip(L2_NAMES, expected["L2"]):
        assert data[name] == pytest.approx(value, rel=1e-12), name
    mpi = [data[f"MPI ratio ({kind})"] for kind in ("min", "avg", "max")]
    assert mpi == pytest.approx(expected["MPI"], rel=1e-12)
    if "BB" in expected:
        top_down = [
            data[name]
            for name in ("Backend Bound Memory", "Frontend Bound", "Retiring")
        ]
        assert top_down == pytest.approx(expected["BB"], rel=1e-12)
    else:
        assert data["Backend Bound Memory"] is None


def test_comparison_plot_for_several_machines(tmp_path: Path) -> None:
    from quare.plot import plot

    mapping = load_mapping(EXAMPLE_MAPPING)
    mapping["sizes"] = ["xsmall"]
    machines = ["ROME_128", "GENOA_192"]
    import_motorbike_2024(DATA, tmp_path / "raw_data", mapping, machines)
    settings = {
        "raw_data_directory_path": "raw_data",
        "preprocessed_data_directory_path": "preprocessed_data",
        "db_path": "quare.sqlite3",
        "output_directory_path": "output",
        "task_sizes": {"xsmall": 167555},
        "metric_names": [],
        "analyses_names": [],
        "session_name_contains": mapping["session"],
        "machine_name": "ROME_128",
        "compare_machines": machines,
        "use_case_name": mapping["use_case"],
        "sizes_to_get": ["xsmall"],
    }
    (tmp_path / "settings.json").write_text(json.dumps(settings))
    utils.close_db_session()
    utils._settings_cache = None
    DataRetrieversManager.retrievers.clear()
    utils.set_settings_path(tmp_path / "settings.json")
    try:
        preprocess(Namespace())
        create_db(Namespace())
        plot(Namespace())
    finally:
        utils.close_db_session()
        utils._settings_cache = None
        utils._settings_path_override = None
        DataRetrieversManager.retrievers.clear()
    out = tmp_path / "output/Motorbike2024"
    assert (out / "motorBike/Comparison.png").stat().st_size > 10_000
