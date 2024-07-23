from argparse import Namespace

from .extensions.AMDuProfMPI_ext import plotter as plotterMPI
from .extensions.AMDuProfPCM_ext import plotter as plotterPCM


def plot(_: Namespace) -> None:
    plotterMPI.main()
    plotterPCM.main()


if __name__ == "__main__":
    plot(Namespace())
