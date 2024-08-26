from sqlalchemy.orm import Session

from ...extensions_abcs import ExtensionDataPlotter
from ...plotter import Plotter
from ..amduprof_data_retriever import AMDuProfDataRetriever
from .models import AMDuProfMPI_metrics, AMDuProfMPI_metrics_dict


class ExtensionDataPlotterImpl(ExtensionDataPlotter):
    @staticmethod
    def plot(db_session: Session) -> None:
        """
        _summary_

        :param db_session: _description_
        """
        Plotter(
            AMDuProfDataRetriever(
                db_session,
                AMDuProfMPI_metrics,
                AMDuProfMPI_metrics_dict,
            ),
            "AMDuProfMPI",
        ).make_all()
