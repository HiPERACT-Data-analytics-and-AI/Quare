import numpy as np
from matplotlib import pyplot as plt
from matplotlib.axes import Axes
from sqlalchemy import select
from sqlalchemy.orm import Session

from db_models import Machine, ProfilingSession, TaskSizesDict, UseCase
from db_models.amduprofpcm_models import (
    AMDuProfPcm_core_metrics,
    AMDuProfPcm_l3_metrics,
    AMDuProfPcm_metrics_dict,
)
from utils import create_db_engine


def make_figures(
    x_range: list[float],
    x_tick_labels: list[str],
    metrics: dict[str, list[float]],
) -> None:

    num_of_figures: int = len(metrics)
    fig, axes = plt.subplots(
        num_of_figures, 1, figsize=(12, num_of_figures * 5), squeeze=False
    )
    fig.subplots_adjust(
        left=0.05, bottom=0.05, right=0.95, top=0.95, wspace=0.4, hspace=0.4
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

        if i+1 == len(metrics):
            axes[i][0].set_xticklabels(x_tick_labels, fontsize="8")
            axes[i][0].set_xlabel("Cells per rank (size name)")

        i += 1

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
    metrics: dict[str, list] = {}

    with Session(create_db_engine()) as db_session:
        for metric_name in metric_names:
            metrics[metric_name] = []

        for task_size in sizes_to_get:
            stmt = (
                select(ProfilingSession, UseCase, TaskSizesDict)
                .join(UseCase)
                .join(TaskSizesDict)
                .join(Machine)
                .where(
                    ProfilingSession.name.contains(session_name_contains),
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

            for metric_name in metric_names:
                stmt = (
                    select(AMDuProfPcm_core_metrics)
                    .where(
                        AMDuProfPcm_core_metrics.profiling_session
                        == profiling_session.id
                    )
                    .join(AMDuProfPcm_metrics_dict)
                    .where(AMDuProfPcm_metrics_dict.name == metric_name)
                )
                rows = db_session.execute(stmt).all()
                values = [row[0].value for row in rows]

                if not rows:
                    stmt = (
                        select(AMDuProfPcm_l3_metrics)
                        .where(
                            AMDuProfPcm_l3_metrics.profiling_session
                            == profiling_session.id
                        )
                    )
                    rows = db_session.execute(stmt).all()
                    values = [getattr(row[0], NO_DICT_METRICS[metric_name]) for row in rows]

                metrics[metric_name].append(np.mean(values))

    make_figures(x_range, x_tick_labels, metrics)


if __name__ == "__main__":
    main()
