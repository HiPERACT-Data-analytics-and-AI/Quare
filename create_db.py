from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from db_loaders.amduprofpcm_loader import load_amduprofpcm
from db_loaders.mpiuprof_loader import load_mpiuprof
from db_models import DBBase


def main():
    db_engine: Engine = create_engine("sqlite:///quare.sqlite3", echo=False)
    DBBase.metadata.create_all(db_engine)
    data_dir_path = Path("csvized_data")

    with Session(db_engine) as db_session:
        load_amduprofpcm(db_session, data_dir_path)
        load_mpiuprof(db_session, data_dir_path)
        
        db_session.commit()


if __name__ == "__main__":
    main()
