from db_models.amduprofpcm_models import AMDuProfPCM_metrics, AMDuProfPCM_metrics_dict

from .amduprof_plotter_utils import make_all


def main() -> None:
    """
    _summary_
    """
    metric_names: set[str] = set()
    metric_names: set[str] = {
        "L2 Access (pti)",
        "L2 Miss (pti)",
        "L2 Hit (pti)",
        "L3 Access",
    }

    session_name_contains: str = "Session1"
    machine_name: str = "ROME_128"
    use_case_name: str = "motorBike"
    sizes_to_get: tuple[str, ...] = (
        "xsmall",
        "small",
        "smid",
        "mid",
        "high",
        "mhigh",
        "uhigh",
        "xhigh",
    )
    repetition_name_contains: str = "Session1"

    make_all(
        AMDuProfPCM_metrics,
        AMDuProfPCM_metrics_dict,
        metric_names,
        session_name_contains,
        machine_name,
        use_case_name,
        sizes_to_get,
        repetition_name_contains,
        "AMDuProfPCM",
    )


if __name__ == "__main__":
    main()
