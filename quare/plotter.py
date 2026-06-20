"""
Core visualisation and export logic shared by all profiler extensions.

:class:`Plotter` produces three kinds of output for each profiler:

1. **INFO plot** — a table image (PNG) summarising the experimental context
   (machine, session, use-case).
2. **CSV export** — all metric/analysis values alongside the x-axis (cells
   per rank) in a spreadsheet-friendly format.
3. **Data plots** — one semi-log scatter plot per metric/analysis.

All output is written to a directory tree under ``output_directory_path``
(from settings)::

    <output>/
    └── <session>/
        └── <machine>/
            └── <use_case>/
                ├── profiler_metrics/<profiler_name>/
                │   ├── INFO.png
                │   ├── results.csv
                │   └── Plot <metric_key>.png
                └── analyses/
                    ├── results.csv
                    └── Plot <analysis_key>.png
"""

from collections.abc import Sequence
from pathlib import Path

import pandas as pd
from matplotlib import pyplot as plt

from .data_retriever import DataRetrieversManager, MetricsData, UniqueMetricKey
from .utils import divide_dict_into_chunks, load_settings


class Plotter:
    """
    Generates plots, CSV exports, and INFO tables for a single profiler extension.

    Instantiated with the profiler name; acquires its
    :class:`~quare.data_retriever.DataRetriever` lazily via
    :class:`~quare.data_retriever.DataRetrieversManager`.

    Extension ``plotter.py`` modules assign this class (or a subclass) to
    ``__extension_data_plotter__``.
    """

    def __init__(self, profiler_name: str) -> None:
        """
        Initialise a Plotter for a specific profiler.

        :param profiler_name: Bare profiler name without the ``_ext`` suffix
            (e.g. ``"AMDuProfPCM"``).  Used as the subdirectory name under
            ``profiler_metrics/`` in the output tree.
        :type profiler_name: str
        """
        self._profiler_name: str = profiler_name

    def make_result_info_plot(
        self,
        result_info: dict[str, str],
        png_filename: Path | None = None,
        svg_filename: Path | None = None,
    ) -> None:
        """
        Render a metadata summary table to an image file.

        Produces a figure containing a two-column table (key / value) with
        alternating row shading.  At least one of *png_filename* or
        *svg_filename* must be supplied; passing ``None`` for both is valid
        but produces no output.

        :param result_info: Ordered mapping of display labels to their
            corresponding string (or numeric) values, as returned by
            :meth:`~quare.data_retriever.DataRetriever.get_result_info`.
        :type result_info: dict[str, str]
        :param png_filename: Destination path for a 300 DPI PNG file, or
            ``None`` to skip PNG output.
        :type png_filename: pathlib.Path or None
        :param svg_filename: Destination path for an SVG file, or ``None`` to
            skip SVG output.
        :type svg_filename: pathlib.Path or None
        """
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

    def make_csv(
        self,
        x_range: list[float],
        columns: list[str],
        metrics: MetricsData,
        filename: Path,
    ) -> None:
        """
        Export metric values to a CSV file.

        Prepends an extra row for the x-axis values (cells per rank) and then
        adds one row per metric.  Column headers are the task-size tick labels.

        :param x_range: Ordered list of x-axis values (cells per rank), one
            per task size.
        :type x_range: list[float]
        :param columns: Task-size label strings used as column headers in the
            CSV.
        :type columns: list[str]
        :param metrics: :data:`~quare.data_retriever.MetricsData` dict to
            export; each key becomes a row label.
        :type metrics: MetricsData
        :param filename: Destination path for the CSV file.  Parent directories
            must already exist.
        :type filename: pathlib.Path
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
        """
        Render a stacked figure of semi-log scatter plots, one per metric.

        Each subplot shows a single metric's values against the x-axis (cells
        per rank) on a logarithmic x-scale.  Only the bottom subplot carries
        x-axis tick labels to avoid repetition.  At least one of
        *png_filename* or *svg_filename* must be provided; passing ``None``
        for both is valid but produces no output.

        :param x_range: Ordered list of x-axis values (cells per rank).
        :type x_range: list[float]
        :param x_tick_labels: Labels for the x-axis ticks (displayed only on
            the bottom subplot).
        :type x_tick_labels: list[str]
        :param metrics: :data:`~quare.data_retriever.MetricsData` to plot;
            each entry produces one subplot.
        :type metrics: MetricsData
        :param png_filename: Destination path for a 300 DPI PNG, or ``None``.
        :type png_filename: pathlib.Path or None
        :param svg_filename: Destination path for an SVG, or ``None``.
        :type svg_filename: pathlib.Path or None
        :param x_grid: Whether to draw vertical grid lines.
        :type x_grid: bool
        :param y_grid: Whether to draw horizontal grid lines.
        :type y_grid: bool
        """
        num_of_figures: int = len(metrics)
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

    def make_all(self) -> None:
        """
        Run the full output pipeline for this profiler.

        Reads all necessary configuration from :func:`~quare.utils.load_settings`,
        then:

        1. Queries :class:`~quare.data_retriever.DataRetriever` for matching
           repetition IDs and result info.
        2. Resolves the output directory path.
        3. Generates and saves the INFO table image.
        4. For raw metrics: saves ``results.csv`` and one PNG per metric.
        5. For computed analyses: saves ``results.csv`` and one PNG per
           analysis.

        Metrics and analyses whose values are *all* ``None`` are skipped (no
        plot is produced).
        """
        settings = load_settings()
        data_retriever = DataRetrieversManager.get_retriever(self._profiler_name)

        repetition_ids = data_retriever.get_repetitions(
            settings["session_name_contains"],
            settings["machine_name"],
            settings["use_case_name"],
            settings["sizes_to_get"],
            settings["repetition_name_contains"],
        )
        x_range, x_tick_labels = data_retriever.get_x_range_and_labels(
            settings["sizes_to_get"], settings["machine_name"]
        )
        result_info = data_retriever.get_result_info(repetition_ids)
        parent_dir_path = (
            Path(settings["output_directory_path"])
            / result_info["Session"]
            / result_info["Machine name"]
            / result_info["Use case"]
        )

        metrics = data_retriever.get_data(
            repetition_ids, settings["metric_names"], []
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
            self.make_data_plots(
                x_range,
                [f"{size}\n{label}" for size, label in zip(x_range, x_tick_labels)],
                chunked_metrics,
                png_filename=png_filename,
            )

        analytics = data_retriever.get_data(
            repetition_ids, [], settings["analyses_names"]
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
            png_filename = analytics_parent_dir_path / f"Plot {one_key}.png"
            self.make_data_plots(
                x_range,
                [f"{size}\n{label}" for size, label in zip(x_range, x_tick_labels)],
                chunked_analytics,
                png_filename=png_filename,
            )
