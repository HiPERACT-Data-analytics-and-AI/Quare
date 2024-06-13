from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from db_models import Machine, ProfilingSession, Repetition, TaskSizesDict, UseCase

from .loaders_utils import create_if_not_exists, extract_from_path, record_exists


class InMemoryTables:
    task_sizes_dict: dict[str, int] = {}

    @classmethod
    def update_task_sizes_dict(cls, db_session: Session) -> None:
        task_sizes_dict_list = db_session.execute(
            select(TaskSizesDict.id, TaskSizesDict.name)
        ).all()
        cls.task_sizes_dict = {row[1]: row[0] for row in task_sizes_dict_list}


@dataclass
class MetricContext:
    path: Path
    repetition_id: int
    db_session: Session


def walk_through_data(
    data_dir_path: Path,
    db_session: Session,
    dir_name_pattern: str,
    file_suffixes: list[tuple[str, Callable[[MetricContext], list]]],
) -> None:
    InMemoryTables.update_task_sizes_dict(db_session)

    for input_path in Path(data_dir_path).glob(
        f"**/{dir_name_pattern}/**/*.{file_suffixes[0][0]}"
    ):
        repetition_name = (
            extract_from_path("repetition_&_date", data_dir_path, input_path)
            + "."
            + extract_from_path("session", data_dir_path, input_path)
        )
        if record_exists(
            db_session=db_session,
            where_column=Repetition.name,
            equal_to=repetition_name,
        ):
            continue

        name_base: str = input_path.name[: -len(file_suffixes[0][0])]

        session_name = extract_from_path("session", data_dir_path, input_path)
        profiling_session = ProfilingSession(name=session_name)
        profiling_session = create_if_not_exists(
            db_session=db_session,
            to_create=profiling_session,
            where_column=ProfilingSession.name,
            equal_to=session_name,
        )

        machine_name = extract_from_path("machine", data_dir_path, input_path)
        machine = Machine(name=machine_name)
        machine = create_if_not_exists(
            db_session=db_session,
            to_create=machine,
            where_column=Machine.name,
            equal_to=machine_name,
        )

        use_case_name = extract_from_path("use_case", data_dir_path, input_path)
        use_case = UseCase(name=use_case_name)
        use_case = create_if_not_exists(
            db_session=db_session,
            to_create=use_case,
            where_column=UseCase.name,
            equal_to=use_case_name,
        )

        task_size_name = extract_from_path("task_size", data_dir_path, input_path)
        try:
            task_size_size = int(task_size_name)
        except ValueError:
            task_size_size = None
        if task_size_name not in InMemoryTables.task_sizes_dict.keys():
            task_size = TaskSizesDict(name=task_size_name, size=task_size_size)
            db_session.add(task_size)
            db_session.commit()
            InMemoryTables.update_task_sizes_dict(db_session)

        db_session.commit()  # the commit needed to obtain the ids of the added objects

        repetition_date = repetition_name.split(".")[0]
        repetition = Repetition(
            name=repetition_name,
            profiling_session=profiling_session.id,
            machine=machine.id,
            use_case=use_case.id,
            task_size=InMemoryTables.task_sizes_dict[task_size_name],
            date=datetime.strptime(repetition_date, "%Y%m%d_%H%M%S"),
            file_dir=input_path.parent.as_posix(),
        )
        repetition = create_if_not_exists(
            db_session=db_session,
            to_create=repetition,
            where_column=Repetition.name,
            equal_to=repetition_name,
        )

        db_session.commit()

        general_path: Path = input_path.parent
        for suffix, function in file_suffixes:
            path: Path = general_path / (name_base + suffix)
            db_session.add_all(
                function(
                    MetricContext(
                        path=path, repetition_id=repetition.id, db_session=db_session
                    )
                )
            )
