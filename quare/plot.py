from argparse import Namespace

from .extensions.AMDuProfMPI import plotter as plotterMPI
from .extensions.AMDuProfPCM import plotter as plotterPCM


def plot(_: Namespace) -> None:
    plotterMPI.main()
    plotterPCM.main()


if __name__ == "__main__":
    plot(Namespace())
