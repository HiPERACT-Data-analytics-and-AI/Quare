from sqlalchemy.orm import Session

from ..amduprof_plotter_utils import make_all
from .models import AMDuProfPCM_metrics, AMDuProfPCM_metrics_dict


def plot(db_session: Session) -> None:
    """
    _summary_

    :param db_session: _description_
    """

    make_all(
        db_session,
        AMDuProfPCM_metrics,
        AMDuProfPCM_metrics_dict,
        "AMDuProfPCM",
    )
