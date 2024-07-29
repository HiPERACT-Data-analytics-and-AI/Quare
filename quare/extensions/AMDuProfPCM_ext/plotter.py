from sqlalchemy.orm import Session

from ..amduprof_plotter_utils import Plotter
from .models import AMDuProfPCM_metrics, AMDuProfPCM_metrics_dict


def plot(db_session: Session) -> None:
    """
    _summary_

    :param db_session: _description_
    """

    Plotter(
        db_session,
        AMDuProfPCM_metrics,
        AMDuProfPCM_metrics_dict,
        "AMDuProfPCM",
    ).make_all()
