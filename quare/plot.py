from argparse import Namespace

from .extensions.AMDuProfMPI import plotter
from .extensions.AMDuProfPCM import plotter


def plot(_: Namespace) -> None:
    plotter.main()
    plotter.main()


if __name__ == "__main__":
    plot(Namespace())
