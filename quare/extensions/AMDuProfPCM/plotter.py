from ..amduprof_plotter_utils import make_all
from .models import AMDuProfPCM_metrics, AMDuProfPCM_metrics_dict


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
