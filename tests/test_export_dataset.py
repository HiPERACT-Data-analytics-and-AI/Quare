"""``export-dataset`` against a row of the real dataset of the study.

The expected line is the row ``xsmall / 2 nodes / 4 ranks per CCX`` of
``motorBike_InputData_ML_POWER_20_11.2026.csv`` (``build_dataset_power.py``).
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from quare.export_dataset import (
    APP_FEATURES,
    build_rows,
    dataset_name,
    hardware_key,
    load_cpu_table,
    write_csv,
    write_legacy,
)

from .test_motorbike_2026 import database  # noqa: F401

HEADER = (
    "size ; NODES ; CPUsPerNode ; platform ; arch ; cores ; ccd ; ccx ; "
    "ccx_per_ccd ; cores_per_ccx ; cores_per_ccd ; totalL3 ; L3PerCore ; "
    "L3_per_ccd ; L3_per_ccx ; L1I ; L1D ; L2 ; mc ; DDR ; MTps ; mbw ; "
    "mbwPerCore ; NPS ; fBase ; fBoostAll ; TDP ; ranksPerCCX ; ranks ; cells ; "
    "cellsPerRank ; totalTime ; firstStepTime ; allStepsTime ; allStepsTime_m1 ; "
    "lenSteps ; avgOneSetepTime ; CVOPTS ; aggregateAllNodesPower ; "
    "aggregateMPIvolume ; avgCoreMPIvolume ; CPI (Sys + User) ; DC Access (pti) ; "
    "L2 Access (pti) ; L2 Access from IC Miss (pti) ; "
    "L2 Access from DC Miss (pti) ; L2 Miss (pti) ; L2 Miss from IC Miss (pti) ; "
    "L2 Miss from DC Miss (pti) ; L2 Hit (pti) ; L2 Hit from IC Miss (pti) ; "
    "L2 Hit from DC Miss (pti) ; L3 Miss % ; \n"
)
ROW = (
    "xsmall ; 2 ; 2 ; GENOA_9654_96c_2026_2_nodes_4MPICCX ;      Zen 4 (Genoa) ; "
    "96 ; 12 ; 12 ; 1 ; 8 ; 8 ; 384 ; 4.0 ; 32 ; 32 ; 32 ; 32 ; 1.0 ; 12 ; DDR5 ; "
    "4800 ; 460.8 ; 4.8 ; 4 ; 2.4 ; 3.5 ; 360 ; 4 ; 192 ; 167555 ; 872.68 ; "
    "7.862718932 ; 0.3 ; 5.41 ; 5.11 ; 200 ; 0.025678391959798996 ; "
    "33984.99412915851 ; 1354.4771153846154 ; 73.38815807600001 ; "
    "0.38222998997916674 ; 0.3 ; 567.91 ; 6.25 ; 1.22 ; 3.79 ; 1.51 ; 0.45 ; "
    "0.51 ; 4.7 ; 0.77 ; 3.24 ; 19.6 ; \n"
)


def test_names_and_hardware_lookup() -> None:
    table = load_cpu_table()
    assert hardware_key("GENOA_9654", table) == "GENOA_9654_96c"
    assert hardware_key("TURIN_9965", table) == "TURIN_9965_192c"
    assert hardware_key("NOPE", table) is None
    assert dataset_name("GENOA_9654_96c", 1, 4) == "GENOA_9654_96c_2026_1_node_4MPICCX"
    assert dataset_name("GENOA_9654_96c", 4, 12) == (
        "GENOA_9654_96c_2026_4_nodes_12MPICCX"
    )


def test_legacy_file_equals_the_original_row(database: Path) -> None:  # noqa: F811
    header, rows = build_rows(["xsmall"], "Motorbike2026", "motorBike")
    target = database / "dataset.csv"
    write_legacy(header, rows, target)
    assert target.read_text(encoding="utf-8") == HEADER + ROW + "\n"


def test_options_and_csv_style(database: Path) -> None:  # noqa: F811
    header, rows = build_rows(["xsmall"], "Motorbike2026", "motorBike", with_power=False)
    assert "aggregateAllNodesPower" not in header
    header, rows = build_rows(
        ["xsmall"],
        "Motorbike2026",
        "motorBike",
        power_features=["aggregateAllNodesEnergy", "avgNodesPower"],
    )
    assert header[header.index("CVOPTS") + 1 :][:2] == [
        "aggregateAllNodesEnergy",
        "avgNodesPower",
    ]
    row = dict(zip(header, rows[0]))
    assert row["aggregateAllNodesEnergy"] == pytest.approx(0.001997853745192308)
    assert row["avgNodesPower"] == pytest.approx(677.2385576923077)
    assert [row[f] for f in APP_FEATURES][:3] == [192, 167555, 872.68]
    target = database / "dataset_plain.csv"
    write_csv(header, rows, target)
    with open(target, newline="") as stream:
        table = list(csv.reader(stream))
    assert table[1][table[0].index("arch")] == "Zen 4 (Genoa)"
    assert len(table) == 2


def test_command_line(database: Path, monkeypatch) -> None:  # noqa: F811
    from quare.__main__ import main

    target = database / "cli.csv"
    monkeypatch.setattr(
        "sys.argv",
        [
            "quare",
            "export-dataset",
            "--config",
            str(database / "settings.json"),
            "--output",
            str(target),
            "--no-power",
        ],
    )
    main()
    lines = target.read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith("size ; NODES ; CPUsPerNode ; platform ;")
    assert "aggregateAllNodesPower" not in lines[0]
    assert lines[1].startswith("xsmall ; 2 ; 2 ; GENOA_9654_96c_2026_2_nodes_4MPICCX ;")
