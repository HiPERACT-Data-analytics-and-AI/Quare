from ..db_models.amduprofpcm_models import AMDuProfPCM_metrics, AMDuProfPCM_metrics_dict
from .amduprof_plotter_utils import make_all


def main() -> None:
    """
    _summary_
    """

    make_all(
        AMDuProfPCM_metrics,
        AMDuProfPCM_metrics_dict,
        "AMDuProfPCM",
    )


if __name__ == "__main__":
    main()
