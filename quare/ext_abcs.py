from abc import ABC, abstractmethod
from pathlib import Path

from sqlalchemy.orm import Session


class ExtensionDataLoader(ABC):
    @staticmethod
    @abstractmethod
    def load(db_session: Session, data_dir_path: Path) -> None:
        pass


class ExtensionDataPlotter(ABC):
    @staticmethod
    @abstractmethod
    def plot(db_session: Session) -> None:
        pass
