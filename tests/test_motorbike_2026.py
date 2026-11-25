"""Import and analyses of the 2026 multi-node motorBike data (Genoa 2 nodes).

The expected numbers are the results of the dataset scripts of the original
study (``app_info.py``, ``en_info.py``, ``mpi_info.py``, ``uProf_info.py``) on
the same files.
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
from quare.importers.motorbike2026 import (
    find_configurations,
    import_motorbike_2026,
    load_mapping,
)
from quare.models import Machine
from quare.preprocess import preprocess
from quare.utils import get_db_session

ROOT = Path(__file__).parent
DATA = ROOT / "data" / "motorBike_2026"
MAPPING = ROOT.parent / "examples" / "motorbike_2026_import.json"
MACHINE = "GENOA_9654_2N_4PCCX_192"

EXPECTED = {
    "CVOPTS": 33984.99412915851,
    "Aggregate node power": 1354.4771153846154,
    "Average node power": 677.2385576923077,
    "Aggregate energy": 0.001997853745192308,
    "MPI volume (aggregate)": 73.38815807600001,
    "MPI volume (per rank)": 0.38222998997916674,
    "L3 miss ratio": 19.6,
}


@pytest.fixture
def database(tmp_path: Path):
    mapping = load_mapping(MAPPING)
    mapping["sizes"] = ["xsmall"]
    import_motorbike_2026(DATA, tmp_path / "raw_data", mapping)
    settings = {
        "raw_data_directory_path": "raw_data",
        "preprocessed_data_directory_path": "preprocessed_data",
        "db_path": "quare.sqlite3",
        "output_directory_path": "output",
        "task_sizes": {"xsmall": 167555},
        "metric_names": [],
        "analyses_names": [],
        "session_name_contains": mapping["session"],
        "machine_name": MACHINE,
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
    yield tmp_path
    reset()


def test_configurations_are_named_after_nodes_and_ranks_per_ccx() -> None:
    mapping = load_mapping(MAPPING)
    found = find_configurations(DATA, "GENOA_9654", mapping["platforms"]["GENOA_9654"])
    assert list(found) == [MACHINE]
    assert found[MACHINE][1] == {"nodes": 2, "ranks": 192, "per_node": 96, "ccx": 4}


def test_import_roles_and_unknown_machine(tmp_path: Path) -> None:
    mapping = load_mapping(MAPPING)
    mapping["sizes"] = ["xsmall"]
    counts = import_motorbike_2026(DATA, tmp_path, mapping)
    # two timing runs (power and MPI logs are excluded from the timing runs)
    assert counts == {"counters": 2, "topdown": 1, "trace": 1, "power": 1}
    runs = sorted(p.name for p in (tmp_path / "Motorbike2026" / MACHINE).rglob("*_*"))
    assert sorted(r[16:] for r in runs if r[:8].isdigit()) == [
        "counters",
        "counters",
        "power",
        "topdown",
        "trace",
    ]
    nodes = tmp_path.rglob("AMDuProfTimechart/node*.csv")
    assert sorted(p.name for p in nodes) == ["node1.csv", "node2.csv"]
    with pytest.raises(ValueError, match="not found"):
        import_motorbike_2026(DATA, tmp_path, mapping, ["GENOA_9654_9N_1PCCX_9"])


def test_machine_has_the_rank_count_as_core_count(database: Path) -> None:
    machine = get_db_session().query(Machine).one()
    assert (machine.name, machine.num_of_cores) == (MACHINE, 192)


def test_analyses_match_the_dataset_scripts(database: Path) -> None:
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
    for name, expected in EXPECTED.items():
        assert data[name] == pytest.approx(expected, rel=1e-12), name
    # system aggregates of the top-down counters (not the mean over cores)
    assert data["Backend Bound Memory"] == pytest.approx(24.29)
    assert data["Frontend Bound"] == pytest.approx(10.64)
    assert data["Retiring"] == pytest.approx(58.12)
    assert data["L2 miss ratio (total)"] == pytest.approx(1.51 / 6.25 * 100)
    assert data["FVOPS"] > 0
    assert data["Time stepping time"] > 0
    # lower median of the two timing runs (7.86 s and 11.16 s)
    assert data["Total time"] == pytest.approx(7.862718932)
