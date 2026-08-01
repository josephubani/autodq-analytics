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
        dataset_name = parameters.get("dataset_name")

        if dataset_name is not None and (
            not str(dataset_name).strip()
            or len(str(dataset_name)) > 255
            or any(
                character in str(dataset_name)
                for character in ";\r\n"
            )
        ):
            raise ADQLValidationError(
                "DATASET selector must contain a valid registered dataset name."
            )

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

            test_size = parameters.get("test_size")

            if test_size is not None and not 0 < test_size < 1:
                raise ADQLValidationError(
                    "AUTO TEST_SIZE must be between 0 and 1."
                )

            random_state = parameters.get("random_state")

            if random_state is not None and (
                not isinstance(random_state, int)
                or isinstance(random_state, bool)
            ):
                raise ADQLValidationError(
                    "AUTO RANDOM_STATE must be an integer."
                )

            report_output = parameters.get("report_output")

            if report_output is not None and Path(report_output).suffix.lower() not in {
                ".html",
                ".json",
            }:
                raise ADQLValidationError(
                    "AUTO REPORT must end with .html or .json."
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

        elif statement.kind == "MISSING":
            action = parameters.get("action")

            if action == "summary":
                return

            columns = parameters.get("columns")

            if columns is not None and (
                not columns
                or any(
                    not str(column).strip()
                    or len(str(column)) > 255
                    or any(
                        character in str(column)
                        for character in ";\r\n"
                    )
                    for column in columns
                )
            ):
                raise ADQLValidationError(
                    "MISSING columns must be valid non-empty column names."
                )

            if action == "fill":
                strategy = str(
                    parameters.get("strategy", "auto")
                ).lower()
                supported = {
                    "auto",
                    "constant",
                    "mean",
                    "median",
                    "mode",
                    "zero",
                    "ffill",
                    "bfill",
                    "interpolate",
                }

                if strategy not in supported:
                    raise ADQLValidationError(
                        "MISSING FILL STRATEGY must be auto, constant, mean, "
                        "median, mode, zero, ffill, bfill, or interpolate."
                    )

                has_value = "value" in parameters

                if strategy == "constant" and (
                    not has_value or parameters.get("value") is None
                ):
                    raise ADQLValidationError(
                        "MISSING FILL constant requires a non-null VALUE."
                    )

                if strategy != "constant" and has_value:
                    raise ADQLValidationError(
                        "MISSING FILL VALUE may only be used with "
                        "STRATEGY constant."
                    )

            elif action == "drop_rows":
                if str(parameters.get("how", "any")).lower() not in {
                    "any",
                    "all",
                }:
                    raise ADQLValidationError(
                        "MISSING DROP ROWS HOW must be any or all."
                    )

            elif action == "drop_columns":
                min_percent = parameters.get("min_percent")

                if min_percent is not None and not 0 <= min_percent <= 100:
                    raise ADQLValidationError(
                        "MISSING DROP COLUMNS MIN_PERCENT must be between "
                        "0 and 100."
                    )
            else:
                raise ADQLValidationError(
                    "MISSING action is not recognized."
                )

        elif statement.kind == "DUPLICATES":
            action = parameters.get("action")

            if action == "summary":
                return

            if action != "drop":
                raise ADQLValidationError(
                    "DUPLICATES action is not recognized."
                )

            keep = str(parameters.get("keep", "first")).lower()

            if keep not in {"first", "last", "none"}:
                raise ADQLValidationError(
                    "DUPLICATES DROP KEEP must be first, last, or none."
                )

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
            source_name = str(parameters["source"]).strip()
            source = source_name.upper()

            if (
                not source_name
                or len(source_name) > 255
                or any(character in source_name for character in ";\r\n")
            ):
                raise ADQLValidationError(
                    "EXPORT source must be a valid built-in source or "
                    "registered dataset name."
                )

            suffix = Path(parameters["output"]).suffix.lower()

            if suffix not in {".csv", ".xlsx"}:
                raise ADQLValidationError(
                    "EXPORT output must end with .csv or .xlsx."
                )

        elif statement.kind == "SET":
            if parameters.get("setting") != "type":
                return

            dtype = str(parameters.get("dtype", "")).lower().strip()
            datetime_types = {"datetime", "date", "timestamp"}
            float_types = {"float", "numeric", "number", "decimal"}
            integer_types = {"int", "integer"}
            supported_types = (
                datetime_types
                | float_types
                | integer_types
                | {"str", "string", "text", "category", "categorical"}
            )

            if dtype not in supported_types:
                raise ADQLValidationError(
                    f"Unsupported SET TYPE dtype: {parameters.get('dtype')}. "
                    "Supported: datetime, string, int, float, decimal, category."
                )

            datetime_option_names = {
                "datetime_format": "FORMAT",
                "dayfirst": "DAYFIRST",
                "yearfirst": "YEARFIRST",
                "utc": "UTC",
            }
            supplied_datetime_options = [
                label
                for key, label in datetime_option_names.items()
                if key in parameters
            ]
            decimals = parameters.get("decimals")

            if dtype in datetime_types:
                if decimals is not None:
                    raise ADQLValidationError(
                        "DECIMALS is only valid for numeric SET TYPE conversions."
                    )

                datetime_format = parameters.get("datetime_format")

                if datetime_format is not None and (
                    not str(datetime_format).strip()
                    or len(str(datetime_format)) > 255
                    or any(
                        character in str(datetime_format)
                        for character in "\x00\r\n;"
                    )
                ):
                    raise ADQLValidationError(
                        "SET TYPE FORMAT must be a non-empty datetime pattern "
                        "of at most 255 characters."
                    )

                format_key = str(datetime_format or "AUTO").upper()

                if (
                    format_key not in {"AUTO", "INFER", "MIXED"}
                    and (
                        parameters.get("dayfirst")
                        or parameters.get("yearfirst")
                    )
                ):
                    raise ADQLValidationError(
                        "DAYFIRST and YEARFIRST are only used with FORMAT AUTO "
                        "or FORMAT MIXED; an explicit pattern already defines "
                        "the date order."
                    )
            else:
                if supplied_datetime_options:
                    raise ADQLValidationError(
                        ", ".join(supplied_datetime_options)
                        + " may only be used with datetime SET TYPE conversions."
                    )

                if decimals is not None:
                    if dtype in integer_types and decimals == 0:
                        pass
                    elif dtype not in float_types:
                        raise ADQLValidationError(
                            "DECIMALS is only valid for float, numeric, number, "
                            "decimal, or integer with DECIMALS 0."
                        )
                    elif decimals < 0 or decimals > 15:
                        raise ADQLValidationError(
                            "DECIMALS must be between 0 and 15."
                        )

        elif statement.kind == "LET":
            name = str(parameters.get("name", "")).strip()

            if (
                not name
                or len(name) > 128
                or any(character in name for character in ";\r\n")
            ):
                raise ADQLValidationError(
                    "LET name must be a valid identifier of at most 128 characters."
                )

            if name.upper() in DATA_SOURCES:
                raise ADQLValidationError(
                    "LET name cannot replace a built-in data source."
                )

            source_kind = parameters.get("source_kind")

            if source_kind == "select":
                self._validate_select(parameters["query"])
            elif source_kind == "stage":
                if parameters.get("source") not in set(DATA_SOURCES.values()):
                    raise ADQLValidationError("LET stage source is not recognized.")
            elif source_kind == "dataset":
                source = str(parameters.get("source", "")).strip()

                if (
                    not source
                    or len(source) > 255
                    or any(character in source for character in ";\r\n")
                ):
                    raise ADQLValidationError(
                        "LET DATASET source must be a valid registered name."
                    )
            else:
                raise ADQLValidationError("LET assignment source is not recognized.")

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
