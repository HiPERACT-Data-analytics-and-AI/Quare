from matplotlib import pyplot as plt


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
    session_names: tuple[str, ...] = (
        "C_AOCC_9554_Sumup.high.0",
        "C_AOCC_7763_MILAN_Sumup.high.0",
        "C_AOCC_7773X_MILAN_X_Sumup.high.0",
        "C_AOCC_7742_ROME_Sumup.high.0",
    )
    
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
