from math import fsum

from matplotlib import pyplot as plt
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


# xRange = []

# for sizeId in MAP_MB_SIZES:
#     size = MB_SIZES[sizeId]
#     xRange.append( int(timing["rome128"][2][sizeId]/128) )
#     x_tick_labels.append( str(xRange[-1]) + "\n("+size+")")


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
    axis_l.semilogx(x_range, fvops, color="k", linestyle='dashed', linewidth=0.4 )
    axis_l.semilogx(x_range, fvops, 'bo', markersize=8 , label="FVOPS" )

    #
    # axis_r.semilogx(x_range, l2_ratios[key][0], "k", linestyle='dashed', linewidth=0.4   )
    # axis_r.semilogx(x_range, l2_ratios[key][0], "C1d", label="L2 miss ratio (total)" )

    # axis_r.semilogx(x_range, l2_ratios[key][1], "k", linestyle='dashed', linewidth=0.4   )
    # axis_r.semilogx(x_range, l2_ratios[key][1], "C2d", label="L2 miss ratio from L1DC" )

    # axis_r.semilogx(x_range, l2_ratios[key][2], "k", linestyle='dashed', linewidth=0.4   )
    # axis_r.semilogx(x_range, l2_ratios[key][2], "C3d", label="L2 miss ratio from HWPF" )

    #
    axis_r.semilogx(x_range, l3_miss_ratio, "k", linestyle='dashed', linewidth=0.4)
    axis_r.semilogx(x_range, l3_miss_ratio, "r*", markersize=8 ,label="L3 miss ratio")

    # axis_r.semilogx(x_range, MPITrace[key][ 1 ], "C6", linestyle='dashed', linewidth=0.4   )
    # axis_r.semilogx(x_range, MPITrace[key][ 1 ], "C6P", label="MPI ratio based on avg comm time" )


    # if key.find("enoa")>=0:
    #     axis_r.semilogx( xRange, BackendBoundMemory[key][0], "k", linestyle='dashed', linewidth=0.4   )
    #     axis_r.semilogx( xRange, BackendBoundMemory[key][0], "C7+", markersize=8 ,label="Backend Bound Memory" )

    #     axis_r.semilogx( xRange, BackendBoundMemory[key][2], "k", linestyle='dashed', linewidth=0.4   )
    #     axis_r.semilogx( xRange, BackendBoundMemory[key][2], "C8+", markersize=8 ,label="Frontend Bound" )

    axis_l.set_xticks(x_range)
    axis_l.set_xticklabels( x_tick_labels, fontsize="8" )
    # axis_l.set_xlim(500, 400000 )

    axis_l.set_xlabel("Cells per rank (size name)")
    # axis_l.set_ylim(1, 50000000 )
    axis_l.set_ylabel("FVOPS")
    axis_l.yaxis.get_major_formatter().set_scientific(False)
    axis_r.set_ylim(0, 100)
    axis_r.set_ylabel("Ratio [%]")
    axis_l.legend(loc='upper left', fontsize="8")
    axis_r.legend(loc='upper right', fontsize="8")


def main():
    session_name_contains: str = "IPC"
    use_case_id: int = 2
    num_of_cores: int = 128
    machine_name: str = "128_ROME"

    num_of_figures: int = 1

    sizes_to_get: tuple[str, ...] = ("xsmall", "small", "smid", "mid", "high", "mhigh", "uhigh", "xhigh")
    x_range: list = []
    x_tick_labels: list = []
    fvops: list = []
    l2_ratios: list = [[], [], []]
    l3_miss_ratio: list = []
    

    with Session(create_db_engine()) as db_session:
        for task_size in sizes_to_get:
            stmt = (
                select(ProfilingSession, UseCase, TaskSizesDict)
                .join(UseCase)
                .join(TaskSizesDict)
                .join(Machine)
                .join(AMDuProfPcm_machine_info)
                .where(
                    ProfilingSession.name.contains(session_name_contains),
                    ~ProfilingSession.name.contains("kosz"),
                    UseCase.id == use_case_id,
                    TaskSizesDict.name == task_size,
                    Machine.name == machine_name,
                    AMDuProfPcm_machine_info.num_of_cores == num_of_cores,
                )
            )
            # for i, row in enumerate(db_session.execute(stmt).all()):
            #     print(i, row[0].name, row[0].use_case, row[1].name, row[2].name)
            row = db_session.execute(stmt).first()
            if row is not None:
                profiling_session, use_case, task_sizes_dict = row
                print(profiling_session.name, use_case.name, task_sizes_dict.name)
                x_range.append(task_sizes_dict.size / num_of_cores)
                x_tick_labels.append(f"{x_range[-1]} \n(\"{task_sizes_dict.name}\")")
                fvops.append(task_sizes_dict.size / profiling_session.exec_time_s)
                
                stmt = (
                    select(AMDuProfPcm_l3_metrics)
                    .where(AMDuProfPcm_l3_metrics.profiling_session == profiling_session.id)
                )
                l3_tmp = [row[0].l3_miss_percent for row in db_session.execute(stmt).all()]
                l3_miss_ratio.append(fsum(l3_tmp) / len(l3_tmp))

                # stmt = (
                #     select(AMDuProfPcm_core_metrics)
                #     .where(AMDuProfPcm_core_metrics.profiling_session == profiling_session.id)
                #     .join(AMDuProfPcm_metrics_dict)
                #     .where(AMDuProfPcm_metrics_dict.name == "L2 Miss (pti)")
                # )
                # l2_miss = db_session.execute(stmt).first()[0].value()
                # stmt = (
                #     select(AMDuProfPcm_core_metrics)
                #     .where(AMDuProfPcm_core_metrics.profiling_session == profiling_session.id)
                #     .join(AMDuProfPcm_metrics_dict)
                #     .where(AMDuProfPcm_metrics_dict.name == "L2 Access (pti)")
                # )
                # l2_access = [row[0].value for row in db_session.execute(stmt).all()]
                # l2_ratios[0].append()


    fig, axes = plt.subplots(1,num_of_figures,figsize=(num_of_figures*12,5))
    fig.subplots_adjust(left=0.05, bottom=0.07, right=0.97, top=0.95, wspace=0.4, hspace=0.4)

    # axis_r = [ax.twinx() for ax in axes]
    axis_r = [axes.twinx()]

    # make_figures(axes[0], axis_r[0], "rome128")
    make_figures(axes, axis_r[0], x_range, x_tick_labels, fvops, l2_ratios, l3_miss_ratio)

    # axes[0].set_title("2x 64-core 2.25 GHz AMD EPYC 7742 (Rome) ", fontsize="12")
    axes.set_title("2x 64-core 2.25 GHz AMD EPYC 7742 (Rome) ", fontsize="12")

    fig.savefig("./GRAPH.png", dpi=300)
    fig.savefig("./GRAPH.svg")
    plt.close()
    plt.cla()
    plt.clf()

if __name__ == "__main__":
    main()
