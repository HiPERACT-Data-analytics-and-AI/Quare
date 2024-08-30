from abc import ABC, abstractmethod
from pathlib import Path


class ExtensionDataLoader(ABC):
    @staticmethod
    @abstractmethod
    def load(data_dir_path: Path) -> None:
        pass


class ExtensionDataPlotter(ABC):
    @staticmethod
    @abstractmethod
    def plot() -> None:
        pass
