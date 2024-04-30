from matplotlib import pyplot as plt
from sqlalchemy import select
from sqlalchemy.orm import Session

# from db_models.amduprofpcm_models import (
#     AMDuProfPcm_core_metrics,
#     AMDuProfPcm_further_machine_info,
#     AMDuProfPcm_l3_metrics,
#     AMDuProfPcm_machine_cpu_topology,
#     AMDuProfPcm_machine_info,
#     AMDuProfPcm_metrics_dict,
# )
from db_models import (
    ProfilingSession,
    UseCase,
    TaskSizesDict,
)

from utils import create_db_engine


xRange = []
xticklabels = []

# for sizieId in MAP_MB_SIZES:
#     size = MB_SIZES[sizieId]
#     xRange.append( int(timing["rome128"][2][sizieId]/128) )
#     xticklabels.append( str(xRange[-1]) + "\n("+size+")")


def make_figures(axis_l, axis_r, key: str):
    # timing [totalSimpleTime, avgStepSimpleTime, domainSize, cellsPerCore, fvops ]
    axis_l.semilogx( xRange, timing[key][4], color="k", linestyle='dashed', linewidth=0.4 )
    axis_l.semilogx( xRange, timing[key][4], 'bo', markersize=8 , label="FVOPS" )

    #
    axis_r.semilogx( xRange, L2Ratios[key][0], "k", linestyle='dashed', linewidth=0.4   )
    axis_r.semilogx( xRange, L2Ratios[key][0], "C1d", label="L2 miss ratio (total)" )

    axis_r.semilogx( xRange, L2Ratios[key][1], "k", linestyle='dashed', linewidth=0.4   )
    axis_r.semilogx( xRange, L2Ratios[key][1], "C2d", label="L2 miss ratio from L1DC" )

    axis_r.semilogx( xRange, L2Ratios[key][2], "k", linestyle='dashed', linewidth=0.4   )
    axis_r.semilogx( xRange, L2Ratios[key][2], "C3d", label="L2 miss ratio from HWPF" )

    #
    axis_r.semilogx( xRange, L3missRatio[key], "k", linestyle='dashed', linewidth=0.4   )
    axis_r.semilogx( xRange, L3missRatio[key], "r*", markersize=8 ,label="L3 miss ratio" )

    axis_r.semilogx( xRange, MPITrace[key][ 1 ], "C6", linestyle='dashed', linewidth=0.4   )
    axis_r.semilogx( xRange, MPITrace[key][ 1 ], "C6P", label="MPI ratio based on avg comm time" )


    if key.find("enoa")>=0:
        axis_r.semilogx( xRange, BackendBoundMemory[key][0], "k", linestyle='dashed', linewidth=0.4   )
        axis_r.semilogx( xRange, BackendBoundMemory[key][0], "C7+", markersize=8 ,label="Backend Bound Memory" )

        axis_r.semilogx( xRange, BackendBoundMemory[key][2], "k", linestyle='dashed', linewidth=0.4   )
        axis_r.semilogx( xRange, BackendBoundMemory[key][2], "C8+", markersize=8 ,label="Frontend Bound" )

    axis_l.set_xticks( xRange )
    axis_l.set_xticklabels( xticklabels, fontsize="8" )
    axis_l.set_xlim(500, 400000 )

    axis_l.set_xlabel("Cells per rank (size name)")
    axis_l.set_ylim(1, 50000000 )
    axis_l.set_ylabel("FVOPS")
    axis_l.yaxis.get_major_formatter().set_scientific(False)
    axis_r.set_ylim(0, 100)
    axis_r.set_ylabel("Ratio [%]")
    axis_l.legend(loc='upper left', fontsize="8")
    axis_r.legend(loc='upper right', fontsize="8")


def main():
    use_case: int = 2
    sizes_to_get: tuple[str, ...] = ("uxlow", "ulow", "mlow", "low", "mid", "high")
    num_of_cores: int = 128

    with Session(create_db_engine()) as db_session:
        stmt = select(ProfilingSession, UseCase, TaskSizesDict)\
            .join(UseCase).join(TaskSizesDict)\
            .where(UseCase.id == use_case, TaskSizesDict.name == "mid", ~ProfilingSession.name.contains("kosz"))
        for row in db_session.execute(stmt).all():
            print(row[0].name, row[0].use_case, row[1].name, row[2].name)

    fig, axes = plt.subplots(1,4,figsize=(4*7,5))
    fig.subplots_adjust(left=0.05, bottom=0.07, right=0.97, top=0.95, wspace=0.4, hspace=0.4)

    axis_r = [ax.twinx() for ax in axes]

    make_figures(axes[0], axis_r[0], "rome128")
    make_figures(axes[1], axis_r[1], "milan128")
    make_figures(axes[2], axis_r[2], "milan128_X")
    make_figures(axes[3], axis_r[3], "genoa128")


    axes[0].set_title("2x 64-core 2.25 GHz AMD EPYC 7742 (Rome) ", fontsize="12")
    axes[1].set_title("2x 64-core 2.45 GHz AMD EPYC 7763 (Milan)", fontsize="12")
    axes[2].set_title("2x 64-core 2.20 GHz AMD EPYC 7773X (MilanX)", fontsize="12")
    axes[3].set_title("2x 64-core 3.10 GHz AMD EPYC 9554 (Genoa)", fontsize="12")

    fig.savefig("./figs_png/128_FVOPS_AOCC_MOTOR.png", dpi=300)
    fig.savefig("./figs_svg/128_FVOPS_AOCC_MOTOR.svg")
    plt.close()
    plt.cla()
    plt.clf()

if __name__ == "__main__":
    main()
