from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from time import perf_counter
from typing import Any

import pandas as pd

from autodq.commands.errors import ADQLExecutionError
from autodq.commands.grammar import COMMAND_HELP, DATA_SOURCES
from autodq.commands.models import ADQLResult, ADQLRunResult


class ADQLExecutor:
    """Execute validated ADQL exclusively through allowlisted operations."""

    DEFAULT_QUERY_LIMIT = 1_000
    MAX_HISTORY = 25

    def execute(
        self,
        project,
        script,
        *,
        continue_on_error: bool = False,
        auto_display: bool = True,
        source_name: str = "notebook",
        base_path: str | Path | None = None,
    ) -> ADQLRunResult:
        run = ADQLRunResult(
            script=script,
            source_name=source_name,
            auto_display=auto_display,
        )

        for statement in script.statements:
            started = perf_counter()

            try:
                output = self._execute_statement(
                    project,
                    statement,
                    base_path=(
                        Path(base_path).expanduser()
                        if base_path is not None
                        else None
                    ),
                )
                result = ADQLResult(
                    statement=statement,
                    status="completed",
                    message=output.get(
                        "message",
                        f"{statement.kind} completed.",
                    ),
                    data=output.get("data"),
                    value=output.get("value"),
                    total_rows=output.get("total_rows"),
                    duration_seconds=round(perf_counter() - started, 4),
                )
            except Exception as error:
                result = ADQLResult(
                    statement=statement,
                    status="failed",
                    message=f"{statement.kind} failed.",
                    duration_seconds=round(perf_counter() - started, 4),
                    error_type=type(error).__name__,
                    error_message=str(error),
                )
                run.results.append(result)

                if not continue_on_error:
                    run.finished_at = datetime.now()
                    raise ADQLExecutionError(
                        f"Statement {statement.statement_number} "
                        f"({statement.kind}) failed: {error}",
                        statement=statement,
                        result=run,
                        cause=error,
                    ) from error

                continue

            run.results.append(result)

        run.finished_at = datetime.now()
        return run

    def _execute_statement(
        self,
        project,
        statement,
        *,
        base_path: Path | None = None,
    ) -> dict[str, Any]:
        kind = statement.kind
        parameters = self._resolve_path_parameters(
            kind,
            statement.parameters,
            base_path=base_path,
        )

        if kind == "DATASET":
            data = project.change_dataset(parameters["dataset_path"])
            target = parameters.get("target")

            if target is not None:
                project.set_target(target)

            return {
                "data": data,
                "total_rows": len(data),
                "value": {
                    "dataset_path": str(project.dataset_path),
                    "target": project.target,
                },
                "message": (
                    f"Loaded standalone dataset {project.dataset_path} "
                    f"with {len(data):,} rows."
                ),
            }

        if kind == "SELECT":
            return self._execute_select(project, parameters)

        simple = {
            "LOAD": project.load,
            "PROFILE": project.profile,
            "STATISTICS": project.statistics,
            "INTERPRET": project.interpret,
            "DIAGNOSE": project.diagnose,
            "RECOMMEND": project.recommend,
            "DECIDE": project.decide,
            "PREVIEW": project.preview,
            "REVIEW": lambda: project.review_cleaning(auto_display=False),
            "CLEAN": project.clean,
            "VALIDATE": project.validate_cleaning,
        }

        if kind in simple:
            value = simple[kind]()
            return {
                "data": value if isinstance(value, pd.DataFrame) else None,
                "value": None if isinstance(value, pd.DataFrame) else value,
                "total_rows": len(value) if isinstance(value, pd.DataFrame) else None,
                "message": f"{kind.title()} completed through the project API.",
            }

        if kind == "AUTO":
            parameters.setdefault("auto_display", False)
            value = project.auto(**parameters)
            return {
                "value": value,
                "message": (
                    f"Automatic {value.config.mode} workflow completed with "
                    f"{value.failed_count} failed stage(s)."
                ),
            }

        if kind == "VISUALIZE":
            parameters.setdefault("chart", "auto")
            parameters.setdefault("display", False)
            value = project.visualize(**parameters)
            return {
                "value": value,
                "message": (
                    f"Generated {value.chart_count} visualization(s)."
                    if value is not None
                    else "No visualization was generated."
                ),
            }

        if kind == "MODEL":
            target = parameters.pop("target", None)

            if target is not None:
                project.set_target(target)

            value = project.model(**parameters)
            return {
                "value": value,
                "message": (
                    f"Trained {value.algorithm} for target {value.target}."
                ),
            }

        if kind == "PREDICT":
            data = project.predict(**parameters)
            report = project.state.prediction_report
            return {
                "data": data,
                "value": report,
                "total_rows": len(data),
                "message": (
                    f"Generated {len(data):,} predictions using "
                    f"{report.algorithm}."
                ),
            }

        if kind == "DASHBOARD":
            parameters.setdefault("auto_display", False)
            value = project.dashboard(**parameters)
            return {
                "value": value,
                "message": (
                    f"Generated dashboard with {value.chart_count} chart(s)"
                    + (
                        f" at {value.path}."
                        if value.path is not None
                        else "."
                    )
                ),
            }

        if kind == "APPROVE":
            value = (
                project.approve_all()
                if parameters["all"]
                else project.approve(parameters["action_ids"])
            )
            return {
                "value": value,
                "message": (
                    f"Cleaning review now has {value.approved_count} "
                    "approved action(s)."
                ),
            }

        if kind == "REJECT":
            value = project.reject(**parameters)
            return {
                "value": value,
                "message": (
                    f"Cleaning review now has {value.rejected_count} "
                    "rejected action(s)."
                ),
            }

        if kind == "REPORT":
            overwrite = parameters.pop("overwrite", False)
            output = Path(parameters["output"]).expanduser()
            self._ensure_output_available(output, overwrite)
            project.generate_report(**parameters)
            return {
                "value": output.resolve(),
                "message": f"Exported project report to {output.resolve()}.",
            }

        if kind == "EXPORT":
            source = DATA_SOURCES[parameters["source"].upper()]
            output = Path(parameters["output"]).expanduser()
            overwrite = bool(parameters.get("overwrite", False))
            self._ensure_output_available(output, overwrite)
            exporters = {
                "current": project.export_current,
                "cleaned": project.export_cleaned,
                "engineered": project.export_engineered,
                "predictions": project.export_predictions,
            }
            exporters[source](str(output))

            if not output.exists():
                raise RuntimeError(
                    f"{source.title()} data is unavailable for export."
                )

            return {
                "value": output.resolve(),
                "message": f"Exported {source} data to {output.resolve()}.",
            }

        if kind == "SET":
            if parameters["setting"] == "target":
                project.set_target(parameters["target"])
                value = parameters["target"]
                message = f"Set the project target to {value}."
            else:
                project.set_type(parameters["column"], parameters["dtype"])
                value = {
                    "column": parameters["column"],
                    "dtype": parameters["dtype"],
                }
                message = (
                    f"Set {parameters['column']} to {parameters['dtype']}."
                )

            return {"value": value, "message": message}

        if kind == "USE":
            data = project.use_dataset(parameters["dataset"])
            return {
                "data": data,
                "total_rows": len(data),
                "message": (
                    f"Activated dataset {parameters['dataset']} with "
                    f"{len(data):,} rows."
                ),
            }

        if kind in {"HEAD", "TAIL"}:
            data = getattr(project, kind.lower())(parameters["rows"])
            return {
                "data": data,
                "total_rows": len(data),
                "message": f"Returned {len(data):,} {kind.lower()} row(s).",
            }

        if kind == "SAMPLE":
            data = project.sample(
                n=parameters["rows"],
                random_state=parameters.get("random_state", 42),
            )
            return {
                "data": data,
                "total_rows": len(data),
                "message": f"Returned a {len(data):,}-row sample.",
            }

        if kind == "HELP":
            command = parameters.get("command")
            rows = [
                item
                for item in COMMAND_HELP
                if command is None
                or command in item["command"].replace(" / ", " ").split()
            ]
            data = pd.DataFrame(rows)
            return {
                "data": data,
                "total_rows": len(data),
                "message": (
                    f"ADQL help for {command}."
                    if command is not None
                    else "ADQL command reference."
                ),
            }

        if kind == "HISTORY":
            data = self._history_frame(project, parameters["limit"])
            return {
                "data": data,
                "total_rows": len(data),
                "message": f"Returned {len(data):,} previous ADQL run(s).",
            }

        raise RuntimeError(f"Execution is not implemented for {kind}.")

    def _execute_select(self, project, parameters) -> dict[str, Any]:
        source_name = parameters["source"]
        frame = self._source_frame(project, source_name).copy()
        filtered = self._apply_conditions(frame, parameters["where"])
        items = parameters["select"]
        aggregates = [
            item for item in items if item["kind"] == "aggregate"
        ]

        self._validate_runtime_columns(
            filtered,
            items=items,
            group_by=parameters["group_by"],
            conditions=parameters["where"],
        )

        if aggregates:
            selected = self._aggregate(
                filtered,
                items=items,
                group_by=parameters["group_by"],
            )
        else:
            selected = self._project_columns(filtered, items)

            if parameters["group_by"]:
                selected = selected.drop_duplicates()

        if parameters["distinct"]:
            selected = selected.drop_duplicates()

        order_by = parameters["order_by"]

        if order_by:
            columns = [item["column"] for item in order_by]
            missing = [column for column in columns if column not in selected.columns]

            if missing:
                raise ValueError(
                    "ORDER BY columns are not present in the query output: "
                    + ", ".join(missing)
                )

            selected = selected.sort_values(
                by=columns,
                ascending=[item["ascending"] for item in order_by],
                kind="mergesort",
                na_position="last",
            )

        total_rows = len(selected)
        requested_limit = parameters["limit"]
        applied_limit = requested_limit or self.DEFAULT_QUERY_LIMIT
        selected = selected.head(applied_limit).reset_index(drop=True)
        limited = total_rows > len(selected)
        message = (
            f"Selected {len(selected):,} row(s) from {source_name} data"
            + (
                f" ({total_rows:,} matched; limited to {applied_limit:,})."
                if limited
                else "."
            )
        )
        return {
            "data": selected,
            "total_rows": total_rows,
            "message": message,
        }

    def _source_frame(self, project, source: str) -> pd.DataFrame:
        if project.state.data is None:
            project.load()

        frames = {
            "current": project.state.data,
            "cleaned": project.state.cleaned_data,
            "engineered": project.state.engineered_data,
            "predictions": project.state.prediction_data,
        }
        frame = frames[source]

        if frame is None:
            guidance = {
                "cleaned": "Run CLEAN first.",
                "engineered": "Run project.apply_features() first.",
                "predictions": "Run MODEL and PREDICT first.",
            }.get(source, "Load the project data first.")
            raise ValueError(f"{source.title()} data is unavailable. {guidance}")

        return frame

    def _apply_conditions(
        self,
        frame: pd.DataFrame,
        conditions: list[dict[str, Any]],
    ) -> pd.DataFrame:
        if not conditions:
            return frame

        mask = pd.Series(True, index=frame.index, dtype=bool)

        for condition in conditions:
            column = condition["column"]

            if column not in frame.columns:
                raise ValueError(f"WHERE column was not found: {column}")

            series = frame[column]
            operator = condition["operator"]
            value = condition["value"]

            try:
                current = self._condition_mask(series, operator, value)
            except (TypeError, ValueError) as error:
                raise ValueError(
                    f"Cannot apply {operator} to column {column}: {error}"
                ) from error

            mask &= current.fillna(False).astype(bool)

        return frame.loc[mask]

    @staticmethod
    def _condition_mask(series, operator: str, value: Any):
        if operator == "IS NULL":
            return series.isna()

        if operator == "IS NOT NULL":
            return series.notna()

        if operator == "IN":
            return series.isin(value)

        if operator == "NOT IN":
            return ~series.isin(value)

        if operator in {"CONTAINS", "STARTS WITH", "ENDS WITH"}:
            text = series.astype("string")
            needle = str(value)

            if operator == "CONTAINS":
                return text.str.contains(
                    re.escape(needle),
                    case=False,
                    regex=True,
                    na=False,
                )

            if operator == "STARTS WITH":
                return text.str.lower().str.startswith(needle.lower(), na=False)

            return text.str.lower().str.endswith(needle.lower(), na=False)

        if value is None:
            raise ValueError("Use IS NULL or IS NOT NULL for null values.")

        comparison_value = value

        if pd.api.types.is_datetime64_any_dtype(series) and isinstance(value, str):
            comparison_value = pd.Timestamp(value)

        comparisons = {
            "=": lambda: series == comparison_value,
            "!=": lambda: series != comparison_value,
            "<": lambda: series < comparison_value,
            "<=": lambda: series <= comparison_value,
            ">": lambda: series > comparison_value,
            ">=": lambda: series >= comparison_value,
        }
        return comparisons[operator]()

    @staticmethod
    def _validate_runtime_columns(
        frame: pd.DataFrame,
        *,
        items,
        group_by,
        conditions,
    ) -> None:
        required = set(group_by)
        required.update(condition["column"] for condition in conditions)

        for item in items:
            if item["kind"] != "wildcard" and item["column"] != "*":
                required.add(item["column"])

        missing = [column for column in required if column not in frame.columns]

        if missing:
            raise ValueError(
                "ADQL columns were not found: " + ", ".join(sorted(missing))
            )

    @staticmethod
    def _project_columns(frame: pd.DataFrame, items) -> pd.DataFrame:
        if items[0]["kind"] == "wildcard":
            return frame.copy()

        return pd.concat(
            [
                frame[item["column"]].rename(item["alias"])
                for item in items
            ],
            axis=1,
        )

    def _aggregate(self, frame, *, items, group_by) -> pd.DataFrame:
        aggregate_items = [
            item for item in items if item["kind"] == "aggregate"
        ]

        if not group_by:
            values = {}

            for item in items:
                if item["kind"] == "aggregate":
                    values[item["alias"]] = self._aggregate_series(
                        frame,
                        item,
                    )

            return pd.DataFrame([values])

        work = frame.copy()
        count_column = "__adql_row_count__"

        while count_column in work.columns:
            count_column = "_" + count_column

        work[count_column] = 1
        named_aggregations = {}

        for item in aggregate_items:
            function = item["function"]
            column = item["column"]

            if function == "COUNT" and column == "*":
                named_aggregations[item["alias"]] = (
                    count_column,
                    "sum",
                )
            else:
                named_aggregations[item["alias"]] = (
                    column,
                    self._pandas_aggregation(function),
                )

        grouped = work.groupby(group_by, dropna=False, sort=False)

        if named_aggregations:
            result = grouped.agg(**named_aggregations).reset_index()
        else:
            result = work.loc[:, group_by].drop_duplicates().reset_index(drop=True)

        output_columns = []
        rename = {}

        for item in items:
            if item["kind"] == "column":
                output_columns.append(item["column"])
                rename[item["column"]] = item["alias"]
            elif item["kind"] == "aggregate":
                output_columns.append(item["alias"])

        return result.loc[:, output_columns].rename(columns=rename)

    def _aggregate_series(self, frame, item):
        function = item["function"]
        column = item["column"]

        if function == "COUNT" and column == "*":
            return int(len(frame))

        series = frame[column]
        operations = {
            "COUNT": series.count,
            "SUM": series.sum,
            "AVG": series.mean,
            "MEAN": series.mean,
            "MIN": series.min,
            "MAX": series.max,
            "MEDIAN": series.median,
            "NUNIQUE": series.nunique,
        }
        return operations[function]()

    @staticmethod
    def _pandas_aggregation(function: str) -> str:
        return {
            "COUNT": "count",
            "SUM": "sum",
            "AVG": "mean",
            "MEAN": "mean",
            "MIN": "min",
            "MAX": "max",
            "MEDIAN": "median",
            "NUNIQUE": "nunique",
        }[function]

    @staticmethod
    def _ensure_output_available(output: Path, overwrite: bool) -> None:
        if output.exists() and not overwrite:
            raise FileExistsError(
                f"Output already exists: {output}. Add OVERWRITE to replace it."
            )

    @staticmethod
    def _resolve_path_parameters(
        kind: str,
        parameters: dict[str, Any],
        *,
        base_path: Path | None,
    ) -> dict[str, Any]:
        resolved = dict(parameters)

        if base_path is None:
            return resolved

        path_options = {
            "DATASET": "dataset_path",
            "DASHBOARD": "output",
            "REPORT": "output",
            "EXPORT": "output",
            "VISUALIZE": "save",
        }
        option = path_options.get(kind)

        if option is None or resolved.get(option) is None:
            return resolved

        path = Path(resolved[option]).expanduser()

        if not path.is_absolute():
            path = base_path / path

        resolved[option] = str(path.resolve())
        return resolved

    @staticmethod
    def _history_frame(project, limit: int) -> pd.DataFrame:
        history = list(project.state.adql_history)[-limit:]
        rows = []

        for index, run in enumerate(reversed(history), start=1):
            rows.append(
                {
                    "run": index,
                    "source": run.source_name,
                    "status": "completed" if run.success else "failed",
                    "statements": run.statement_count,
                    "completed": run.completed_count,
                    "failed": run.failed_count,
                    "duration_seconds": run.duration_seconds,
                    "started_at": run.started_at.isoformat(),
                }
            )

        return pd.DataFrame(
            rows,
            columns=[
                "run",
                "source",
                "status",
                "statements",
                "completed",
                "failed",
                "duration_seconds",
                "started_at",
            ],
        )
