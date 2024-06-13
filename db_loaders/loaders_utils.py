from pathlib import Path
from typing import TypeVar

from sqlalchemy import select
from sqlalchemy.orm import InstrumentedAttribute, Session

from db_models import DBBase


def extract_from_path(key: str, data_dir_path: Path, file_path: Path) -> str:
    path_struct: dict[str, tuple[int, ...]] = {
        "session": (0,),
        "machine": (1,),
        "use_case": (2,),
        "task_size": (3,),
        "repetition_&_date": (4, 0),
    }
    file_path = file_path.relative_to(data_dir_path)
    return ".".join(file_path.parts[i] for i in path_struct[key])


DBBaseModel = TypeVar("DBBaseModel", bound=DBBase)
T = TypeVar("T")


def create_if_not_exists(
    db_session: Session,
    to_create: DBBaseModel,
    where_column: InstrumentedAttribute[T],
    equal_to: T,
) -> DBBaseModel:
    selected_row = db_session.execute(
        select(where_column.parent).where(where_column == equal_to)
    ).first()

    if not selected_row:
        db_session.add(to_create)  # needs a commit after returning <- add to docs
        return to_create
    return selected_row[0]


def record_exists(
    db_session: Session,
    where_column: InstrumentedAttribute[T],
    equal_to: T,
) -> bool:
    selected_row = db_session.execute(
        select(where_column.parent).where(where_column == equal_to)
    ).first()
    return bool(selected_row)
