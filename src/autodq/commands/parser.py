from __future__ import annotations

import ast
import re
import shlex
from typing import Any

from autodq.commands.errors import ADQLSyntaxError
from autodq.commands.grammar import (
    AGGREGATE_FUNCTIONS,
    AUTO_OPTIONS,
    BLUE_OPTIONS,
    DASHBOARD_OPTIONS,
    DATA_SOURCES,
    EXPLAIN_OPTIONS,
    GALLERY_STYLE_OPTIONS,
    MODEL_OPTIONS,
    PREDICT_OPTIONS,
    SHAP_OPTIONS,
    SIMPLE_COMMANDS,
    SUPPORTED_COMMANDS,
    VISUALIZE_OPTIONS,
)
from autodq.commands.models import ADQLScript, ADQLStatement


class ADQLParser:
    """Parse ADQL text into a safe, structured syntax tree."""

    SELECT_CLAUSES = ("FROM", "WHERE", "GROUP BY", "ORDER BY", "LIMIT")

    def parse(self, source: str) -> ADQLScript:
        if not isinstance(source, str):
            raise TypeError("ADQL source must be a string.")

        cleaned = self._strip_comments(source)
        raw_statements = self._split_statements(cleaned)

        if not raw_statements:
            raise ADQLSyntaxError("ADQL source does not contain a statement.")

        statements = []

        for number, raw in enumerate(raw_statements, start=1):
            try:
                statements.append(self._parse_statement(raw, number))
            except ADQLSyntaxError as error:
                message = str(error)

                if not message.startswith("Statement "):
                    message = f"Statement {number}: {message}"

                raise ADQLSyntaxError(message) from error

        return ADQLScript(source=source, statements=statements)

    def _parse_statement(self, raw: str, number: int) -> ADQLStatement:
        match = re.match(r"^\s*([A-Za-z_]+)", raw)

        if match is None:
            raise ADQLSyntaxError("A statement must begin with a command.")

        kind = match.group(1).upper()

        if kind not in SUPPORTED_COMMANDS:
            raise ADQLSyntaxError(
                f"Unsupported ADQL command: {kind}. Use HELP for syntax."
            )

        if kind == "SELECT":
            parameters = self._parse_select(raw)
        else:
            parameters = self._parse_workflow(kind, raw)

        return ADQLStatement(
            kind=kind,
            raw=raw.strip(),
            parameters=parameters,
            statement_number=number,
        )

    def _parse_workflow(self, kind: str, raw: str) -> dict[str, Any]:
        try:
            tokens = shlex.split(raw, posix=True)
        except ValueError as error:
            raise ADQLSyntaxError(f"Invalid quoting: {error}") from error

        arguments = tokens[1:]

        if kind == "DATASET":
            if not arguments:
                raise ADQLSyntaxError(
                    "DATASET requires a CSV or Excel file path."
                )

            options = self._parse_options(
                arguments[1:],
                {"TARGET": "target"},
            )
            return {"dataset_path": arguments[0], **options}

        if kind == "CLEANING":
            if not arguments or arguments[0].upper() not in {"PREVIEW", "APPLY"}:
                raise ADQLSyntaxError("CLEANING requires PREVIEW or APPLY.")
            action = arguments[0].lower()
            if action == "apply":
                if len(arguments) != 1:
                    raise ADQLSyntaxError("CLEANING APPLY does not accept arguments.")
                return {"action": action}
            options = self._parse_options(
                arguments[1:],
                {"ACTIONS": "action_ids", "MAX_ROWS": "max_rows"},
            )
            if "action_ids" in options:
                options["action_ids"] = self._integer_list(
                    options["action_ids"], option="ACTIONS"
                )
            return {"action": action, **self._coerce_options(options)}

        if kind in SIMPLE_COMMANDS:
            if arguments:
                raise ADQLSyntaxError(f"{kind} does not accept arguments.")

            return {}

        if kind == "AUTO":
            start = 0
            defaults = {}

            if arguments and self._key(arguments[0]) not in AUTO_OPTIONS:
                defaults["mode"] = arguments[0]
                start = 1

            defaults.update(
                self._parse_options(arguments[start:], AUTO_OPTIONS)
            )
            return self._coerce_options(defaults)

        if kind == "VISUALIZE":
            start = 0
            defaults = {}

            if arguments and self._key(arguments[0]) not in VISUALIZE_OPTIONS:
                defaults["chart"] = arguments[0]
                start = 1

            defaults.update(
                self._parse_options(arguments[start:], VISUALIZE_OPTIONS)
            )
            return self._coerce_options(defaults)

        if kind == "MODEL":
            if arguments and arguments[0].upper() in {"SAVE", "LOAD"}:
                action = arguments[0].lower()
                keyword = "TO" if action == "save" else "FROM"
                options = self._parse_options(
                    arguments[1:],
                    {
                        keyword: "path",
                        "OVERWRITE": "overwrite",
                    },
                    flags={"OVERWRITE"},
                )
                if "path" not in options:
                    raise ADQLSyntaxError(
                        f"MODEL {action.upper()} requires {keyword} followed by a path."
                    )
                return {"action": action, **self._coerce_options(options)}

            return self._coerce_options(
                self._parse_options(arguments, MODEL_OPTIONS)
            )

        if kind == "PREDICT":
            return self._coerce_options(
                self._parse_options(arguments, PREDICT_OPTIONS)
            )

        if kind == "EXPLAIN":
            return self._coerce_options(
                self._parse_options(arguments, EXPLAIN_OPTIONS)
            )

        if kind == "SHAP":
            return self._coerce_options(
                self._parse_options(arguments, SHAP_OPTIONS)
            )

        if kind == "WORKSPACE":
            return self._parse_workspace(arguments)

        if kind == "ADD":
            if len(arguments) < 4 or arguments[0].upper() != "DATASET":
                raise ADQLSyntaxError(
                    "ADD syntax is ADD DATASET name FROM path [OVERWRITE]."
                )
            options = self._parse_options(
                arguments[2:],
                {"FROM": "dataset_path", "OVERWRITE": "overwrite"},
                flags={"OVERWRITE"},
            )
            if "dataset_path" not in options:
                raise ADQLSyntaxError("ADD DATASET requires FROM followed by a path.")
            return {
                "entity": "dataset",
                "name": arguments[1],
                **self._coerce_options(options),
            }

        if kind == "LIST":
            if len(arguments) != 1 or arguments[0].upper() not in {
                "DATASETS", "WORKSPACES", "VISUALIZATIONS"
            }:
                raise ADQLSyntaxError(
                    "LIST requires DATASETS, WORKSPACES, or VISUALIZATIONS."
                )
            return {"entity": arguments[0].lower()}

        if kind == "MERGE":
            return self._parse_merge(arguments)

        if kind == "CONCAT":
            return self._parse_concat(arguments)

        if kind == "EDIT":
            if len(arguments) < 4 or arguments[0].upper() != "ROW":
                raise ADQLSyntaxError(
                    "EDIT syntax is EDIT ROW index CHANGES '{...}' [REASON text]."
                )
            options = self._parse_options(
                arguments[2:],
                {"CHANGES": "changes", "REASON": "reason"},
            )
            if "changes" not in options:
                raise ADQLSyntaxError("EDIT ROW requires CHANGES.")
            return {
                "row_index": self._literal(arguments[1]),
                "changes": self._mapping(options["changes"], option="CHANGES"),
                **({"reason": options["reason"]} if "reason" in options else {}),
            }

        if kind == "DOMAIN":
            return self._parse_domain(arguments)

        if kind == "OUTLIERS":
            return self._parse_outliers(arguments)

        if kind == "AUDIT":
            if not arguments or arguments[0].upper() != "EXPORT":
                raise ADQLSyntaxError("AUDIT syntax is AUDIT EXPORT TO path.")
            options = self._parse_options(arguments[1:], {"TO": "output"})
            if "output" not in options:
                raise ADQLSyntaxError("AUDIT EXPORT requires TO followed by a path.")
            return {"action": "export", **options}

        if kind == "CORRELATION":
            return self._coerce_options(
                self._parse_options(arguments, {"MIN_ABS": "min_abs_correlation"})
            )

        if kind in {"READINESS", "FEATURES"}:
            if arguments:
                raise ADQLSyntaxError(f"{kind} does not accept arguments.")
            return {}

        if kind == "FEATURE":
            return self._parse_feature(arguments)

        if kind == "BLUE":
            return self._parse_blue(arguments)

        if kind == "GALLERY":
            return self._parse_gallery(arguments)

        if kind == "DASHBOARD":
            return self._coerce_options(
                self._parse_options(
                    arguments,
                    DASHBOARD_OPTIONS,
                    flags={"OVERWRITE"},
                )
            )

        if kind == "APPROVE":
            if len(arguments) != 1:
                raise ADQLSyntaxError(
                    "APPROVE requires ALL or a comma-separated action list."
                )

            if arguments[0].upper() == "ALL":
                return {"all": True, "action_ids": []}

            return {
                "all": False,
                "action_ids": self._integer_list(
                    arguments[0],
                    option="APPROVE",
                ),
            }

        if kind == "REJECT":
            if not arguments:
                raise ADQLSyntaxError(
                    "REJECT requires a comma-separated action list."
                )

            action_ids = self._integer_list(
                arguments[0],
                option="REJECT",
            )
            options = self._parse_options(
                arguments[1:],
                {"REASON": "reason"},
            )
            return {"action_ids": action_ids, **options}

        if kind == "REPORT":
            options = self._parse_options(
                arguments,
                {
                    "TO": "output",
                    "STYLE": "style",
                    "OVERWRITE": "overwrite",
                },
                flags={"OVERWRITE"},
            )

            if "output" not in options:
                raise ADQLSyntaxError("REPORT requires TO followed by a path.")

            return options

        if kind == "EXPORT":
            if not arguments:
                raise ADQLSyntaxError(
                    "EXPORT requires a data source and TO followed by a path."
                )

            source = arguments[0].upper()
            options = self._parse_options(
                arguments[1:],
                {"TO": "output", "OVERWRITE": "overwrite"},
                flags={"OVERWRITE"},
            )

            if "output" not in options:
                raise ADQLSyntaxError("EXPORT requires TO followed by a path.")

            return {"source": source, **options}

        if kind == "SET":
            if len(arguments) == 2 and arguments[0].upper() == "TARGET":
                return {"setting": "target", "target": arguments[1]}

            if len(arguments) == 3 and arguments[0].upper() == "TYPE":
                return {
                    "setting": "type",
                    "column": arguments[1],
                    "dtype": arguments[2],
                }

            raise ADQLSyntaxError(
                "SET syntax is SET TARGET column or SET TYPE column dtype."
            )

        if kind == "USE":
            if len(arguments) != 2 or arguments[0].upper() != "DATASET":
                raise ADQLSyntaxError("USE syntax is USE DATASET name.")

            return {"dataset": arguments[1]}

        if kind in {"HEAD", "TAIL"}:
            if len(arguments) > 1:
                raise ADQLSyntaxError(f"{kind} accepts at most one row count.")

            return {
                "rows": self._positive_integer(
                    arguments[0] if arguments else "5",
                    option=kind,
                )
            }

        if kind == "SAMPLE":
            rows = 5
            start = 0

            if arguments and self._key(arguments[0]) != "RANDOM_STATE":
                rows = self._positive_integer(arguments[0], option="SAMPLE")
                start = 1

            options = self._parse_options(
                arguments[start:],
                {"RANDOM_STATE": "random_state"},
            )
            options = self._coerce_options(options)
            return {"rows": rows, **options}

        if kind == "HELP":
            if len(arguments) > 1:
                raise ADQLSyntaxError("HELP accepts at most one command name.")

            return {"command": arguments[0].upper() if arguments else None}

        if kind == "HISTORY":
            if not arguments:
                return {"limit": 10}

            if len(arguments) != 2 or arguments[0].upper() != "LIMIT":
                raise ADQLSyntaxError("HISTORY syntax is HISTORY [LIMIT n].")

            return {
                "limit": self._positive_integer(
                    arguments[1],
                    option="HISTORY LIMIT",
                )
            }

        raise ADQLSyntaxError(f"Parser is not implemented for {kind}.")

    def _parse_workspace(self, arguments: list[str]) -> dict[str, Any]:
        if not arguments:
            raise ADQLSyntaxError(
                "WORKSPACE requires CREATE, OPEN, SAVE, INFO, or LIST."
            )

        action = arguments[0].lower()
        rest = arguments[1:]

        if action == "create":
            if not rest:
                raise ADQLSyntaxError("WORKSPACE CREATE requires a name.")
            options = self._parse_options(
                rest[1:],
                {"ROOT": "workspace_root", "TARGET": "target"},
            )
            return {"action": action, "name": rest[0], **options}

        if action == "open":
            if not rest:
                raise ADQLSyntaxError("WORKSPACE OPEN requires a name or path.")
            options = self._parse_options(
                rest[1:],
                {"ROOT": "workspace_root", "LOAD_MODEL": "load_model"},
            )
            return {
                "action": action,
                "name_or_path": rest[0],
                **self._coerce_options(options),
            }

        if action == "save":
            options = self._parse_options(
                rest,
                {
                    "MODEL_NAME": "model_name",
                    "INCLUDE_MODEL": "include_model",
                },
            )
            return {"action": action, **self._coerce_options(options)}

        if action == "info":
            if rest:
                raise ADQLSyntaxError("WORKSPACE INFO does not accept arguments.")
            return {"action": action}

        if action == "list":
            options = self._parse_options(rest, {"ROOT": "workspace_root"})
            return {"action": action, **options}

        raise ADQLSyntaxError(
            "WORKSPACE requires CREATE, OPEN, SAVE, INFO, or LIST."
        )

    def _parse_merge(self, arguments: list[str]) -> dict[str, Any]:
        if not arguments:
            raise ADQLSyntaxError(
                "MERGE syntax is MERGE left WITH right AS output ON column."
            )
        options = self._parse_options(
            arguments[1:],
            {
                "WITH": "right",
                "AS": "output_name",
                "HOW": "how",
                "ON": "on",
                "LEFT_ON": "left_on",
                "RIGHT_ON": "right_on",
                "VALIDATE": "validate",
                "SUFFIXES": "suffixes",
                "MAKE_ACTIVE": "make_active",
            },
        )
        if "right" not in options:
            raise ADQLSyntaxError("MERGE requires WITH followed by a dataset.")
        for key in ("on", "left_on", "right_on"):
            if key in options and "," in str(options[key]):
                options[key] = self._string_list(options[key], option=key)
        if "suffixes" in options:
            suffixes = self._string_list(options["suffixes"], option="SUFFIXES")
            if len(suffixes) != 2:
                raise ADQLSyntaxError("MERGE SUFFIXES requires exactly two values.")
            options["suffixes"] = tuple(suffixes)
        return {
            "left": arguments[0],
            **self._coerce_options(options),
        }

    def _parse_concat(self, arguments: list[str]) -> dict[str, Any]:
        if not arguments:
            raise ADQLSyntaxError(
                "CONCAT syntax is CONCAT first,second AS output."
            )
        datasets = self._string_list(arguments[0], option="CONCAT")
        if len(datasets) < 2:
            raise ADQLSyntaxError("CONCAT requires at least two datasets.")
        options = self._parse_options(
            arguments[1:],
            {
                "AS": "output_name",
                "AXIS": "axis",
                "IGNORE_INDEX": "ignore_index",
                "JOIN": "join",
                "MAKE_ACTIVE": "make_active",
            },
        )
        return {"datasets": datasets, **self._coerce_options(options)}

    def _parse_domain(self, arguments: list[str]) -> dict[str, Any]:
        if not arguments:
            raise ADQLSyntaxError("DOMAIN requires ADD or VALIDATE.")
        action = arguments[0].lower()

        if action == "validate":
            if len(arguments) != 1:
                raise ADQLSyntaxError("DOMAIN VALIDATE does not accept arguments.")
            return {"action": action}

        if action != "add" or len(arguments) < 3:
            raise ADQLSyntaxError(
                "DOMAIN ADD requires a column and at least one constraint."
            )
        options = self._parse_options(
            arguments[2:],
            {
                "MIN": "min_value",
                "MAX": "max_value",
                "ALLOWED": "allowed_values",
                "PATTERN": "pattern",
                "NULLABLE": "nullable",
                "UNIQUE": "unique",
                "DESCRIPTION": "description",
            },
        )
        for key in ("min_value", "max_value"):
            if key in options:
                options[key] = self._literal(options[key])
        if "allowed_values" in options:
            options["allowed_values"] = [
                self._literal(item)
                for item in self._split_top_level(options["allowed_values"], ",")
            ]
        options = self._coerce_options(options)
        return {"action": action, "column": arguments[1], **options}

    def _parse_outliers(self, arguments: list[str]) -> dict[str, Any]:
        if not arguments:
            raise ADQLSyntaxError("OUTLIERS requires REVIEW or TREAT.")
        action = arguments[0].lower()

        if action == "review":
            options = self._parse_options(
                arguments[1:],
                {"COLUMNS": "columns", "IQR": "iqr_multiplier"},
            )
            if "columns" in options:
                options["columns"] = self._string_list(
                    options["columns"], option="COLUMNS"
                )
            return {"action": action, **self._coerce_options(options)}

        if action == "treat":
            options = self._parse_options(
                arguments[1:],
                {
                    "COLUMN": "column",
                    "STRATEGY": "strategy",
                    "LOWER": "lower_bound",
                    "UPPER": "upper_bound",
                    "REASON": "reason",
                    "IQR": "iqr_multiplier",
                },
            )
            if "column" not in options:
                raise ADQLSyntaxError("OUTLIERS TREAT requires COLUMN.")
            return {"action": action, **self._coerce_options(options)}

        raise ADQLSyntaxError("OUTLIERS requires REVIEW or TREAT.")

    def _parse_feature(self, arguments: list[str]) -> dict[str, Any]:
        if not arguments:
            raise ADQLSyntaxError("FEATURE requires CREATE or APPLY.")
        action = arguments[0].lower()

        if action == "apply":
            options = self._parse_options(arguments[1:], {"NAMES": "features"})
            if "features" in options:
                options["features"] = self._string_list(
                    options["features"], option="NAMES"
                )
            return {"action": action, **options}

        if action != "create" or len(arguments) < 2:
            raise ADQLSyntaxError("FEATURE CREATE requires a feature name.")
        options = self._parse_options(
            arguments[2:],
            {
                "METHOD": "method",
                "COLUMN": "column",
                "COLUMNS": "columns",
                "EXPRESSION": "expression",
                "BINS": "bins",
                "LABELS": "labels",
                "USE_ENGINEERED": "use_engineered",
            },
        )
        if "method" not in options:
            raise ADQLSyntaxError("FEATURE CREATE requires METHOD.")
        if "columns" in options:
            options["columns"] = self._string_list(options["columns"], option="COLUMNS")
        if "bins" in options:
            try:
                options["bins"] = [float(item) for item in self._string_list(options["bins"], option="BINS")]
            except ValueError as error:
                raise ADQLSyntaxError("FEATURE BINS must be numeric.") from error
        if "labels" in options:
            options["labels"] = self._string_list(options["labels"], option="LABELS")
        return {
            "action": action,
            "name": arguments[1],
            **self._coerce_options(options),
        }

    def _parse_blue(self, arguments: list[str]) -> dict[str, Any]:
        if arguments and arguments[0].upper() in {
            "VISUALIZE", "INTERPRET", "PRESCRIBE"
        }:
            action = arguments[0].lower()
            rest = arguments[1:]
            if action == "visualize":
                options = self._parse_options(
                    rest,
                    {
                        "APPEND": "append",
                        "ALLOW_DUPLICATES": "allow_duplicates",
                    },
                )
                return {"action": action, **self._coerce_options(options)}
            if rest:
                raise ADQLSyntaxError(f"BLUE {action.upper()} does not accept arguments.")
            return {"action": action}

        return {
            "action": "analyze",
            **self._coerce_options(self._parse_options(arguments, BLUE_OPTIONS)),
        }

    def _parse_gallery(self, arguments: list[str]) -> dict[str, Any]:
        if not arguments:
            raise ADQLSyntaxError(
                "GALLERY requires LIST, GET, CUSTOMIZE, SAVE, REMOVE, or CLEAR."
            )
        action = arguments[0].lower()
        rest = arguments[1:]

        if action == "list":
            options = self._parse_options(
                rest,
                {
                    "TYPE": "chart_type",
                    "STAGE": "stage",
                    "RECOMMENDED": "recommended",
                },
            )
            return {"action": action, **self._coerce_options(options)}

        if action in {"get", "remove"}:
            if len(rest) != 1:
                raise ADQLSyntaxError(f"GALLERY {action.upper()} requires a chart ID.")
            return {"action": action, "chart_id": rest[0]}

        if action == "customize":
            if not rest:
                raise ADQLSyntaxError("GALLERY CUSTOMIZE requires a chart ID.")
            options = self._parse_options(rest[1:], GALLERY_STYLE_OPTIONS)
            return {
                "action": action,
                "chart_id": rest[0],
                **self._coerce_options(options),
            }

        if action == "save":
            options = self._parse_options(
                rest, {"TO": "output_dir", "FORMAT": "format"}
            )
            return {"action": action, **options}

        if action == "clear":
            if rest:
                raise ADQLSyntaxError("GALLERY CLEAR does not accept arguments.")
            return {"action": action}

        raise ADQLSyntaxError(
            "GALLERY requires LIST, GET, CUSTOMIZE, SAVE, REMOVE, or CLEAR."
        )

    def _parse_select(self, raw: str) -> dict[str, Any]:
        body = re.sub(r"^\s*SELECT\b", "", raw, count=1, flags=re.I).strip()
        positions = self._keyword_positions(body, self.SELECT_CLAUSES)
        from_positions = positions.get("FROM", [])

        if len(from_positions) != 1:
            raise ADQLSyntaxError("SELECT requires exactly one FROM clause.")

        flattened = sorted(
            (position, keyword)
            for keyword, matches in positions.items()
            for position in matches
        )
        keywords = [keyword for _, keyword in flattened]

        if not flattened or flattened[0][1] != "FROM":
            raise ADQLSyntaxError("FROM must follow the SELECT expression list.")

        expected_order = {
            keyword: index for index, keyword in enumerate(self.SELECT_CLAUSES)
        }
        indexes = [expected_order[keyword] for keyword in keywords]

        if indexes != sorted(indexes) or len(keywords) != len(set(keywords)):
            raise ADQLSyntaxError(
                "SELECT clauses are duplicated or out of order. Expected "
                "FROM, WHERE, GROUP BY, ORDER BY, LIMIT."
            )

        projection_text = body[: flattened[0][0]].strip()

        if not projection_text:
            raise ADQLSyntaxError("SELECT requires at least one expression.")

        clause_values = {}

        for index, (position, keyword) in enumerate(flattened):
            value_start = position + len(keyword)
            value_end = (
                flattened[index + 1][0]
                if index + 1 < len(flattened)
                else len(body)
            )
            value = body[value_start:value_end].strip()

            if not value:
                raise ADQLSyntaxError(f"{keyword} clause cannot be empty.")

            clause_values[keyword] = value

        source = clause_values["FROM"].upper()

        if source not in DATA_SOURCES:
            supported = ", ".join(DATA_SOURCES)
            raise ADQLSyntaxError(
                f"Unsupported SELECT source: {source}. Use one of {supported}."
            )

        distinct = False

        if re.match(r"^DISTINCT\b", projection_text, flags=re.I):
            projection_text = re.sub(
                r"^DISTINCT\b",
                "",
                projection_text,
                count=1,
                flags=re.I,
            ).strip()
            distinct = True

        select_items = [
            self._parse_select_item(item)
            for item in self._split_top_level(projection_text, ",")
        ]
        where = (
            self._parse_where(clause_values["WHERE"])
            if "WHERE" in clause_values
            else []
        )
        group_by = (
            [
                self._identifier(item)
                for item in self._split_top_level(
                    clause_values["GROUP BY"],
                    ",",
                )
            ]
            if "GROUP BY" in clause_values
            else []
        )
        order_by = (
            self._parse_order_by(clause_values["ORDER BY"])
            if "ORDER BY" in clause_values
            else []
        )
        limit = None

        if "LIMIT" in clause_values:
            limit = self._positive_integer(
                clause_values["LIMIT"],
                option="LIMIT",
            )

        return {
            "source": DATA_SOURCES[source],
            "distinct": distinct,
            "select": select_items,
            "where": where,
            "group_by": group_by,
            "order_by": order_by,
            "limit": limit,
        }

    def _parse_select_item(self, text: str) -> dict[str, Any]:
        text = text.strip()

        if not text:
            raise ADQLSyntaxError("SELECT expressions cannot be empty.")

        alias = None
        alias_positions = self._keyword_positions(text, ("AS",)).get("AS", [])

        if len(alias_positions) > 1:
            raise ADQLSyntaxError(f"Invalid SELECT alias: {text}")

        if alias_positions:
            position = alias_positions[0]
            alias = self._identifier(text[position + 2 :])
            text = text[:position].strip()

        aggregate = re.match(
            r"^(COUNT|SUM|AVG|MEAN|MIN|MAX|MEDIAN|NUNIQUE)\s*\((.*)\)$",
            text,
            flags=re.I | re.S,
        )

        if aggregate:
            function = aggregate.group(1).upper()
            column_text = aggregate.group(2).strip()
            column = "*" if column_text == "*" else self._identifier(column_text)
            default_alias = (
                "count"
                if column == "*"
                else f"{function.lower()}_{column}"
            )
            return {
                "kind": "aggregate",
                "function": function,
                "column": column,
                "alias": alias or default_alias,
            }

        if text == "*":
            return {"kind": "wildcard", "column": "*", "alias": None}

        column = self._identifier(text)
        return {
            "kind": "column",
            "column": column,
            "alias": alias or column,
        }

    def _parse_where(self, text: str) -> list[dict[str, Any]]:
        if self._keyword_positions(text, ("OR",)).get("OR"):
            raise ADQLSyntaxError(
                "OR is not supported in ADQL v1. Use IN (...) or separate queries."
            )

        parts = self._split_keyword(text, "AND")
        return [self._parse_condition(part) for part in parts]

    def _parse_condition(self, text: str) -> dict[str, Any]:
        text = text.strip()

        for operator in ("IS NOT NULL", "IS NULL"):
            positions = self._keyword_positions(text, (operator,)).get(
                operator,
                [],
            )

            if positions and positions[-1] + len(operator) == len(text):
                return {
                    "column": self._identifier(text[: positions[-1]]),
                    "operator": operator,
                    "value": None,
                }

        for operator in (
            "NOT IN",
            "IN",
            "STARTS WITH",
            "ENDS WITH",
            "CONTAINS",
        ):
            positions = self._keyword_positions(text, (operator,)).get(
                operator,
                [],
            )

            if not positions:
                continue

            position = positions[0]
            column = self._identifier(text[:position])
            raw_value = text[position + len(operator) :].strip()

            if operator in {"IN", "NOT IN"}:
                if not (raw_value.startswith("(") and raw_value.endswith(")")):
                    raise ADQLSyntaxError(
                        f"{operator} requires a parenthesized value list."
                    )

                values = self._split_top_level(raw_value[1:-1], ",")

                if not values:
                    raise ADQLSyntaxError(f"{operator} list cannot be empty.")

                value = [self._literal(item) for item in values]
            else:
                value = self._literal(raw_value)

            return {"column": column, "operator": operator, "value": value}

        match = re.match(r"^(.*?)\s*(<=|>=|!=|=|<|>)\s*(.+)$", text, flags=re.S)

        if match is None:
            raise ADQLSyntaxError(f"Unsupported WHERE condition: {text}")

        return {
            "column": self._identifier(match.group(1)),
            "operator": match.group(2),
            "value": self._literal(match.group(3)),
        }

    def _parse_order_by(self, text: str) -> list[dict[str, Any]]:
        terms = []

        for item in self._split_top_level(text, ","):
            match = re.match(r"^(.*?)(?:\s+(ASC|DESC))?$", item, flags=re.I | re.S)

            if match is None:
                raise ADQLSyntaxError(f"Invalid ORDER BY expression: {item}")

            terms.append(
                {
                    "column": self._identifier(match.group(1)),
                    "ascending": (match.group(2) or "ASC").upper() == "ASC",
                }
            )

        return terms

    def _parse_options(
        self,
        tokens: list[str],
        option_map: dict[str, str],
        flags: set[str] | None = None,
    ) -> dict[str, Any]:
        flags = flags or set()
        options = {}
        index = 0

        while index < len(tokens):
            key = self._key(tokens[index])

            if key not in option_map:
                raise ADQLSyntaxError(f"Unsupported option: {tokens[index]}")

            destination = option_map[key]

            if destination in options:
                raise ADQLSyntaxError(f"Option {key} was provided more than once.")

            if key in flags:
                if (
                    index + 1 < len(tokens)
                    and self._key(tokens[index + 1]) not in option_map
                    and tokens[index + 1].lower() in {"true", "false"}
                ):
                    options[destination] = tokens[index + 1]
                    index += 2
                else:
                    options[destination] = True
                    index += 1

                continue

            if index + 1 >= len(tokens):
                raise ADQLSyntaxError(f"Option {key} requires a value.")

            options[destination] = tokens[index + 1]
            index += 2

        return options

    def _coerce_options(self, options: dict[str, Any]) -> dict[str, Any]:
        boolean_options = {
            "visualize",
            "approve_all",
            "apply_cleaning",
            "apply_features",
            "train_model",
            "generate_predictions",
            "explain_model",
            "refresh",
            "continue_on_error",
            "use_engineered",
            "exclude_leakage",
            "uncertainty",
            "include_charts",
            "include_data_preview",
            "overwrite",
            "auto_display",
            "grid",
            "legend",
            "display",
            "append",
            "load_model",
            "include_model",
            "make_active",
            "ignore_index",
            "nullable",
            "unique",
            "allow_duplicates",
            "transparent",
        }
        integer_options = {
            "random_state",
            "dpi",
            "max_charts",
            "max_preview_rows",
            "max_rows",
            "row",
            "axis",
            "max_features",
        }
        float_options = {
            "test_size",
            "confidence_level",
            "low_confidence_threshold",
            "min_abs_correlation",
            "iqr_multiplier",
            "lower_bound",
            "upper_bound",
            "significance_level",
            "leakage_threshold",
        }
        list_options = {"exclude_features", "chart_ids"}
        coerced = {}

        for key, value in options.items():
            if key in boolean_options:
                coerced[key] = self._boolean(value, option=key)
            elif key in integer_options:
                coerced[key] = self._integer(value, option=key)
            elif key in float_options:
                coerced[key] = self._float(value, option=key)
            elif key in list_options:
                coerced[key] = self._string_list(value, option=key)
            elif key == "figsize":
                coerced[key] = self._figsize(value)
            else:
                coerced[key] = value

        return coerced

    @staticmethod
    def _strip_comments(source: str) -> str:
        output = []
        quote = None
        index = 0

        while index < len(source):
            character = source[index]

            if quote is not None:
                output.append(character)

                if character == "\\" and index + 1 < len(source):
                    index += 1
                    output.append(source[index])
                elif character == quote:
                    quote = None

                index += 1
                continue

            if character in {"'", '"', "`"}:
                quote = character
                output.append(character)
                index += 1
                continue

            if character == "#" or source[index : index + 2] == "--":
                while index < len(source) and source[index] not in "\r\n":
                    index += 1

                continue

            output.append(character)
            index += 1

        if quote is not None:
            raise ADQLSyntaxError("Unterminated quoted value.")

        return "".join(output)

    @classmethod
    def _split_statements(cls, source: str) -> list[str]:
        return [
            item.strip()
            for item in cls._split_top_level(source, ";")
            if item.strip()
        ]

    @staticmethod
    def _split_top_level(text: str, separator: str) -> list[str]:
        parts = []
        start = 0
        quote = None
        depth = 0
        index = 0

        while index < len(text):
            character = text[index]

            if quote is not None:
                if character == "\\" and index + 1 < len(text):
                    index += 2
                    continue

                if character == quote:
                    quote = None

                index += 1
                continue

            if character in {"'", '"', "`"}:
                quote = character
            elif character == "(":
                depth += 1
            elif character == ")":
                depth -= 1

                if depth < 0:
                    raise ADQLSyntaxError("Unbalanced parentheses.")
            elif depth == 0 and text.startswith(separator, index):
                parts.append(text[start:index].strip())
                index += len(separator)
                start = index
                continue

            index += 1

        if quote is not None:
            raise ADQLSyntaxError("Unterminated quoted value.")

        if depth != 0:
            raise ADQLSyntaxError("Unbalanced parentheses.")

        parts.append(text[start:].strip())
        return parts

    @classmethod
    def _keyword_positions(
        cls,
        text: str,
        keywords: tuple[str, ...],
    ) -> dict[str, list[int]]:
        positions = {keyword: [] for keyword in keywords}
        quote = None
        depth = 0
        upper = text.upper()
        index = 0

        while index < len(text):
            character = text[index]

            if quote is not None:
                if character == "\\" and index + 1 < len(text):
                    index += 2
                    continue

                if character == quote:
                    quote = None

                index += 1
                continue

            if character in {"'", '"', "`"}:
                quote = character
                index += 1
                continue

            if character == "(":
                depth += 1
                index += 1
                continue

            if character == ")":
                depth -= 1
                index += 1
                continue

            if depth == 0:
                matched = False

                for keyword in sorted(keywords, key=len, reverse=True):
                    end = index + len(keyword)

                    if end > len(text):
                        continue

                    before_ok = index == 0 or not (
                        upper[index - 1].isalnum() or upper[index - 1] == "_"
                    )
                    after_ok = end == len(text) or not (
                        upper[end].isalnum() or upper[end] == "_"
                    )

                    if before_ok and after_ok and upper.startswith(keyword, index):
                        positions[keyword].append(index)
                        index = end
                        matched = True
                        break

                if matched:
                    continue

            index += 1

        return positions

    @classmethod
    def _split_keyword(cls, text: str, keyword: str) -> list[str]:
        positions = cls._keyword_positions(text, (keyword,)).get(keyword, [])

        if not positions:
            return [text.strip()]

        parts = []
        start = 0

        for position in positions:
            parts.append(text[start:position].strip())
            start = position + len(keyword)

        parts.append(text[start:].strip())

        if any(not item for item in parts):
            raise ADQLSyntaxError(f"{keyword} cannot appear without conditions.")

        return parts

    @staticmethod
    def _identifier(value: str) -> str:
        value = value.strip()

        if len(value) >= 2 and value[0] == value[-1] and value[0] in {
            "'",
            '"',
            "`",
        }:
            value = value[1:-1]

        value = value.strip()

        if not value:
            raise ADQLSyntaxError("Column and alias names cannot be empty.")

        if any(character in value for character in ";\r\n"):
            raise ADQLSyntaxError("Column and alias names cannot contain separators.")

        return value

    @staticmethod
    def _literal(value: str) -> Any:
        value = value.strip()

        if not value:
            raise ADQLSyntaxError("A condition value cannot be empty.")

        upper = value.upper()

        if upper in {"NULL", "NONE"}:
            return None

        if upper == "TRUE":
            return True

        if upper == "FALSE":
            return False

        if value[0] in {"'", '"'}:
            try:
                parsed = ast.literal_eval(value)
            except (SyntaxError, ValueError) as error:
                raise ADQLSyntaxError(
                    f"Invalid quoted literal: {value}"
                ) from error

            if not isinstance(parsed, str):
                raise ADQLSyntaxError("Quoted ADQL values must be strings.")

            return parsed

        if re.fullmatch(r"[+-]?\d+", value):
            return int(value)

        if re.fullmatch(
            r"[+-]?(?:\d+\.\d*|\d*\.\d+|\d+)(?:[eE][+-]?\d+)?",
            value,
        ):
            return float(value)

        return value

    @staticmethod
    def _mapping(value: Any, *, option: str) -> dict[str, Any]:
        try:
            parsed = ast.literal_eval(str(value))
        except (SyntaxError, ValueError) as error:
            raise ADQLSyntaxError(
                f"{option} must be a quoted dictionary, for example "
                "'{\"Revenue\": 120}'."
            ) from error

        if not isinstance(parsed, dict) or not parsed:
            raise ADQLSyntaxError(f"{option} must be a non-empty dictionary.")

        if any(not isinstance(key, str) or not key for key in parsed):
            raise ADQLSyntaxError(f"{option} keys must be column names.")

        return parsed

    @staticmethod
    def _key(value: str) -> str:
        return value.upper().replace("-", "_")

    @staticmethod
    def _boolean(value: Any, *, option: str) -> bool:
        if isinstance(value, bool):
            return value

        normalized = str(value).lower().strip()

        if normalized in {"true", "yes", "1", "on"}:
            return True

        if normalized in {"false", "no", "0", "off"}:
            return False

        raise ADQLSyntaxError(f"{option} must be true or false.")

    @staticmethod
    def _integer(value: Any, *, option: str) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError) as error:
            raise ADQLSyntaxError(f"{option} must be an integer.") from error

        if isinstance(value, str) and str(parsed) != value.strip():
            raise ADQLSyntaxError(f"{option} must be an integer.")

        return parsed

    @classmethod
    def _positive_integer(cls, value: Any, *, option: str) -> int:
        parsed = cls._integer(value, option=option)

        if parsed <= 0:
            raise ADQLSyntaxError(f"{option} must be a positive integer.")

        return parsed

    @staticmethod
    def _float(value: Any, *, option: str) -> float:
        try:
            return float(value)
        except (TypeError, ValueError) as error:
            raise ADQLSyntaxError(f"{option} must be numeric.") from error

    @classmethod
    def _integer_list(cls, value: Any, *, option: str) -> list[int]:
        values = str(value).split(",")

        if not values or any(not item.strip() for item in values):
            raise ADQLSyntaxError(f"{option} action list cannot be empty.")

        return [
            cls._positive_integer(item.strip(), option=option)
            for item in values
        ]

    @staticmethod
    def _string_list(value: Any, *, option: str) -> list[str]:
        values = [item.strip() for item in str(value).split(",")]

        if not values or any(not item for item in values):
            raise ADQLSyntaxError(f"{option} list cannot be empty.")

        return values

    @classmethod
    def _figsize(cls, value: Any) -> tuple[float, float]:
        pieces = re.split(r"[xX,]", str(value))

        if len(pieces) != 2:
            raise ADQLSyntaxError("FIGSIZE must use width,height or widthxheight.")

        width = cls._float(pieces[0], option="FIGSIZE width")
        height = cls._float(pieces[1], option="FIGSIZE height")

        if width <= 0 or height <= 0:
            raise ADQLSyntaxError("FIGSIZE values must be positive.")

        return width, height
