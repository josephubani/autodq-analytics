import pandas as pd

from autodq.datasets.models import ConcatReport, MergeReport


class DatasetMerger:
    """
    Safely merges and concatenates datasets with validation reports.
    """

    VALID_RELATIONSHIPS = {
        "one_to_one",
        "one_to_many",
        "many_to_one",
        "many_to_many",
        "1:1",
        "1:m",
        "m:1",
        "m:m",
    }

    def merge(
        self,
        left_df: pd.DataFrame,
        right_df: pd.DataFrame,
        left_name: str,
        right_name: str,
        how: str = "left",
        on: str | list[str] | None = None,
        left_on: str | list[str] | None = None,
        right_on: str | list[str] | None = None,
        validate: str | None = None,
        suffixes: tuple[str, str] = ("_left", "_right"),
    ) -> tuple[pd.DataFrame, MergeReport]:
        self._validate_merge_arguments(
            left_df=left_df,
            right_df=right_df,
            on=on,
            left_on=left_on,
            right_on=right_on,
            validate=validate,
        )

        left_keys, right_keys = self._resolve_keys(
            on=on,
            left_on=left_on,
            right_on=right_on,
        )

        left_rows = len(left_df)
        right_rows = len(right_df)

        duplicate_left_keys = int(
            left_df.duplicated(subset=left_keys).sum()
        )
        duplicate_right_keys = int(
            right_df.duplicated(subset=right_keys).sum()
        )

        relationship = self._detect_relationship(
            duplicate_left_keys=duplicate_left_keys,
            duplicate_right_keys=duplicate_right_keys,
        )

        left_marker = "__autodq_left_row_id__"

        while left_marker in left_df.columns:
            left_marker = f"_{left_marker}"

        marked_left = left_df.copy()
        marked_left[left_marker] = range(left_rows)

        merged = pd.merge(
            marked_left,
            right_df,
            how=how,
            on=on,
            left_on=left_on,
            right_on=right_on,
            validate=validate,
            suffixes=suffixes,
            indicator=True,
        )

        matched_left_rows = int(
            merged.loc[
                merged["_merge"].isin(["both"]),
                left_marker,
            ].nunique()
        )

        unmatched_left_rows = max(
            0,
            left_rows - matched_left_rows,
        )

        output_rows = len(merged)

        warnings = self._build_merge_warnings(
            how=how,
            left_rows=left_rows,
            output_rows=output_rows,
            unmatched_left_rows=unmatched_left_rows,
            relationship=relationship,
            validate=validate,
        )

        merged = merged.drop(
            columns=[left_marker, "_merge"],
            errors="ignore",
        )

        report = MergeReport(
            left_dataset=left_name,
            right_dataset=right_name,
            how=how,
            left_rows=left_rows,
            right_rows=right_rows,
            output_rows=output_rows,
            matched_left_rows=matched_left_rows,
            unmatched_left_rows=unmatched_left_rows,
            duplicate_left_keys=duplicate_left_keys,
            duplicate_right_keys=duplicate_right_keys,
            relationship=relationship,
            row_change=output_rows - left_rows,
            join_columns=self._join_column_labels(
                left_keys,
                right_keys,
            ),
            warnings=warnings,
        )

        return merged, report

    def concat(
        self,
        datasets: list[pd.DataFrame],
        dataset_names: list[str],
        axis: int = 0,
        ignore_index: bool = True,
        join: str = "outer",
    ) -> tuple[pd.DataFrame, ConcatReport]:
        if len(datasets) < 2:
            raise ValueError(
                "At least two datasets are required for concatenation."
            )

        if axis not in [0, 1]:
            raise ValueError("axis must be 0 or 1.")

        input_rows = sum(len(df) for df in datasets)
        input_columns = sum(len(df.columns) for df in datasets)

        warnings: list[str] = []

        if axis == 0:
            column_sets = [
                set(df.columns)
                for df in datasets
            ]

            if any(
                column_set != column_sets[0]
                for column_set in column_sets[1:]
            ):
                warnings.append(
                    "Input datasets do not have identical columns. "
                    "Concatenation may create missing values."
                )

        if axis == 1:
            row_counts = [len(df) for df in datasets]

            if len(set(row_counts)) > 1:
                warnings.append(
                    "Input datasets have different row counts. "
                    "Horizontal concatenation may create missing values."
                )

        combined = pd.concat(
            datasets,
            axis=axis,
            ignore_index=ignore_index if axis == 0 else False,
            join=join,
        )

        report = ConcatReport(
            datasets=dataset_names,
            axis=axis,
            input_rows=input_rows,
            output_rows=len(combined),
            input_columns=input_columns,
            output_columns=len(combined.columns),
            warnings=warnings,
        )

        return combined, report

    def _validate_merge_arguments(
        self,
        left_df: pd.DataFrame,
        right_df: pd.DataFrame,
        on,
        left_on,
        right_on,
        validate,
    ) -> None:
        if on is None and (
            left_on is None or right_on is None
        ):
            raise ValueError(
                "Provide either 'on' or both 'left_on' and 'right_on'."
            )

        if on is not None and (
            left_on is not None or right_on is not None
        ):
            raise ValueError(
                "Use either 'on' or left_on/right_on, not both."
            )

        if validate is not None:
            if validate not in self.VALID_RELATIONSHIPS:
                raise ValueError(
                    f"Unsupported merge validation: {validate}"
                )

        left_keys, right_keys = self._resolve_keys(
            on=on,
            left_on=left_on,
            right_on=right_on,
        )

        missing_left = [
            column
            for column in left_keys
            if column not in left_df.columns
        ]

        missing_right = [
            column
            for column in right_keys
            if column not in right_df.columns
        ]

        if missing_left:
            raise ValueError(
                f"Left dataset is missing join columns: {missing_left}"
            )

        if missing_right:
            raise ValueError(
                f"Right dataset is missing join columns: {missing_right}"
            )

    def _resolve_keys(
        self,
        on,
        left_on,
        right_on,
    ) -> tuple[list[str], list[str]]:
        if on is not None:
            keys = [on] if isinstance(on, str) else list(on)
            return keys, keys

        left_keys = (
            [left_on]
            if isinstance(left_on, str)
            else list(left_on)
        )

        right_keys = (
            [right_on]
            if isinstance(right_on, str)
            else list(right_on)
        )

        if len(left_keys) != len(right_keys):
            raise ValueError(
                "left_on and right_on must contain the same "
                "number of columns."
            )

        return left_keys, right_keys

    def _detect_relationship(
        self,
        duplicate_left_keys: int,
        duplicate_right_keys: int,
    ) -> str:
        left_unique = duplicate_left_keys == 0
        right_unique = duplicate_right_keys == 0

        if left_unique and right_unique:
            return "one_to_one"

        if left_unique and not right_unique:
            return "one_to_many"

        if not left_unique and right_unique:
            return "many_to_one"

        return "many_to_many"

    def _join_column_labels(
        self,
        left_keys: list[str],
        right_keys: list[str],
    ) -> list[str]:
        labels = []

        for left_key, right_key in zip(
            left_keys,
            right_keys,
        ):
            if left_key == right_key:
                labels.append(left_key)
            else:
                labels.append(
                    f"{left_key} → {right_key}"
                )

        return labels

    def _build_merge_warnings(
        self,
        how: str,
        left_rows: int,
        output_rows: int,
        unmatched_left_rows: int,
        relationship: str,
        validate: str | None,
    ) -> list[str]:
        warnings = []

        if output_rows > left_rows:
            warnings.append(
                f"The merge expanded the left dataset by "
                f"{output_rows - left_rows} row(s)."
            )

        if unmatched_left_rows > 0:
            warnings.append(
                f"{unmatched_left_rows} left-side row(s) did not match."
            )

        if relationship == "many_to_many":
            warnings.append(
                "A many-to-many relationship was detected. "
                "This can multiply rows and distort totals."
            )

        if validate is None:
            warnings.append(
                "No pandas merge relationship validation was supplied."
            )

        if how == "inner" and output_rows < left_rows:
            warnings.append(
                "The inner merge removed unmatched left-side rows."
            )

        return warnings