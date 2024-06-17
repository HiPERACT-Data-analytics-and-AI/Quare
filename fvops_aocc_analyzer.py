from math import fsum

import numpy as np
from matplotlib import pyplot as plt
from sqlalchemy import select
from sqlalchemy.orm import Session

from db_models import Machine, Repetition, TaskSizesDict, UseCase
from db_models.amduprofpcm_models import (
    AMDuProfPCM_metrics,
    AMDuProfPCM_further_machine_info,
    AMDuProfPCM_l3_metrics,
    AMDuProfPCM_machine_cpu_topology,
    AMDuProfPCM_machine_info,
    AMDuProfPCM_metrics_dict,
)
from utils import create_db_engine


def make_figures(
    axis_l,
    axis_r,
    x_range: list,
    x_tick_labels: list,
    fvops: list,
    l2_ratios: list,
    l3_miss_ratio: list,
):
    # timing [totalSimpleTime, avgStepSimpleTime, domainSize, cellsPerCore, fvops ]
    axis_l.semilogx(x_range, fvops, color="k", linestyle="dashed", linewidth=0.4)
    axis_l.semilogx(x_range, fvops, "bo", markersize=8, label="FVOPS")

    #
    axis_r.semilogx(x_range, l2_ratios[0], "k", linestyle="dashed", linewidth=0.4)
    axis_r.semilogx(x_range, l2_ratios[0], "C1d", label="L2 miss ratio (total)")

    axis_r.semilogx(x_range, l2_ratios[1], "k", linestyle="dashed", linewidth=0.4)
    axis_r.semilogx(x_range, l2_ratios[1], "C2d", label="L2 miss ratio from L1DC")

    axis_r.semilogx(x_range, l2_ratios[2], "k", linestyle="dashed", linewidth=0.4)
    axis_r.semilogx(x_range, l2_ratios[2], "C3d", label="L2 miss ratio from HWPF")

    axis_r.semilogx(x_range, l2_ratios[3], "k", linestyle="dashed", linewidth=0.4)
    axis_r.semilogx(x_range, l2_ratios[3], "C1s", label="L2 hit ratio (total)")

    axis_r.semilogx(x_range, l2_ratios[4], "k", linestyle="dashed", linewidth=0.4)
    axis_r.semilogx(x_range, l2_ratios[4], "C2s", label="L2 hit ratio from L1DC")

    axis_r.semilogx(x_range, l2_ratios[5], "k", linestyle="dashed", linewidth=0.4)
    axis_r.semilogx(x_range, l2_ratios[5], "C3s", label="L2 hit ratio from HWPF")

    #
    axis_r.semilogx(x_range, l3_miss_ratio, "k", linestyle="dashed", linewidth=0.4)
    axis_r.semilogx(x_range, l3_miss_ratio, "r*", markersize=8, label="L3 miss ratio")

    # axis_r.semilogx(x_range, MPITrace[key][ 1 ], "C6", linestyle='dashed', linewidth=0.4   )
    # axis_r.semilogx(x_range, MPITrace[key][ 1 ], "C6P", label="MPI ratio based on avg comm time" )

    # if key.find("enoa")>=0:
    #     axis_r.semilogx( xRange, BackendBoundMemory[key][0], "k", linestyle='dashed', linewidth=0.4   )
    #     axis_r.semilogx( xRange, BackendBoundMemory[key][0], "C7+", markersize=8 ,label="Backend Bound Memory" )

    #     axis_r.semilogx( xRange, BackendBoundMemory[key][2], "k", linestyle='dashed', linewidth=0.4   )
    #     axis_r.semilogx( xRange, BackendBoundMemory[key][2], "C8+", markersize=8 ,label="Frontend Bound" )

    axis_l.set_xticks(x_range)
    axis_l.set_xticklabels(x_tick_labels, fontsize="8")
    # axis_l.set_xlim(500, 400000 )

    axis_l.set_xlabel("Cells per rank (size name)")
    # axis_l.set_ylim(1, 50000000 )
    axis_l.set_ylabel("FVOPS")
    axis_l.yaxis.get_major_formatter().set_scientific(False)
    axis_r.set_ylim(0, 100)
    axis_r.set_ylabel("Ratio [%]")
    axis_l.legend(loc="upper left", fontsize="8")
    axis_r.legend(loc="upper right", fontsize="8")


def main():
    session_name_contains: str = "IPC"
    use_case_id: int = 2
    num_of_cores: int = 128
    machine_name: str = "128_ROME"

    num_of_figures: int = 2

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
    x_range: list = []
    x_tick_labels: list = []
    fvops: list = []
    l2_ratios: list = [[], [], [], [], [], []]
    l3_miss_ratio: list = []

    with Session(create_db_engine()) as db_session:
        for task_size in sizes_to_get:
            stmt = (
                select(Repetition, UseCase, TaskSizesDict)
                .join(UseCase)
                .join(TaskSizesDict)
                .join(Machine)
                .join(AMDuProfPCM_machine_info)
                .where(
                    Repetition.name.contains(session_name_contains),
                    ~Repetition.name.contains("kosz"),
                    UseCase.id == use_case_id,
                    TaskSizesDict.name == task_size,
                    Machine.name == machine_name,
                    AMDuProfPCM_machine_info.num_of_cores == num_of_cores,
                )
            )
            # for i, row in enumerate(db_session.execute(stmt).all()):
            #     print(i, row[0].name, row[0].use_case, row[1].name, row[2].name)
            row = db_session.execute(stmt).first()
            if row is None:
                continue

            profiling_session, use_case, task_sizes_dict = row
            print(profiling_session.name, use_case.name, task_sizes_dict.name)
            x_range.append(task_sizes_dict.size / num_of_cores)
            x_tick_labels.append(f'{x_range[-1]} \n("{task_sizes_dict.name}")')
            fvops.append(task_sizes_dict.size / profiling_session.exec_time_s)

            stmt = select(AMDuProfPCM_l3_metrics).where(
                AMDuProfPCM_l3_metrics.repetition == profiling_session.id
            )
            l3_tmp = [row[0].l3_miss_percent for row in db_session.execute(stmt).all()]
            l3_miss_ratio.append(fsum(l3_tmp) / len(l3_tmp))

            # L2
            stmt = (
                select(AMDuProfPCM_metrics)
                .where(
                    AMDuProfPCM_metrics.repetition == profiling_session.id
                )
                .join(AMDuProfPCM_metrics_dict)
                .where(AMDuProfPCM_metrics_dict.name == "L2 Access (pti)")
            )
            l2_rows = db_session.execute(stmt).all()
            l2_a = [row[0].value for row in l2_rows]

            stmt = (
                select(AMDuProfPCM_metrics)
                .where(
                    AMDuProfPCM_metrics.repetition == profiling_session.id
                )
                .join(AMDuProfPCM_metrics_dict)
                .where(AMDuProfPCM_metrics_dict.name == "L2 Miss (pti)")
            )
            l2_rows = db_session.execute(stmt).all()
            l2_m = [row[0].value for row in l2_rows]

            stmt = (
                select(AMDuProfPCM_metrics)
                .where(
                    AMDuProfPCM_metrics.repetition == profiling_session.id
                )
                .join(AMDuProfPCM_metrics_dict)
                .where(AMDuProfPCM_metrics_dict.name == "L2 Hit (pti)")
            )
            l2_rows = db_session.execute(stmt).all()
            l2_h = [row[0].value for row in l2_rows]

            stmt = (
                select(AMDuProfPCM_metrics)
                .where(
                    AMDuProfPCM_metrics.repetition == profiling_session.id
                )
                .join(AMDuProfPCM_metrics_dict)
                .where(AMDuProfPCM_metrics_dict.name == "L2 Access from DC Miss (pti)")
            )
            l2_rows = db_session.execute(stmt).all()
            l2_DCa = [row[0].value for row in l2_rows]

            stmt = (
                select(AMDuProfPCM_metrics)
                .where(
                    AMDuProfPCM_metrics.repetition == profiling_session.id
                )
                .join(AMDuProfPCM_metrics_dict)
                .where(AMDuProfPCM_metrics_dict.name == "L2 Miss from DC Miss (pti)")
            )
            l2_rows = db_session.execute(stmt).all()
            l2_DCm = [row[0].value for row in l2_rows]

            stmt = (
                select(AMDuProfPCM_metrics)
                .where(
                    AMDuProfPCM_metrics.repetition == profiling_session.id
                )
                .join(AMDuProfPCM_metrics_dict)
                .where(AMDuProfPCM_metrics_dict.name == "L2 Hit from DC Miss (pti)")
            )
            l2_rows = db_session.execute(stmt).all()
            l2_DCh = [row[0].value for row in l2_rows]

            stmt = (
                select(AMDuProfPCM_metrics)
                .where(
                    AMDuProfPCM_metrics.repetition == profiling_session.id
                )
                .join(AMDuProfPCM_metrics_dict)
                .where(AMDuProfPCM_metrics_dict.name == "L2 Access from HWPF (pti)")
            )
            l2_rows = db_session.execute(stmt).all()
            l2_HWPFa = [row[0].value for row in l2_rows]

            stmt = (
                select(AMDuProfPCM_metrics)
                .where(
                    AMDuProfPCM_metrics.repetition == profiling_session.id
                )
                .join(AMDuProfPCM_metrics_dict)
                .where(AMDuProfPCM_metrics_dict.name == "L2 Miss from HWPF (pti)")
            )
            l2_rows = db_session.execute(stmt).all()
            l2_HWPFm = [row[0].value for row in l2_rows]

            stmt = (
                select(AMDuProfPCM_metrics)
                .where(
                    AMDuProfPCM_metrics.repetition == profiling_session.id
                )
                .join(AMDuProfPCM_metrics_dict)
                .where(AMDuProfPCM_metrics_dict.name == "L2 Hit from HWPF (pti)")
            )
            l2_rows = db_session.execute(stmt).all()
            l2_HWPFh = [row[0].value for row in l2_rows]

            l2_ratios[0].append(np.mean(l2_m) / np.mean(l2_a) * 100.0)
            l2_ratios[1].append(np.mean(l2_DCm) / np.mean(l2_DCa) * 100.0)
            l2_ratios[2].append(np.mean(l2_HWPFm) / np.mean(l2_HWPFa) * 100.0)
            l2_ratios[3].append(np.mean(l2_h) / np.mean(l2_a) * 100.0)
            l2_ratios[4].append(np.mean(l2_DCh) / np.mean(l2_DCa) * 100.0)
            l2_ratios[5].append(np.mean(l2_HWPFh) / np.mean(l2_HWPFa) * 100.0)

            # l2_ratios[0].append((fsum(l2_m)/len(l2_m))/(fsum(l2_a)/len(l2_a)) *100.0)
            # l2_ratios[1].append((fsum(l2_DCm)/len(l2_DCm))/(fsum(l2_DCa)/len(l2_DCa)) *100.0)
            # l2_ratios[2].append((fsum(l2_HWPFm)/len(l2_HWPFm))/(fsum(l2_HWPFa)/len(l2_HWPFa)) *100.0)
            # l2_ratios[3].append((fsum(l2_h)/len(l2_h))/(fsum(l2_a)/len(l2_a)) *100.0)
            # l2_ratios[4].append((fsum(l2_DCh)/len(l2_DCh))/(fsum(l2_DCa)/len(l2_DCa)) *100.0)
            # l2_ratios[5].append((fsum(l2_HWPFh)/len(l2_HWPFh))/(fsum(l2_HWPFa)/len(l2_HWPFa)) *100.0)

    fig, axes = plt.subplots(
        1, num_of_figures, figsize=(num_of_figures * 12, 5), squeeze=False
    )
    fig.subplots_adjust(
        left=0.05, bottom=0.07, right=0.97, top=0.95, wspace=0.4, hspace=0.4
    )

    axis_r = [ax.twinx() for ax in axes[0]]
    # axis_r = [axes.twinx()]

    make_figures(
        axes[0][0], axis_r[0], x_range, x_tick_labels, fvops, l2_ratios, l3_miss_ratio
    )
    # make_figures(axes, axis_r[0], x_range, x_tick_labels, fvops, l2_ratios, l3_miss_ratio)

    axes[0][0].set_title("2x 64-core 2.25 GHz AMD EPYC 7742 (Rome) ", fontsize="12")
    # axes.set_title("2x 64-core 2.25 GHz AMD EPYC 7742 (Rome) ", fontsize="12")

    fig.savefig("./GRAPH.png", dpi=300)
    fig.savefig("./GRAPH.svg")
    plt.close()
    plt.cla()
    plt.clf()


if __name__ == "__main__":
    main()
