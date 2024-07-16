from ..db_models.amduprofmpi_models import AMDuProfMPI_metrics, AMDuProfMPI_metrics_dict
from .amduprof_plotter_utils import make_all


def main() -> None:
    """
    _summary_
    """

    make_all(
        AMDuProfMPI_metrics,
        AMDuProfMPI_metrics_dict,
        "AMDuProfMPI",
    )


if __name__ == "__main__":
    main()
