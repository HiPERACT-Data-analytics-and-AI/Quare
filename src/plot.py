from argparse import Namespace

from plotters import amduprofmpi_metric_plotter, amduprofpcm_metric_plotter


def plot(_: Namespace) -> None:
    amduprofmpi_metric_plotter.main()
    amduprofpcm_metric_plotter.main()


if __name__ == "__main__":
    plot(Namespace())
