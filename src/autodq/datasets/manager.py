from pathlib import Path

import pandas as pd

from autodq.datasets.models import DatasetEntry
from autodq.io.loaders import load_dataset


class DatasetManager:
    """
    Stores and manages multiple named datasets in one AutoDQ project.
    """

    def __init__(self):
        self._datasets: dict[str, DatasetEntry] = {}

    def add(
        self,
        name: str,
        dataset_path: str | Path | None = None,
        data: pd.DataFrame | None = None,
        is_primary: bool = False,
        overwrite: bool = False,
    ) -> DatasetEntry:
        normalized_name = self._normalize_name(name)

        if normalized_name in self._datasets and not overwrite:
            raise ValueError(
                f"Dataset '{normalized_name}' already exists. "
                "Use overwrite=True to replace it."
            )

        if data is None and dataset_path is None:
            raise ValueError(
                "Provide either dataset_path or a pandas DataFrame."
            )

        if data is not None:
            loaded_data = data.copy()
            stored_path = (
                str(dataset_path)
                if dataset_path is not None
                else None
            )
        else:
            loaded_data = load_dataset(dataset_path)
            stored_path = str(dataset_path)

        if not isinstance(loaded_data, pd.DataFrame):
            raise TypeError(
                "Loaded dataset must be a pandas DataFrame."
            )

        if is_primary:
            for entry in self._datasets.values():
                entry.is_primary = False

        entry = DatasetEntry(
            name=normalized_name,
            path=stored_path,
            data=loaded_data,
            is_primary=is_primary,
        )

        self._datasets[normalized_name] = entry

        return entry

    def get(self, name: str) -> DatasetEntry:
        normalized_name = self._normalize_name(name)

        if normalized_name not in self._datasets:
            available = ", ".join(self.names()) or "none"

            raise KeyError(
                f"Dataset '{normalized_name}' was not found. "
                f"Available datasets: {available}"
            )

        return self._datasets[normalized_name]

    def get_data(self, name: str) -> pd.DataFrame:
        return self.get(name).data

    def remove(self, name: str) -> DatasetEntry:
        normalized_name = self._normalize_name(name)

        if normalized_name not in self._datasets:
            raise KeyError(
                f"Dataset '{normalized_name}' was not found."
            )

        return self._datasets.pop(normalized_name)

    def names(self) -> list[str]:
        return list(self._datasets.keys())

    def entries(self) -> list[DatasetEntry]:
        return list(self._datasets.values())

    def set_primary(self, name: str) -> DatasetEntry:
        selected = self.get(name)

        for entry in self._datasets.values():
            entry.is_primary = False

        selected.is_primary = True

        return selected

    def primary(self) -> DatasetEntry | None:
        for entry in self._datasets.values():
            if entry.is_primary:
                return entry

        return None

    def exists(self, name: str) -> bool:
        return self._normalize_name(name) in self._datasets

    def clear(self, keep_primary: bool = False) -> None:
        if not keep_primary:
            self._datasets.clear()
            return

        primary = self.primary()

        self._datasets.clear()

        if primary is not None:
            self._datasets[primary.name] = primary

    def _normalize_name(self, name: str) -> str:
        if not name or not name.strip():
            raise ValueError("Dataset name cannot be empty.")

        return name.strip()