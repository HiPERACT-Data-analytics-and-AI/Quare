from sqlalchemy import create_engine

from db_models import DBBase

db_engine = create_engine("sqlite:///quare.sqlite3", echo=True)
DBBase.metadata.create_all(db_engine)
