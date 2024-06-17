from pathlib import Path

from sqlalchemy.orm import Session

from db_loaders.amduprofmpi_loader import load_mpiuprof
from db_loaders.amduprofpcm_loader import load_amduprofpcm
from db_models import DBBase
from utils import create_db_engine


def main():
    db_engine = create_db_engine()
    DBBase.metadata.create_all(db_engine)
    data_dir_path = Path("../quare-test-db/csvized_data")

    with Session(db_engine) as db_session:
        load_amduprofpcm(db_session, data_dir_path)
        load_mpiuprof(db_session, data_dir_path)

        db_session.commit()


if __name__ == "__main__":
    main()
