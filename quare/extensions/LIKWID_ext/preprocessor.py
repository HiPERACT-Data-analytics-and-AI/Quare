"""
Preprocessor for LIKWID (``likwid-perfctr``) output.

Raw layout, one run per date directory, one text file per counter group::

    <...>/<date>_likwid/LIKWID/L2.txt     # likwid-perfctr output, group L2
                              L3.txt
                              NUMA.txt

The preprocessor merges the files of a run into ``run.stat.csv`` with the
columns ``group,metric,sum,min,max,avg``.  Only the ``STAT`` rows of the
metric tables (``| Metric | Sum | Min | Max | Avg |``) are kept, as in the
original scripts; the per-thread tables and the raw event tables are not used.
The group name is taken from the ``Group <n>: <name>`` line, or from the file
name when the line is missing.

Authors: Marcin Lawenda, Łukasz Szustak
"""

from __future__ import annotations

import re
from pathlib import Path

from ...preprocessor import Preprocessor

_GROUP = re.compile(r"^Group\s+\d+:\s*(\S+)")
STAT_SUFFIX = " STAT"


def read_stat_rows(path: Path) -> tuple[str, list[tuple[str, list[float]]]]:
    """
    Group name and metric ``STAT`` rows of one LIKWID output file.

    :returns: ``(group, [(metric, [sum, min, max, avg]), ...])``.  Rows of the
        event tables have a counter column and are skipped.
    """
    group = path.stem
    rows: list[tuple[str, list[float]]] = []
    with open(path, encoding="utf-8", errors="replace") as stream:
        for raw in stream:
            match = _GROUP.match(raw)
            if match:
                group = match.group(1)
                continue
            if not raw.startswith("|"):
                continue
            cells = [cell.strip() for cell in raw.strip().strip("|").split("|")]
            if len(cells) != 5 or not cells[0].endswith(STAT_SUFFIX):
                continue
            try:
                numbers = [float(cell) for cell in cells[1:]]
            except ValueError:
                continue
            rows.append((cells[0][: -len(STAT_SUFFIX)].strip(), numbers))
    return group, rows


class LIKWIDPreprocessor(Preprocessor):
    """Merge the group files of every run into ``run.stat.csv``."""

    def preprocess(self) -> None:
        """Write ``run.stat.csv`` next to the (not copied) raw group files."""
        for directory in sorted(self._raw_data_path.glob(f"**/{self.profiler_name}")):
            files = sorted(directory.glob("*.txt"))
            if not files:
                continue
            target = (
                self._preprocessed_data_path
                / directory.relative_to(self._raw_data_path)
            ) / "run.stat.csv"
            if target.exists():
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with open(target, "w", encoding="utf-8") as out:
                out.write("group,metric,sum,min,max,avg\n")
                for path in files:
                    group, rows = read_stat_rows(path)
                    for metric, numbers in rows:
                        out.write(
                            f'{group},"{metric}",'
                            + ",".join(repr(n) for n in numbers)
                            + "\n"
                        )


__extension_data_preprocessor__: type[Preprocessor] = LIKWIDPreprocessor
