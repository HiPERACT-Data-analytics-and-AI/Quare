from itertools import islice
from pathlib import Path

import numpy as np
from matplotlib import pyplot as plt
from matplotlib.axes import Axes
from sqlalchemy import select
from sqlalchemy.orm import Session

from db_models import Machine, ProfilingSession, Repetition, TaskSizesDict, UseCase
from db_models.amduprofpcm_models import AMDuProfPCM_metrics, AMDuProfPCM_metrics_dict
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


def divide_dict_into_chunks(dict_to_splice, max_size):
    dict_items_iterator = iter(dict_to_splice.items())
    return [
        dict(islice(dict_items_iterator, max_size))
        for _ in range(0, len(dict_to_splice), max_size)
    ]


def make_figures(
    x_range: list[float],
    x_tick_labels: list[str],
    metrics: dict[str, list[float | int]],
    png_filename: Path | None = None,
    svg_filename: Path | None = None,
) -> None:

    num_of_figures: int = len(metrics)
    axes: list[list[Axes]]
    fig, axes = plt.subplots(
        num_of_figures, 1, figsize=(12, num_of_figures * 5), squeeze=False
    )

    fig.subplots_adjust(
        left=0.15, bottom=0.05, right=0.95, top=0.95, wspace=0.4, hspace=0.0
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
        axes[i][0].set_ylabel("Native unit for the metric")
        axes[i][0].legend(loc="upper right", fontsize="8")
        # axes[i][0].yaxis.set_major_formatter(ticker.ScalarFormatter(useMathText=False))
        # axes[i][0].yaxis.get_major_formatter()
        axes[i][0].yaxis.get_major_formatter().set_scientific(False)  # pyright: ignore

        if i + 1 == len(metrics):
            axes[i][0].set_xticklabels(x_tick_labels, fontsize="8")
            axes[i][0].set_xlabel("Cells per rank (size name)")

        i += 1

    if png_filename:
        fig.savefig(png_filename, dpi=300)
    if svg_filename:
        fig.savefig(svg_filename)
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


def main() -> None:
    metric_names: set[str] = set()
    metric_names: set[str] = {
        "L2 Access (pti)",
        "L2 Miss (pti)",
        # "L2 Hit (pti)",
        # "L3 Access",
    }
    num_of_cores: int = 128

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
    metrics: dict[str, list] = {}

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
            print(task_size_name, repetitions_ids)

            x_range.append(
                InMemoryTables.task_sizes_dict[task_size_name] / num_of_cores
            )
            x_tick_labels.append(f"{x_range[-1]} \n({task_size_name})")

            for metric_name in metric_names:
                stmt = (
                    select(AMDuProfPCM_metrics)
                    .where(AMDuProfPCM_metrics.repetition.in_(repetitions_ids))
                    .join(AMDuProfPCM_metrics_dict)
                    .where(AMDuProfPCM_metrics_dict.name == metric_name)
                )
                rows = db_session.execute(stmt).all()
                if not rows:
                    metrics[metric_name].append(0)  # temporary hotfix
                else:
                    values = [row[0].value for row in rows]
                    metrics[metric_name].append(np.mean(values))

    multi_metrics = divide_dict_into_chunks(metrics, 15)
    for i, chunked_metrics in enumerate(multi_metrics):
        png_filename = Path(f"./GRAPH{i}.png")
        # svg_filename = Path(f"./GRAPH{i}.svg")
        make_figures(x_range, x_tick_labels, chunked_metrics, png_filename=png_filename)


if __name__ == "__main__":
    main()
