from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd


@dataclass(slots=True)
class DatasetEntry:
    name: str
    path: str | None
    data: pd.DataFrame
    is_primary: bool = False
    added_at: datetime = field(default_factory=datetime.now)

    @property
    def rows(self) -> int:
        return len(self.data)

    @property
    def columns(self) -> int:
        return len(self.data.columns)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "path": self.path,
            "rows": self.rows,
            "columns": self.columns,
            "is_primary": self.is_primary,
            "added_at": self.added_at.isoformat(),
        }


@dataclass(slots=True)
class MergeReport:
    left_dataset: str
    right_dataset: str
    how: str

    left_rows: int
    right_rows: int
    output_rows: int

    matched_left_rows: int
    unmatched_left_rows: int

    duplicate_left_keys: int
    duplicate_right_keys: int

    relationship: str
    row_change: int

    join_columns: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def expanded_rows(self) -> int:
        return max(0, self.output_rows - self.left_rows)

    def to_dict(self) -> dict:
        return {
            "left_dataset": self.left_dataset,
            "right_dataset": self.right_dataset,
            "how": self.how,
            "join_columns": self.join_columns,
            "left_rows": self.left_rows,
            "right_rows": self.right_rows,
            "output_rows": self.output_rows,
            "matched_left_rows": self.matched_left_rows,
            "unmatched_left_rows": self.unmatched_left_rows,
            "duplicate_left_keys": self.duplicate_left_keys,
            "duplicate_right_keys": self.duplicate_right_keys,
            "relationship": self.relationship,
            "row_change": self.row_change,
            "expanded_rows": self.expanded_rows,
            "warnings": self.warnings,
        }


@dataclass(slots=True)
class ConcatReport:
    datasets: list[str]
    axis: int
    input_rows: int
    output_rows: int
    input_columns: int
    output_columns: int
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "datasets": self.datasets,
            "axis": self.axis,
            "input_rows": self.input_rows,
            "output_rows": self.output_rows,
            "input_columns": self.input_columns,
            "output_columns": self.output_columns,
            "warnings": self.warnings,
        }