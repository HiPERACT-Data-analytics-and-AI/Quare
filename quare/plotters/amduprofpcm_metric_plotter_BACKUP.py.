import numpy as np
from matplotlib import pyplot as plt
from matplotlib.axes import Axes
from sqlalchemy import select
from sqlalchemy.orm import Session

from db_models import Machine, Repetition, TaskSizesDict, UseCase
from db_models.amduprofpcm_models import (
    AMDuProfPCM_l3_metrics,
    AMDuProfPCM_metrics,
    AMDuProfPCM_metrics_dict,
)
from utils import create_db_engine


def make_figures(
    x_range: list[float],
    x_tick_labels: list[str],
    fvops: list[float],
    metrics: dict[str, list[float]],
) -> None:
    # up to 9 different parameters (due to color):
    COLORS = ["C1", "C2", "C3"]
    MARKERS = ["d", "d", "d", "s", "s", "s", "*", "*", "*"]

    num_of_figures: int = 1
    fig, axes = plt.subplots(
        1, num_of_figures, figsize=(num_of_figures * 12, 5), squeeze=False
    )
    fig.subplots_adjust(
        left=0.05, bottom=0.13, right=0.95, top=0.95, wspace=0.4, hspace=0.4
    )

    axis_l: Axes = axes[0][0]
    axis_r: Axes = [ax.twinx() for ax in axes[0]][0]

    axis_l.semilogx(
        x_range,
        fvops,
        "bo",
        label="FVOPS",
        markersize=8,
        linestyle="dashed",
        linewidth=0.4,
    )

    n: int = 0
    for key, value_series in metrics.items():
        axis_r.semilogx(
            x_range,
            value_series,
            f"{MARKERS[n%len(MARKERS)]}{COLORS[n%len(COLORS)]}",
            label=key,
            linestyle="dashed",
            linewidth=0.4,
        )
        n += 1

    axis_l.set_xticks(x_range)
    axis_l.set_xticklabels(x_tick_labels, fontsize="8")
    axis_l.set_xlabel("Cells per rank (size name)")

    axis_l.set_ylabel("FVOPS")
    axis_r.set_ylabel("Common scale for all the metrics")

    axis_l.legend(loc="upper left", fontsize="8")
    axis_r.legend(loc="upper right", fontsize="8")

    fig.savefig("./GRAPH.png", dpi=300)
    fig.savefig("./GRAPH.svg")
    plt.close()
    plt.cla()
    plt.clf()


def main() -> None:
    NO_DICT_METRICS: dict = {
        "L3 Access": "l3_access",
        "L3 Miss": "l3_miss",
        "L3 Miss Percent": "l3_miss_percent",
        "L3 Miss Latency": "ave_l3_miss_latency",
    }
    metric_names: list[str] = ["L2 Access (pti)", "L2 Miss (pti)", "L2 Hit (pti)"]
    num_of_cores: int = 128

    session_name_contains: str = "IPC"
    use_case_id: int = 2
    machine_name: str = "128_ROME"
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

    x_range: list[float] = []
    x_tick_labels: list[str] = []
    fvops: list[float] = []
    metrics: dict[str, list] = {}

    with Session(create_db_engine()) as db_session:
        for metric_name in metric_names:
            metrics[metric_name] = []

        for task_size in sizes_to_get:
            stmt = (
                select(Repetition, UseCase, TaskSizesDict)
                .join(UseCase)
                .join(TaskSizesDict)
                .join(Machine)
                .where(
                    Repetition.name.contains(session_name_contains),
                    ~Repetition.name.contains("kosz"),
                    UseCase.id == use_case_id,
                    TaskSizesDict.name == task_size,
                    Machine.name == machine_name,
                )
            )

            row = db_session.execute(stmt).first()
            if row is None:
                continue

            profiling_session, use_case, task_sizes_dict = row
            print(profiling_session.name, use_case.name, task_sizes_dict.name)
            x_range.append(task_sizes_dict.size / num_of_cores)
            x_tick_labels.append(f'{x_range[-1]} \n("{task_sizes_dict.name}")')

            fvops.append(task_sizes_dict.size / profiling_session.exec_time_s)

            for metric_name in metric_names:
                stmt = (
                    select(AMDuProfPCM_metrics)
                    .where(AMDuProfPCM_metrics.repetition == profiling_session.id)
                    .join(AMDuProfPCM_metrics_dict)
                    .where(AMDuProfPCM_metrics_dict.name == metric_name)
                )
                rows = db_session.execute(stmt).all()
                values = [row[0].value for row in rows]

                if not rows:
                    stmt = select(AMDuProfPCM_l3_metrics).where(
                        AMDuProfPCM_l3_metrics.repetition == profiling_session.id
                    )
                    rows = db_session.execute(stmt).all()
                    values = [
                        getattr(row[0], NO_DICT_METRICS[metric_name]) for row in rows
                    ]

                metrics[metric_name].append(np.mean(values))

    make_figures(x_range, x_tick_labels, fvops, metrics)


if __name__ == "__main__":
    main()
