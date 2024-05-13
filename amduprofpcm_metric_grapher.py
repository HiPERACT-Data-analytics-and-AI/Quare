from matplotlib import pyplot as plt
import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from db_models.amduprofpcm_models import (
    AMDuProfPcm_core_metrics,
    AMDuProfPcm_further_machine_info,
    AMDuProfPcm_l3_metrics,
    AMDuProfPcm_machine_cpu_topology,
    AMDuProfPcm_machine_info,
    AMDuProfPcm_metrics_dict,
)
from db_models import (
    ProfilingSession,
    UseCase,
    TaskSizesDict,
    Machine,
)

from utils import create_db_engine


def make_figures(
        x_range: list[float],
        x_tick_labels: list[str],
        metrics: dict[str, list[float]],
    ) -> None:
    COLORS = ["C1", "C2", "C3"]
    # up to 9 parameters (due to color):
    MARKERS = ["d", "d", "d", "s", "s", "s", "*", "*", "*"]

    num_of_figures: int = 1
    fig, axes = plt.subplots(1,num_of_figures,figsize=(num_of_figures*12,5), squeeze=False)
    fig.subplots_adjust(left=0.05, bottom=0.07, right=0.95, top=0.95, wspace=0.4, hspace=0.4)

    axis_l = axes[0][0]
    axis_r = [ax.twinx() for ax in axes[0]]
    axis_r = axis_r[0]
    
    n = 0
    for key, value_series in metrics.items():
        axis_r.semilogx(x_range, value_series, "k", linestyle='dashed', linewidth=0.4)
        axis_r.semilogx(x_range, value_series, f"{COLORS[n%len(COLORS)]}{MARKERS[n%len(MARKERS)]}", label=key)
        n += 1
    
    axis_l.set_xticks(x_range)
    axis_l.set_xticklabels( x_tick_labels, fontsize="8" )
    axis_l.set_xlabel("Cells per rank (size name)")
    axis_r.set_ylabel("Metric's unit")
    axis_l.legend(loc='upper left', fontsize="8")
    axis_r.legend(loc='upper right', fontsize="8")

    fig.savefig("./GRAPH.png", dpi=300)
    fig.savefig("./GRAPH.svg")
    plt.close()
    plt.cla()
    plt.clf()


def main() -> None:
    metric_names: list[str] = ["L2 Access (pti)", "L2 Miss (pti)", "L2 Hit (pti)"]
    num_of_cores: int = 128

    session_name_contains: str = "IPC"
    use_case_id: int = 2
    machine_name: str = "128_ROME"
    sizes_to_get: tuple[str, ...] = ("xsmall", "small", "smid", "mid", "high", "mhigh", "uhigh", "xhigh")

    num_of_figures: int = 1
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
                    ~ProfilingSession.name.contains("kosz"),
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
            x_tick_labels.append(f"{x_range[-1]} \n(\"{task_sizes_dict.name}\")")

            for metric_name in metric_names:
                stmt = (
                    select(AMDuProfPcm_core_metrics)
                    .where(AMDuProfPcm_core_metrics.profiling_session == profiling_session.id)
                    .join(AMDuProfPcm_metrics_dict)
                    .where(AMDuProfPcm_metrics_dict.name == metric_name)
                )
                rows = db_session.execute(stmt).all()
                values = [row[0].value for row in rows]
                metrics[metric_name].append(np.mean(values))
    make_figures(x_range, x_tick_labels, metrics)


if __name__ == "__main__":
    main()
