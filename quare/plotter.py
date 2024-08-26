from collections.abc import Sequence
from pathlib import Path

import pandas as pd
from matplotlib import pyplot as plt

from .data_retriever import DataRetriever, MetricsData, UniqueMetricKey
from .utils import divide_dict_into_chunks, load_settings


class Plotter:
    """
    _summary_

    :param data_retriever: _description_
    :param profiler_name: _description_
    """

    def __init__(
        self,
        data_retriever: DataRetriever,
        profiler_name: str,
    ) -> None:
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
            UniqueMetricKey("Cells per rank (size)", "number", ""): x_range
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
        result_info = self._data_retriever.get_result_info(repetition_ids)
        parent_dir_path = (
            Path(settings["output_directory_path"])
            / result_info["Session"]
            / result_info["Machine name"]
            / result_info["Use case"]
        )

        metrics = self._data_retriever.get_data(
            repetition_ids, settings["metric_names"], [""]
        )
        metrics_parent_dir_path = (
            parent_dir_path / "profiler_metrics" / self._profiler_name
        )
        metrics_parent_dir_path.mkdir(parents=True, exist_ok=True)

        self.make_result_info_plot(
            result_info, png_filename=metrics_parent_dir_path / "INFO.png"
        )
        self.make_csv(
            x_range,
            x_tick_labels,
            metrics,
            metrics_parent_dir_path / "results.csv",
        )
        multi_metrics = divide_dict_into_chunks(metrics, 1)
        for chunked_metrics in multi_metrics:
            one_key = list(chunked_metrics.keys())[0]
            if all(val is None for val in chunked_metrics[one_key]):
                continue
            png_filename: Path = metrics_parent_dir_path / f"Plot {one_key}.png"
            # svg_filename = parent_dir_path / f"GRAPH{i}.svg"
            self.make_data_plots(
                x_range,
                [f"{size}\n{label}" for size, label in zip(x_range, x_tick_labels)],
                chunked_metrics,
                png_filename=png_filename,
            )

        analytics = self._data_retriever.get_data(
            repetition_ids, [""], settings["analyses_names"]
        )
        analytics_parent_dir_path = parent_dir_path / "analyses"
        analytics_parent_dir_path.mkdir(parents=True, exist_ok=True)
        self.make_csv(
            x_range,
            x_tick_labels,
            analytics,
            analytics_parent_dir_path / "results.csv",
        )
        multi_analytics = divide_dict_into_chunks(analytics, 1)
        for chunked_analytics in multi_analytics:
            one_key = list(chunked_analytics.keys())[0]
            if all(val is None for val in chunked_analytics[one_key]):
                continue
            png_filename: Path = analytics_parent_dir_path / f"Plot {one_key}.png"
            self.make_data_plots(
                x_range,
                [f"{size}\n{label}" for size, label in zip(x_range, x_tick_labels)],
                chunked_analytics,
                png_filename=png_filename,
            )
