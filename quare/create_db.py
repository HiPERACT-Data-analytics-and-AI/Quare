from argparse import Namespace
from pathlib import Path

from sqlalchemy.orm import Session

from .extensions.AMDuProfMPI_ext.loader import load_mpiuprof
from .extensions.AMDuProfPCM_ext.loader import load_amduprofpcm
from .models import DBBase
from .utils import create_db_engine, load_settings


def create_db(_: Namespace):
    """
    Creates Quare's DB using custom loaders for different profilers.
    """
    db_engine = create_db_engine()
    DBBase.metadata.create_all(db_engine)
    settings = load_settings()
    data_dir_path = Path(settings["csvized_data_directory_path"])

    with Session(db_engine) as db_session:
        load_amduprofpcm(db_session, data_dir_path)
        load_mpiuprof(db_session, data_dir_path)

        db_session.commit()


if __name__ == "__main__":
    create_db(Namespace())
