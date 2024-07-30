from sqlalchemy.orm import Session

from ...plotter import Plotter
from ..amduprof_data_retriever import AMDuProfDataRetriever
from .models import AMDuProfPCM_metrics, AMDuProfPCM_metrics_dict


def plot(db_session: Session) -> None:
    """
    _summary_

    :param db_session: _description_
    """
    Plotter(
        AMDuProfDataRetriever(
            db_session,
            AMDuProfPCM_metrics,
            AMDuProfPCM_metrics_dict,
        ),
        "AMDuProfPCM",
    ).make_all()
