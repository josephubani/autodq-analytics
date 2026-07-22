from __future__ import annotations

from pathlib import Path

from autodq.commands.errors import ADQLValidationError
from autodq.commands.grammar import (
    AGGREGATE_FUNCTIONS,
    DATA_SOURCES,
    SUPPORTED_COMMANDS,
)


class ADQLValidator:
    """Validate parsed ADQL before any project operation is executed."""

    MAX_SOURCE_LENGTH = 100_000
    MAX_STATEMENTS = 100
    MAX_QUERY_ROWS = 10_000
    MAX_WHERE_CONDITIONS = 50

    def validate(self, script) -> None:
        if len(script.source) > self.MAX_SOURCE_LENGTH:
            raise ADQLValidationError(
                f"ADQL source exceeds {self.MAX_SOURCE_LENGTH:,} characters."
            )

        if script.statement_count > self.MAX_STATEMENTS:
            raise ADQLValidationError(
                f"ADQL scripts support at most {self.MAX_STATEMENTS} statements."
            )

        for statement in script.statements:
            try:
                self._validate_statement(statement)
            except ADQLValidationError as error:
                message = str(error)

                if not message.startswith("Statement "):
                    message = f"Statement {statement.statement_number}: {message}"

                raise ADQLValidationError(message) from error

    def _validate_statement(self, statement) -> None:
        if statement.kind not in SUPPORTED_COMMANDS:
            raise ADQLValidationError(
                f"Command is not allowlisted: {statement.kind}."
            )

        if statement.kind == "SELECT":
            self._validate_select(statement.parameters)
            return

        parameters = statement.parameters

        if statement.kind == "DATASET":
            dataset_path = Path(parameters["dataset_path"])

            if "\x00" in str(dataset_path):
                raise ADQLValidationError(
                    "DATASET path contains an invalid null character."
                )

            if dataset_path.suffix.lower() not in {".csv", ".xlsx", ".xls"}:
                raise ADQLValidationError(
                    "DATASET path must end with .csv, .xlsx, or .xls."
                )

        elif statement.kind == "AUTO":
            mode = str(parameters.get("mode", "review")).lower()

            if mode not in {"review", "clean", "full"}:
                raise ADQLValidationError(
                    "AUTO MODE must be review, clean, or full."
                )

        elif statement.kind == "MODEL":
            if parameters.get("action") in {"save", "load"}:
                return
            test_size = parameters.get("test_size")

            if test_size is not None and not 0 < test_size < 1:
                raise ADQLValidationError(
                    "MODEL TEST_SIZE must be between 0 and 1."
                )

        elif statement.kind == "PREDICT":
            confidence = parameters.get("confidence_level")

            if confidence is not None and not 0 < confidence < 1:
                raise ADQLValidationError(
                    "PREDICT CONFIDENCE must be between 0 and 1."
                )

            threshold = parameters.get("low_confidence_threshold")

            if threshold is not None and not 0 <= threshold <= 1:
                raise ADQLValidationError(
                    "LOW_CONFIDENCE must be between 0 and 1."
                )

        elif statement.kind == "EXPLAIN":
            if parameters.get("max_rows", 1) < 1:
                raise ADQLValidationError("EXPLAIN MAX_ROWS must be positive.")

        elif statement.kind == "SHAP":
            if parameters.get("row", 0) < 0:
                raise ADQLValidationError("SHAP ROW cannot be negative.")
            if parameters.get("chart", "summary").lower() not in {
                "summary", "bar", "beeswarm", "waterfall", "dependence"
            }:
                raise ADQLValidationError("Unsupported SHAP chart type.")

        elif statement.kind == "ADD":
            suffix = Path(parameters["dataset_path"]).suffix.lower()
            if suffix not in {".csv", ".xlsx", ".xls"}:
                raise ADQLValidationError(
                    "ADD DATASET path must end with .csv, .xlsx, or .xls."
                )

        elif statement.kind == "OUTLIERS":
            multiplier = parameters.get("iqr_multiplier")
            if multiplier is not None and multiplier <= 0:
                raise ADQLValidationError("OUTLIERS IQR must be positive.")

        elif statement.kind == "CORRELATION":
            threshold = parameters.get("min_abs_correlation")
            if threshold is not None and not 0 <= threshold <= 1:
                raise ADQLValidationError(
                    "CORRELATION MIN_ABS must be between 0 and 1."
                )

        elif statement.kind == "BLUE":
            if parameters.get("max_features", 1) < 1:
                raise ADQLValidationError("BLUE MAX_FEATURES must be positive.")
            significance = parameters.get("significance_level")
            if significance is not None and not 0 < significance < 1:
                raise ADQLValidationError(
                    "BLUE SIGNIFICANCE must be between 0 and 1."
                )

        elif statement.kind == "AUDIT":
            if Path(parameters["output"]).suffix.lower() not in {".json", ".csv"}:
                raise ADQLValidationError(
                    "AUDIT EXPORT output must end with .json or .csv."
                )

        elif statement.kind == "GALLERY":
            if parameters.get("format", "png").lower() not in {
                "png", "svg", "pdf", "jpg", "jpeg"
            }:
                raise ADQLValidationError("Unsupported GALLERY export format.")

        elif statement.kind == "DASHBOARD":
            output = parameters.get("output")

            if output is not None and Path(output).suffix.lower() != ".html":
                raise ADQLValidationError(
                    "DASHBOARD SAVE output must end with .html."
                )

        elif statement.kind == "REPORT":
            suffix = Path(parameters["output"]).suffix.lower()

            if suffix not in {".html", ".json"}:
                raise ADQLValidationError(
                    "REPORT output must end with .html or .json."
                )

        elif statement.kind == "EXPORT":
            source = parameters["source"].upper()

            if source not in DATA_SOURCES:
                supported = ", ".join(DATA_SOURCES)
                raise ADQLValidationError(
                    f"Unsupported EXPORT source: {source}. Use {supported}."
                )

            suffix = Path(parameters["output"]).suffix.lower()

            if suffix not in {".csv", ".xlsx"}:
                raise ADQLValidationError(
                    "EXPORT output must end with .csv or .xlsx."
                )

        elif statement.kind == "HELP":
            command = parameters.get("command")

            if command is not None and command not in SUPPORTED_COMMANDS:
                raise ADQLValidationError(
                    f"HELP command is not recognized: {command}."
                )

    def _validate_select(self, parameters) -> None:
        items = parameters["select"]
        group_by = parameters["group_by"]
        where = parameters["where"]
        limit = parameters["limit"]

        if not items:
            raise ADQLValidationError(
                "SELECT requires at least one expression."
            )

        wildcard_items = [item for item in items if item["kind"] == "wildcard"]

        if wildcard_items and len(items) != 1:
            raise ADQLValidationError(
                "SELECT * cannot be combined with other expressions."
            )

        aliases = [
            item["alias"]
            for item in items
            if item.get("alias") is not None
        ]

        if len({item.casefold() for item in aliases}) != len(aliases):
            raise ADQLValidationError(
                "SELECT output aliases must be unique."
            )

        aggregates = [
            item for item in items if item["kind"] == "aggregate"
        ]
        columns = [item for item in items if item["kind"] == "column"]

        for item in aggregates:
            if item["function"] not in AGGREGATE_FUNCTIONS:
                raise ADQLValidationError(
                    f"Unsupported aggregate: {item['function']}."
                )

            if item["column"] == "*" and item["function"] != "COUNT":
                raise ADQLValidationError(
                    "Only COUNT may aggregate the * expression."
                )

        if aggregates and columns:
            if not group_by:
                raise ADQLValidationError(
                    "Non-aggregate SELECT columns require GROUP BY when "
                    "aggregates are present."
                )

            missing = [
                item["column"]
                for item in columns
                if item["column"] not in group_by
            ]

            if missing:
                raise ADQLValidationError(
                    "SELECT columns missing from GROUP BY: "
                    + ", ".join(missing)
                )

        if len(group_by) != len(set(group_by)):
            raise ADQLValidationError(
                "GROUP BY columns cannot be repeated."
            )

        if len(where) > self.MAX_WHERE_CONDITIONS:
            raise ADQLValidationError(
                f"WHERE supports at most {self.MAX_WHERE_CONDITIONS} conditions."
            )

        if limit is not None and limit > self.MAX_QUERY_ROWS:
            raise ADQLValidationError(
                f"LIMIT cannot exceed {self.MAX_QUERY_ROWS:,} rows."
            )
