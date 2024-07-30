from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import (
    Machine,
    MetricsBase,
    MetricsDictBase,
    ProfilingSession,
    Repetition,
    TaskSizesDict,
    UseCase,
)
from .utils import InMemoryTaskSizesDict, divide_dict_into_chunks, load_settings


@dataclass
class UniqueMetricKey:
    """_summary_"""

    name: str
    """member description"""
    unit: str
    """member description"""
    processing_unit: str
    """member description"""

    def __hash__(self) -> int:
        return hash(self.name + self.unit + self.processing_unit)

    def __repr__(self) -> str:
        return f"{self.name} | {self.unit} | {self.processing_unit}"


MetricsData = dict[UniqueMetricKey, list[float | int | None]]


class DataRetriever:
    """_summary_"""

    def __init__(
        self,
        db_session: Session,
        metrics_table: type[MetricsBase],
        metrics_dict_table: type[MetricsDictBase],
    ) -> None:
        """_summary_

        :param db_session: _description_
        :param metrics_table: _description_
        :param metrics_dict_table: _description_
        """
        self._db_session: Session = db_session
        self._metrics_table: type[MetricsBase] = metrics_table
        self._metrics_dict_table: type[MetricsDictBase] = metrics_dict_table

        InMemoryTaskSizesDict.initialize(db_session)

    def get_repetitions(
        self,
        session_name_contains: str,
        machine_name: str,
        use_case_name: str,
        task_size_names: list[str],
        repetition_name_contains: str,
    ) -> dict[str, list[int]]:
        """
        _summary_

        :param session_name_contains: _description_
        :param machine_name: _description_
        :param use_case_name: _description_
        :param task_size_names: _description_
        :param repetition_name_contains: _description_
        :return: _description_
        """
        result: dict[str, list[int]] = {}
        for size_name in task_size_names:
            stmt = (
                select(Repetition.id)
                .join(ProfilingSession)
                .join(Machine)
                .join(UseCase)
                .join(TaskSizesDict)
                .where(
                    ProfilingSession.name.contains(session_name_contains),
                    Machine.name == machine_name,
                    UseCase.name == use_case_name,
                    TaskSizesDict.name == size_name,
                    Repetition.name.contains(repetition_name_contains),
                )
            )

            rows = self._db_session.execute(stmt).all()
            if rows:
                ids: list[int] = [row.id for row in rows]
            else:
                ids: list[int] = []
            result[size_name] = ids
        return result

    def get_result_info(self, repetition_ids: dict[str, list[int]]) -> dict[str, str]:
        """
        _summary_

        :param repetition_ids: _description_
        :return: _description_
        """
        result_info: dict[str, str] = {}
        for size_repetition_ids in repetition_ids.values():
            for repetition_id in size_repetition_ids:
                stmt = (
                    select(
                        Repetition,
                        Machine,
                        UseCase,
                        ProfilingSession,
                    )
                    .where(Repetition.id == repetition_id)
                    .join(Machine)
                    .join(UseCase)
                    .join(ProfilingSession)
                )
                row = self._db_session.execute(stmt).first()
                if row:
                    result_info = {
                        "Session": row[3].name,
                        "Machine name": row[1].name,
                        "Use case": row[2].name,
                        "Num. of cores": row[1].num_of_cores,
                        "Num. of threads": row[1].num_of_threads,
                    }
                    return result_info
        return {}

    def get_data(
        self, repetition_ids: dict[str, list[int]], metric_names: list[str]
    ) -> MetricsData:
        """_summary_

        :param repetition_ids: _description_
        :param metric_names: _description_
        :return: _description_
        """
        metrics: MetricsData = {}

        if metric_names:
            stmt = select(
                self._metrics_dict_table.name,
                self._metrics_dict_table.unit,
                self._metrics_dict_table.processing_unit,
            ).where(self._metrics_dict_table.name.in_(metric_names))
        else:
            stmt = select(
                self._metrics_dict_table.name,
                self._metrics_dict_table.unit,
                self._metrics_dict_table.processing_unit,
            )
        metrics_data: list = list(self._db_session.execute(stmt).all())

        validated_metric_names: list[str] = [row[0] for row in metrics_data]
        metric_units: list[str] = [row[1] for row in metrics_data]
        metric_processing_units: list[str] = [row[2] for row in metrics_data]

        for metric_data in zip(
            validated_metric_names, metric_units, metric_processing_units
        ):
            metrics[UniqueMetricKey(*metric_data)] = []

        for size_repetition_ids in repetition_ids.values():
            for metric_data in zip(
                validated_metric_names, metric_units, metric_processing_units
            ):
                stmt = (
                    select(self._metrics_table)
                    .where(self._metrics_table.repetition.in_(size_repetition_ids))
                    .join(self._metrics_dict_table)
                    .where(
                        self._metrics_dict_table.name == metric_data[0],
                        self._metrics_dict_table.unit == metric_data[1],
                        self._metrics_dict_table.processing_unit == metric_data[2],
                    )
                )
                rows = self._db_session.execute(stmt).all()
                if not rows:
                    metrics[UniqueMetricKey(*metric_data)].append(None)
                else:
                    values = [row[0].value for row in rows]
                    metrics[UniqueMetricKey(*metric_data)].append(
                        float(np.mean(values))
                    )
        return metrics

    def get_machine_cores_count(self, machine_name: str) -> int | None:
        """_summary_

        :param machine_name: _description_
        :return: _description_
        """
        stmt = select(Machine.num_of_cores).where(Machine.name == machine_name)
        row = self._db_session.execute(stmt).first()
        if row:
            return row[0]
        else:
            return None

    def get_x_range_and_labels(
        self, sizes: list[str], machine_name: str
    ) -> tuple[list[float], list[str]]:
        """_summary_

        :param sizes: _description_
        :param machine_name: _description_
        :raises Exception: _description_
        :return: _description_
        """
        machine_num_of_cores = self.get_machine_cores_count(machine_name)
        if not machine_num_of_cores:
            raise Exception(f'No num_of_cores for "{machine_name}" machine')

        x_range: list[float] = []
        x_tick_labels: list[str] = []
        for task_size_name in sizes:
            x_range.append(
                InMemoryTaskSizesDict.rows[task_size_name][1] / machine_num_of_cores
            )
            x_tick_labels.append(task_size_name)
        return x_range, x_tick_labels


class Plotter:
    """_summary_"""

    def __init__(
        self,
        data_retriever: DataRetriever,
        profiler_name: str,
    ) -> None:
        """_summary_

        :param data_retriever: _description_
        :param profiler_name: _description_
        """
        self._data_retriever: DataRetriever = data_retriever
        self._profiler_name: str = profiler_name

    def make_result_info_plot(
        self,
        result_info: dict[str, str],
        png_filename: Path | None = None,
        svg_filename: Path | None = None,
    ) -> None:
        """
        _summary_

        :param result_info: _description_
        :param png_filename: _description_, defaults to None
        :param svg_filename: _description_, defaults to None
        """
        # axes: list[list[Axes]]
        fig, axes = plt.subplots(1, 1, figsize=(12, 5), squeeze=False)
        fig.subplots_adjust(
            left=0.01, bottom=0.01, right=0.99, top=0.99, wspace=0.0, hspace=0.0
        )

        axes[0][0].set_yticks([])
        axes[0][0].set_xticks([])
        machine_info_table = axes[0][0].table(
            [[key, val] for key, val in result_info.items()],
            colWidths=[1 / 4, 3 / 4],
            cellLoc="left",
            loc="upper center",
            edges="closed",
        )
        for yx, cell in machine_info_table.get_celld().items():
            y, _ = yx
            cell.set_linewidth(0)
            if not y % 2:
                cell.set_facecolor("lightblue")

        if png_filename:
            fig.savefig(png_filename.as_posix(), dpi=300)
        if svg_filename:
            fig.savefig(svg_filename.as_posix())
        plt.close()
        plt.cla()
        plt.clf()

    def make_csv(
        self,
        x_range: list[float],
        columns: list[str],
        metrics: MetricsData,
        filename: Path,
    ) -> None:
        """_summary_

        :param x_range: _description_
        :param columns: _description_
        :param metrics: _description_
        :param filename: _description_
        """
        data: dict[UniqueMetricKey, Sequence[float | None]] = {
            UniqueMetricKey("Cells per rank (size)", "", ""): x_range
        }
        data.update(metrics)
        pd.DataFrame.from_dict(data, orient="index", columns=columns).to_csv(filename)

    def make_data_plots(
        self,
        x_range: list[float],
        x_tick_labels: list[str],
        metrics: MetricsData,
        png_filename: Path | None = None,
        svg_filename: Path | None = None,
        x_grid: bool = True,
        y_grid: bool = True,
    ) -> None:
        """_summary_

        :param x_range: _description_
        :param x_tick_labels: _description_
        :param metrics: _description_
        :param png_filename: _description_, defaults to None
        :param svg_filename: _description_, defaults to None
        :param x_grid: _description_, defaults to True
        :param y_grid: _description_, defaults to True
        """
        num_of_figures: int = len(metrics)
        # axes: list[list[Axes]]
        fig, axes = plt.subplots(
            num_of_figures, 1, figsize=(12, num_of_figures * 5), squeeze=False
        )

        fig.subplots_adjust(
            left=0.12, bottom=0.115, right=0.98, top=0.95, wspace=0.0, hspace=0.0
        )

        i: int = 0
        for key, value_series in metrics.items():
            axes[i][0].semilogx(
                x_range,
                value_series,
                "bo",
                # label=key,
                linestyle="dashed",
                linewidth=0.4,
            )
            axes[i][0].set_title(
                key.name
                + (" (" + key.unit + ") " if key.unit else " ")
                + f"[{key.processing_unit}] vs. task size"
            )
            axes[i][0].set_xticks(x_range)
            axes[i][0].set_ylabel(key.unit if key.unit else "unknown unit")
            # axes[i][0].legend(loc="upper right", fontsize="8")
            axes[i][0].yaxis.get_major_formatter().set_scientific(
                False
            )  # pyright: ignore
            axes[i][0].xaxis.grid(x_grid)
            axes[i][0].yaxis.grid(y_grid)

            if i + 1 == len(metrics):
                axes[i][0].set_xticklabels(x_tick_labels, fontsize="8")
                axes[i][0].set_xlabel("Cells per rank (size name)")

            i += 1

        if png_filename:
            fig.savefig(png_filename.as_posix(), dpi=300)
        if svg_filename:
            fig.savefig(svg_filename.as_posix())
        plt.close()
        plt.cla()
        plt.clf()

    def make_all(self) -> None:
        """_summary_"""
        settings = load_settings()

        repetition_ids = self._data_retriever.get_repetitions(
            settings["session_name_contains"],
            settings["machine_name"],
            settings["use_case_name"],
            settings["sizes_to_get"],
            settings["repetition_name_contains"],
        )
        x_range, x_tick_labels = self._data_retriever.get_x_range_and_labels(
            settings["sizes_to_get"], settings["machine_name"]
        )
        metrics = self._data_retriever.get_data(
            repetition_ids, settings["metric_names"]
        )
        result_info = self._data_retriever.get_result_info(repetition_ids)

        parent_dir_path = (
            Path(settings["output_directory_path"])
            / result_info["Session"]
            / result_info["Machine name"]
            / result_info["Use case"]
            / self._profiler_name
        )
        parent_dir_path.mkdir(parents=True, exist_ok=True)

        self.make_result_info_plot(
            result_info, png_filename=parent_dir_path / "INFO.png"
        )
        self.make_csv(
            x_range,
            x_tick_labels,
            metrics,
            parent_dir_path / "results.csv",
        )
        multi_metrics = divide_dict_into_chunks(metrics, 1)
        for chunked_metrics in multi_metrics:
            one_key = list(chunked_metrics.keys())[0]
            if all(val is None for val in chunked_metrics[one_key]):
                continue
            png_filename: Path = parent_dir_path / f"Plot {one_key}.png"
            # svg_filename = parent_dir_path / f"GRAPH{i}.svg"
            self.make_data_plots(
                x_range,
                [f"{size}\n{label}" for size, label in zip(x_range, x_tick_labels)],
                chunked_metrics,
                png_filename=png_filename,
            )
