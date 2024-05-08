from pathlib import Path
from typing import TypeVar

from sqlalchemy import select
from sqlalchemy.orm import InstrumentedAttribute, Session

from db_models import DBBase


def extract_from_path(key: str, path: Path) -> str:
    path_struct: dict[str, tuple[int, ...]] = {
        "use_case": (2,),
        "machine": (3,),
        "task_size": (5,),
        "session": (3, 4, 5, 6),
    }
    return ".".join(path.parts[i] for i in path_struct[key])


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
