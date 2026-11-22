"""
Preprocessor for AMD uProf Timechart power traces.

Raw layout (one run per date directory), one file per node::

    <...>/<date>_power/AMDuProfTimechart/node1.csv   # timechart.csv of node 1
                                         node2.csv

The preprocessor merges the nodes of a run into ``run.power.csv``: one row per
sample, one column ``Node <n> power`` per node with the node power in watts
(package power of socket 0 plus socket 1, the last two columns of the
timechart records, as in the original ``en_info.py``).

Authors: Marcin Lawenda, Łukasz Szustak
"""

from __future__ import annotations

import re
from pathlib import Path

from ...preprocessor import Preprocessor

_NODE_FILE = re.compile(r"^node(\d+)\.csv$")


def read_node_power(path: Path) -> list[float]:
    """
    Node power timeline of a uProf ``timechart.csv`` in watts.

    The records follow the ``RecordId,Timestamp`` header; the node power is the
    sum of the last two columns (``socket0-package-power`` and
    ``socket1-package-power``).  Unparsable records are skipped.
    """
    power: list[float] = []
    started = False
    with open(path, encoding="utf-8") as stream:
        for raw in stream:
            line = raw.strip()
            if started:
                parts = line.split(",")
                if len(parts) >= 4:
                    try:
                        power.append(float(parts[-2]) + float(parts[-1]))
                    except ValueError:
                        continue
            if line.startswith("RecordId,Timestamp"):
                started = True
    return power


class AMDuProfTimechartPreprocessor(Preprocessor):
    """Merge the per-node timecharts of every run into ``run.power.csv``."""

    def preprocess(self) -> None:
        """Write ``run.power.csv`` next to the (not copied) raw node files."""
        for directory in self._raw_data_path.glob(f"**/{self.profiler_name}"):
            nodes = sorted(
                (int(m.group(1)), path)
                for path in directory.iterdir()
                if (m := _NODE_FILE.match(path.name))
            )
            if not nodes:
                continue
            target = (
                self._preprocessed_data_path / directory.relative_to(self._raw_data_path)
            ) / "run.power.csv"
            if target.exists():
                continue
            timelines = {n: read_node_power(path) for n, path in nodes}
            length = max(len(t) for t in timelines.values())
            target.parent.mkdir(parents=True, exist_ok=True)
            with open(target, "w", encoding="utf-8") as out:
                out.write("," + ",".join(f"Node {n} power" for n in timelines) + "\n")
                for i in range(length):
                    cells = [
                        repr(t[i]) if i < len(t) else "" for t in timelines.values()
                    ]
                    out.write(f"{i}," + ",".join(cells) + "\n")


__extension_data_preprocessor__: type[Preprocessor] = AMDuProfTimechartPreprocessor
