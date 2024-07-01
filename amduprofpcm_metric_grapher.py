from itertools import islice
from pathlib import Path
from typing import TypeVar

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.axes import Axes
from sqlalchemy import select
from sqlalchemy.orm import Session

from db_models import Machine, ProfilingSession, Repetition, TaskSizesDict, UseCase
from db_models.amduprofpcm_models import (
    AMDuProfPCM_further_machine_info,
    AMDuProfPCM_machine_info,
    AMDuProfPCM_metrics,
    AMDuProfPCM_metrics_dict,
)
from utils import create_db_engine


class InMemoryTables:
    task_sizes_dict: dict[str, int] = {}

    @classmethod
    def update_task_sizes_dict(cls, db_session: Session) -> None:
        results_list = db_session.execute(
            select(
                TaskSizesDict.size,
                TaskSizesDict.name,
            )
        ).all()
        cls.task_sizes_dict = {row[1]: row[0] for row in results_list}


T = TypeVar("T")
U = TypeVar("U")


def divide_dict_into_chunks(
    dict_to_splice: dict[T, U], max_size: int
) -> list[dict[T, U]]:
    dict_items_iterator = iter(dict_to_splice.items())
    return [
        dict(islice(dict_items_iterator, max_size))
        for _ in range(0, len(dict_to_splice), max_size)
    ]


def make_csv(
    x_range: list[float],
    columns: list[str],
    metrics: dict[str, list[float | int]],
    filename: Path,
) -> None:
    data: dict[str, list[float]] = {"Cells per rank (size)": x_range}
    data.update(metrics)
    pd.DataFrame.from_dict(data, orient="index", columns=columns).to_csv(filename)


def make_info_plot(
    result_info: dict[str, str],
    png_filename: Path | None = None,
    svg_filename: Path | None = None,
) -> None:
    axes: list[list[Axes]]
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


def make_data_plots(
    x_range: list[float],
    x_tick_labels: list[str],
    metrics: dict[str, list[float | int]],
    x_grid: bool = True,
    y_grid: bool = True,
    png_filename: Path | None = None,
    svg_filename: Path | None = None,
) -> None:

    num_of_figures: int = len(metrics)
    axes: list[list[Axes]]
    fig, axes = plt.subplots(
        num_of_figures, 1, figsize=(12, num_of_figures * 5), squeeze=False
    )

    fig.subplots_adjust(
        left=0.12, bottom=0.115, right=0.98, top=0.97, wspace=0.0, hspace=0.0
    )

    i: int = 0
    for key, value_series in metrics.items():
        axes[i][0].semilogx(
            x_range,
            value_series,
            "bo",
            label=key,
            linestyle="dashed",
            linewidth=0.4,
        )
        axes[i][0].set_xticks(x_range)
        # axes[i][0].set_ylabel("Unit")
        axes[i][0].legend(loc="upper right", fontsize="8")
        axes[i][0].yaxis.get_major_formatter().set_scientific(False)  # pyright: ignore
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


def select_repetitions(
    db_session: Session,
    session_name_contains: str,
    machine_name: str,
    use_case_name: str,
    task_size_name: str,
    repetition_name_contains: str,
) -> list[int]:
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
            TaskSizesDict.name == task_size_name,
            Repetition.name.contains(repetition_name_contains),
        )
    )

    rows = db_session.execute(stmt).all()
    if rows:
        ids: list[int] = [row.id for row in rows]
    else:
        ids: list[int] = []
    return ids


def get_result_info_dict(db_session: Session, repetition_id: int) -> dict[str, str]:
    stmt = (
        select(
            AMDuProfPCM_machine_info,
            AMDuProfPCM_further_machine_info,
            Machine,
            UseCase,
            ProfilingSession,
        )
        .where(AMDuProfPCM_machine_info.repetition == repetition_id)
        .join(
            AMDuProfPCM_further_machine_info,
            AMDuProfPCM_machine_info.repetition
            == AMDuProfPCM_further_machine_info.repetition,
        )
        .join(Repetition)
        .join(Machine)
        .join(UseCase)
        .join(ProfilingSession)
    )
    row = db_session.execute(stmt).first()
    if row:
        return {
            "Session": row[4].name,
            "Use case": row[3].name,
            "Machine name": row[2].name,
            "System": row[0].system,
            "# of sockets": row[0].num_of_sockets,
            "# of ccds": row[0].num_of_ccds,
            "# of ccxs": row[0].num_of_ccxs,
            "# of cores": row[0].num_of_cores,
            "# of threads": row[0].num_of_threads,
            "# of threads sharing L3": row[0].num_of_threads_sharing_l3,
            "Core p0 state freq": row[1].core_p0_state_freq,
            "Multiplex interval for core": row[1].multiplex_interval_for_core,
            "Multiplex interval for df": row[1].multiplex_interval_for_df,
            "Multiplex interval for l3": row[1].multiplex_interval_for_l3,
            "Measured df frequency": row[1].measured_df_frequency,
            "Multiplex interval": row[1].multiplex_interval,
            "Version": row[1].version,
        }
    else:
        return {}


def main() -> None:
    metric_names: set[str] = set()
    metric_names: set[str] = {
        "L2 Access (pti)",
        "L2 Miss (pti)",
        "L2 Hit (pti)",
        "L3 Access",
    }

    session_name_contains: str = "Session1"
    machine_name: str = "ROME_128"
    use_case_name: str = "motorBike"
    sizes_to_get: tuple[str, ...] = (
        "xsmall",
        "small",
        "smid",
        "mid",
        "high",
        "mhigh",
        "uhigh",
        "xhigh",
    )
    repetition_name_contains: str = "Session1"

    x_range: list[float] = []
    x_tick_labels: list[str] = []
    metrics: dict[str, list[float | int]] = {}
    result_info: dict[str, str] = {}

    with Session(create_db_engine()) as db_session:
        if not metric_names:
            metrics_data = db_session.execute(
                select(AMDuProfPCM_metrics_dict.name)
            ).all()
            metric_names = {row[0] for row in metrics_data}

        InMemoryTables.update_task_sizes_dict(db_session)

        for metric_name in metric_names:
            metrics[metric_name] = []

        for task_size_name in sizes_to_get:
            repetitions_ids = select_repetitions(
                db_session,
                session_name_contains,
                machine_name,
                use_case_name,
                task_size_name,
                repetition_name_contains,
            )
            if not result_info:
                result_info = get_result_info_dict(db_session, repetitions_ids[0])

            print(task_size_name, repetitions_ids)

            x_range.append(
                InMemoryTables.task_sizes_dict[task_size_name]
                / int(result_info["# of cores"])
            )
            x_tick_labels.append(f"{task_size_name}")

            for metric_name in metric_names:
                stmt = (
                    select(AMDuProfPCM_metrics)
                    .where(AMDuProfPCM_metrics.repetition.in_(repetitions_ids))
                    .join(AMDuProfPCM_metrics_dict)
                    .where(AMDuProfPCM_metrics_dict.name == metric_name)
                )
                rows = db_session.execute(stmt).all()
                if not rows:
                    metrics[metric_name].append(
                        0
                    )  # TODO: Temporary hotfix - better do not make data points at all
                else:
                    values = [row[0].value for row in rows]
                    metrics[metric_name].append(float(np.mean(values)))

    profiler_name: str = "AMDuProfPCM"
    parent_dir_path = (
        Path("output")
        / result_info["Session"]
        / result_info["Machine name"]
        / result_info["Use case"]
        / profiler_name
    )
    parent_dir_path.mkdir(parents=True, exist_ok=True)

    make_csv(
        x_range,
        x_tick_labels,
        metrics,
        parent_dir_path / "results.csv",
    )
    make_info_plot(result_info, png_filename=parent_dir_path / "INFO.png")
    multi_metrics = divide_dict_into_chunks(metrics, 1)
    for chunked_metrics in multi_metrics:
        png_filename: Path = (
            parent_dir_path / f"Plot {[key for key in chunked_metrics.keys()][0]}.png"
        )
        # svg_filename = parent_dir_path / f"GRAPH{i}.svg"
        make_data_plots(
            x_range,
            [f"{size}\n{label}" for size, label in zip(x_range, x_tick_labels)],
            chunked_metrics,
            png_filename=png_filename,
        )


if __name__ == "__main__":
    main()
