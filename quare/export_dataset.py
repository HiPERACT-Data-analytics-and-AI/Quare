"""
``export-dataset`` subcommand: build the machine-learning input table of the
OpenFOAM motorBike study from the Quare database.

One row is one run configuration (platform, number of nodes, MPI ranks per
CCX) and one mesh size.  The columns are those of the dataset scripts of the
study (``build_dataset.py`` / ``build_dataset_power.py``):

* identification: ``size``, ``NODES``, ``CPUsPerNode``, ``platform``;
* hardware of one CPU (``quare/data/cpu_features.json``, from ``cpu_info.py``);
* ``ranksPerCCX`` and the application features of
  :meth:`~quare.extensions.OpenFOAMlogs_ext.plotter.OpenFOAMAnalyzer.timing_record`
  (``app_info.py``);
* power features (``en_info.py``), left out with ``--no-power``;
* MPI volume (``mpi_info.py``);
* AMD uProf PCM counters of the whole system (``uProf_info.py``).

The machines of the database must be named
``<platform>_<N>N_<C>PCCX_<R>`` (see :mod:`quare.importers.motorbike2026`)
with ``<platform>`` the hardware key without the core suffix, for example
``GENOA_9654`` for ``GENOA_9654_96c``.  The dataset name of a row is
``<hardware key>_2026_<N>_node(s)_<C>MPICCX``.

The default output style ``legacy`` reproduces the files of the original
scripts exactly (fields followed by `` ; ``, padded ``arch`` strings); the
style ``csv`` is a plain comma-separated file.

Usage::

    quare export-dataset --output dataset.csv [--no-power] [--style csv]

Authors: Marcin Lawenda, Łukasz Szustak
"""

from __future__ import annotations

import csv
import json
import re
from argparse import ArgumentParser, Namespace
from pathlib import Path

from sqlalchemy import select

from .data_retriever import DataRetrieversManager
from .models import Machine
from .utils import get_db_session, load_settings

CPU_FEATURES_PATH = Path(__file__).parent / "data" / "cpu_features.json"
"""Hardware table shipped with Quare."""

CPU_FEATURES = [
    "arch", "cores", "ccd", "ccx", "ccx_per_ccd", "cores_per_ccx",
    "cores_per_ccd", "totalL3", "L3PerCore", "L3_per_ccd", "L3_per_ccx",
    "L1I", "L1D", "L2", "mc", "DDR", "MTps", "mbw", "mbwPerCore", "NPS",
    "fBase", "fBoostAll", "TDP",
]  # fmt: skip
APP_FEATURES = [
    "ranks", "cells", "cellsPerRank", "totalTime", "firstStepTime",
    "allStepsTime", "allStepsTime_m1", "lenSteps", "avgOneSetepTime", "CVOPTS",
]  # fmt: skip
POWER_FEATURES = {
    "aggregateAllNodesPower": "sum",
    "aggregateAllNodesEnergy": "energy",
    "avgNodesPower": "mean",
}
"""Power features and the ``kind`` of ``OpenFOAMAnalyzer.power_value``."""
DEFAULT_POWER_FEATURES = ["aggregateAllNodesPower"]
MPI_FEATURES = {"aggregateMPIvolume": False, "avgCoreMPIvolume": True}
UPROF_FEATURES = [
    "CPI (Sys + User)", "DC Access (pti)", "L2 Access (pti)",
    "L2 Access from IC Miss (pti)", "L2 Access from DC Miss (pti)",
    "L2 Miss (pti)", "L2 Miss from IC Miss (pti)", "L2 Miss from DC Miss (pti)",
    "L2 Hit (pti)", "L2 Hit from IC Miss (pti)", "L2 Hit from DC Miss (pti)",
    "L3 Miss %",
]  # fmt: skip

_MACHINE = re.compile(
    r"^(?P<platform>.+)_(?P<nodes>\d+)N_(?P<ccx>\d+)PCCX_(?P<ranks>\d+)$"
)


def load_cpu_table(path: Path = CPU_FEATURES_PATH) -> dict:
    """Read the hardware table (``platforms``, ``export_order``, ...)."""
    return json.loads(path.read_text(encoding="utf-8"))


def hardware_key(platform: str, table: dict) -> str | None:
    """Hardware key of a platform name (``GENOA_9654`` -> ``GENOA_9654_96c``)."""
    for key in table["platforms"]:
        if key.startswith(platform + "_"):
            return key
    return None


def dataset_name(key: str, nodes: int, ccx: int) -> str:
    """Platform name of a dataset row, e.g. ``GENOA_9654_96c_2026_2_nodes_4MPICCX``."""
    node_text = "1_node" if nodes == 1 else f"{nodes}_nodes"
    return f"{key}_2026_{node_text}_{ccx}MPICCX"


def build_rows(
    sizes: list[str],
    session_contains: str,
    use_case: str,
    with_power: bool = True,
    power_features: list[str] | None = None,
    table: dict | None = None,
) -> tuple[list[str], list[list]]:
    """
    Build the header and the rows of the dataset from the database.

    :param sizes: Mesh size names, in the order of the rows of a configuration.
    :param session_contains: Substring of the profiling session name.
    :param use_case: Use case name.
    :param with_power: Include the power features.
    :param power_features: Power features to include (keys of
        :data:`POWER_FEATURES`); default ``aggregateAllNodesPower``.
    :param table: Hardware table; the shipped one by default.
    :returns: ``(header, rows)``.  Machines that cannot be parsed or have no
        hardware entry are skipped; missing values are ``None``.
    """
    table = table or load_cpu_table()
    power_features = power_features or DEFAULT_POWER_FEATURES
    unknown = [f for f in power_features if f not in POWER_FEATURES]
    if unknown:
        raise ValueError(f"unknown power feature: {', '.join(unknown)}")
    retriever = DataRetrieversManager.get_retriever("OpenFOAMlogs")
    from .extensions.OpenFOAMlogs_ext.plotter import OpenFOAMAnalyzer

    assert isinstance(retriever, OpenFOAMAnalyzer)

    order = {key: i for i, key in enumerate(table["export_order"])}
    configurations = []
    for machine in get_db_session().execute(select(Machine.name)).scalars():
        match = _MACHINE.match(machine)
        key = hardware_key(match["platform"], table) if match else None
        if match is None or key is None:
            continue
        configurations.append(
            (
                order.get(key, len(order)),
                key,
                int(match["nodes"]),
                int(match["ccx"]),
                machine,
            )
        )
    configurations.sort()

    header = (
        ["size", "NODES", "CPUsPerNode", "platform"]
        + CPU_FEATURES
        + ["ranksPerCCX"]
        + APP_FEATURES
        + (power_features if with_power else [])
        + list(MPI_FEATURES)
        + UPROF_FEATURES
    )
    rows: list[list] = []
    for _, key, nodes, ccx, machine in configurations:
        hardware = table["platforms"][key]
        ids = retriever.get_repetitions(session_contains, machine, use_case, sizes, "")
        for size in sizes:
            run_ids = ids[size]
            record = retriever.timing_record(run_ids) or {}
            counters = retriever.pcm_features(run_ids, UPROF_FEATURES) or {}
            row: list = [
                size,
                nodes,
                table["sockets_per_node"],
                dataset_name(key, nodes, ccx),
                *[hardware[f] for f in CPU_FEATURES],
                ccx,
                *[record.get(f) for f in APP_FEATURES],
            ]
            if with_power:
                row += [
                    retriever.power_value(run_ids, POWER_FEATURES[f])
                    for f in power_features
                ]
            row += [
                retriever.volume_value(run_ids, per_rank)
                for per_rank in MPI_FEATURES.values()
            ]
            row += [counters.get(f) for f in UPROF_FEATURES]
            rows.append(row)
    return header, rows


def write_legacy(header: list[str], rows: list[list], path: Path) -> None:
    """Write the table as the original scripts print it (`` ; `` after every field)."""

    def line(fields: list) -> str:
        return "".join(f"{'' if x is None else x} ; " for x in fields) + "\n"

    # the scripts print the table with print(), which adds one more newline
    path.write_text(
        line(header) + "".join(line(row) for row in rows) + "\n", encoding="utf-8"
    )


def write_csv(header: list[str], rows: list[list], path: Path) -> None:
    """Write a plain comma-separated file (``arch`` without padding)."""
    arch = header.index("arch") if "arch" in header else None
    with open(path, "w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(header)
        for row in rows:
            writer.writerow(
                [
                    v.strip() if i == arch and isinstance(v, str) else v
                    for i, v in enumerate(row)
                ]
            )


def add_arguments(parser: ArgumentParser) -> None:
    """Register the arguments of ``export-dataset``."""
    parser.add_argument("--output", type=Path, required=True, help="output file")
    parser.add_argument(
        "--no-power", action="store_true", help="leave out the power features"
    )
    parser.add_argument(
        "--power-feature",
        action="append",
        choices=sorted(POWER_FEATURES),
        help="power feature to include (repeatable; default: aggregateAllNodesPower)",
    )
    parser.add_argument(
        "--style",
        choices=["legacy", "csv"],
        default="legacy",
        help="legacy: exactly as the original scripts; csv: plain CSV",
    )


def export_dataset(args: Namespace) -> None:
    """
    Run the export with the settings of the active settings file.

    The rows are the sizes of ``sizes_to_get`` of every machine of the session
    ``session_name_contains`` and use case ``use_case_name``.
    """
    settings = load_settings()
    header, rows = build_rows(
        settings["sizes_to_get"],
        settings["session_name_contains"],
        settings["use_case_name"],
        with_power=not args.no_power,
        power_features=args.power_feature,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    (write_csv if args.style == "csv" else write_legacy)(header, rows, args.output)
    print(f"Wrote {len(rows)} rows to {args.output}")
