from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from db_loaders.amduprofpcm_loader import load_uprof_pcm
from db_models import DBBase


def main():
    db_engine: Engine = create_engine("sqlite:///quare.sqlite3", echo=False)
    DBBase.metadata.create_all(db_engine)

    with Session(db_engine) as db_session:
        load_uprof_pcm(db_session)
        db_session.commit()


if __name__ == "__main__":
    main()
