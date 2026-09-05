"""Grammar constants for the AutoDQ Analytics Domain Query Language."""

# Public language version. This is intentionally independent from the AutoDQ
# package and VS Code extension versions.
ADQL_LANGUAGE_VERSION = "2.6"

# Human-readable drift sensitivity presets. Explicit threshold options on a
# CHECK DRIFT statement override the selected preset.
DRIFT_SENSITIVITY_PRESETS = {
    "strict": {
        "psi_warning": 0.05,
        "psi_error": 0.15,
        "missing_warning": 1.0,
        "missing_error": 2.0,
    },
    "normal": {
        "psi_warning": 0.10,
        "psi_error": 0.25,
        "missing_warning": 2.0,
        "missing_error": 5.0,
    },
    "relaxed": {
        "psi_warning": 0.20,
        "psi_error": 0.35,
        "missing_warning": 5.0,
        "missing_error": 10.0,
    },
}

SUPPORTED_COMMANDS = {
    "SELECT",
    "DATASET",
    "LOAD",
    "KNOWLEDGE",
    "LET",
    "PROFILE",
    "STATISTICS",
    "INTERPRET",
    "DIAGNOSE",
    "RECOMMEND",
    "DECIDE",
    "PREVIEW",
    "REVIEW",
    "APPROVE",
    "REJECT",
    "CLEAN",
    "VALIDATE",
    "CLEANING",
    "AUTO",
    "VISUALIZE",
    "MODEL",
    "PREDICT",
    "EXPLAIN",
    "SHAP",
    "DASHBOARD",
    "WORKSPACE",
    "ADD",
    "LIST",
    "MERGE",
    "CONCAT",
    "EDIT",
    "MISSING",
    "DUPLICATES",
    "DOMAIN",
    "OUTLIERS",
    "AUDIT",
    "CORRELATION",
    "READINESS",
    "OPERATIONS",
    "KPI",
    "PROCESS",
    "BOTTLENECKS",
    "ROOT",
    "INVENTORY",
    "FEATURES",
    "FEATURE",
    "BLUE",
    "GALLERY",
    "REPORT",
    "EXPORT",
    "SET",
    "USE",
    "HEAD",
    "TAIL",
    "SAMPLE",
    "HELP",
    "HISTORY",
    "SESSION",
    "ASSERT",
    "SCHEMA",
    "DRIFT",
    "CONTRACT",
    "BASELINE",
    "CHECK",
}

SIMPLE_COMMANDS = {
    "LOAD",
    "KNOWLEDGE",
    "PROFILE",
    "STATISTICS",
    "INTERPRET",
    "DIAGNOSE",
    "RECOMMEND",
    "DECIDE",
    "PREVIEW",
    "REVIEW",
    "CLEAN",
    "VALIDATE",
}

# Commands whose only optional positional argument may be a dataset name.
# ``PROFILE customers`` is therefore concise, while commands that already
# accept positional values use the explicit ``DATASET customers`` selector.
POSITIONAL_DATASET_COMMANDS = SIMPLE_COMMANDS | {
    "FEATURES",
    "READINESS",
    "OPERATIONS",
    "KPI",
    "PROCESS",
    "BOTTLENECKS",
}

# Dataset-scoped commands operate on project state.  The parser accepts a
# leading ``DATASET name`` selector for every command in this set, and the
# executor activates that dataset before dispatching through the project API.
DATASET_SCOPED_COMMANDS = {
    "APPROVE",
    "ASSERT",
    "AUDIT",
    "AUTO",
    "BLUE",
    "CLEAN",
    "CLEANING",
    "CORRELATION",
    "DASHBOARD",
    "DECIDE",
    "DIAGNOSE",
    "DOMAIN",
    "EDIT",
    "EXPLAIN",
    "EXPORT",
    "FEATURE",
    "FEATURES",
    "HEAD",
    "INTERPRET",
    "KNOWLEDGE",
    "LOAD",
    "MODEL",
    "MISSING",
    "DUPLICATES",
    "OUTLIERS",
    "PREDICT",
    "PREVIEW",
    "PROFILE",
    "READINESS",
    "OPERATIONS",
    "KPI",
    "PROCESS",
    "BOTTLENECKS",
    "ROOT",
    "INVENTORY",
    "RECOMMEND",
    "REJECT",
    "REPORT",
    "REVIEW",
    "SAMPLE",
    "SET",
    "SHAP",
    "STATISTICS",
    "TAIL",
    "VALIDATE",
    "VISUALIZE",
}

DATA_SOURCES = {
    "CURRENT": "current",
    "RAW": "current",
    "DATA": "current",
    "CLEANED": "cleaned",
    "ENGINEERED": "engineered",
    "FEATURES": "engineered",
    "PREDICTIONS": "predictions",
}

AGGREGATE_FUNCTIONS = {
    "COUNT",
    "SUM",
    "AVG",
    "MEAN",
    "MIN",
    "MAX",
    "MEDIAN",
    "NUNIQUE",
}

COMPARISON_OPERATORS = {
    "=",
    "!=",
    "<",
    "<=",
    ">",
    ">=",
    "IN",
    "NOT IN",
    "IS NULL",
    "IS NOT NULL",
    "CONTAINS",
    "STARTS WITH",
    "ENDS WITH",
}

VISUALIZE_OPTIONS = {
    "CHART": "chart",
    "X": "x",
    "Y": "y",
    "COLUMN": "column",
    "STAGE": "stage",
    "TITLE": "title",
    "SUBTITLE": "subtitle",
    "X_LABEL": "x_label",
    "Y_LABEL": "y_label",
    "THEME": "theme",
    "COLOR": "color",
    "PALETTE": "palette",
    "FIGSIZE": "figsize",
    "DPI": "dpi",
    "GRID": "grid",
    "LEGEND": "legend",
    "DISPLAY": "display",
    "APPEND": "append",
    "SAVE": "save",
    "FORMAT": "save_format",
}

AUTO_OPTIONS = {
    "MODE": "mode",
    "VISUALIZE": "visualize",
    "APPROVE_ALL": "approve_all",
    "APPLY_CLEANING": "apply_cleaning",
    "APPLY_FEATURES": "apply_features",
    "TRAIN_MODEL": "train_model",
    "PREDICT": "generate_predictions",
    "EXPLAIN": "explain_model",
    "ALGORITHM": "algorithm",
    "TEST_SIZE": "test_size",
    "RANDOM_STATE": "random_state",
    "REPORT": "report_output",
    "REPORT_OUTPUT": "report_output",
    "REPORT_STYLE": "report_style",
    "SAVE_WORKSPACE": "save_workspace",
    "REFRESH": "refresh",
    "CONTINUE_ON_ERROR": "continue_on_error",
    "RAISE_ON_ERROR": "raise_on_error",
}

MODEL_OPTIONS = {
    "TARGET": "target",
    "USING": "algorithm",
    "ALGORITHM": "algorithm",
    "TEST_SIZE": "test_size",
    "RANDOM_STATE": "random_state",
    "USE_ENGINEERED": "use_engineered",
    "EXCLUDE_LEAKAGE": "exclude_leakage",
    "EXCLUDE": "exclude_features",
}

PREDICT_OPTIONS = {
    "CONFIDENCE": "confidence_level",
    "CONFIDENCE_LEVEL": "confidence_level",
    "UNCERTAINTY": "uncertainty",
    "LOW_CONFIDENCE": "low_confidence_threshold",
    "LOW_CONFIDENCE_THRESHOLD": "low_confidence_threshold",
}

EXPLAIN_OPTIONS = {
    "MAX_ROWS": "max_rows",
    "USE_ENGINEERED": "use_engineered",
}

SHAP_OPTIONS = {
    "CHART": "chart",
    "ROW": "row",
    "FEATURE": "feature",
    "SAVE": "save",
}

BLUE_OPTIONS = {
    "SOURCE": "source",
    "USE_ENGINEERED": "use_engineered",
    "EXCLUDE_LEAKAGE": "exclude_leakage",
    "MAX_FEATURES": "max_features",
    "SIGNIFICANCE": "significance_level",
    "LEAKAGE_THRESHOLD": "leakage_threshold",
    "EXCLUDE": "exclude_features",
}

OPERATIONS_OPTIONS = {
    "ENTITY": "entity_column",
    "TIME": "time_column",
    "START": "start_column",
    "END": "end_column",
    "STATUS": "status_column",
    "STAGE": "stage_column",
    "DURATION": "duration_column",
    "VALUE": "value_column",
    "COST": "cost_column",
    "QUANTITY": "quantity_column",
    "CAPACITY": "capacity_column",
    "GROUP": "group_by",
    "GROUP_BY": "group_by",
    "SLA": "sla_target",
    "PERIOD": "period",
    "TOP": "top",
    "DATASET": "dataset_name",
}

INVENTORY_OPTIONS = {
    "ITEM": "item_column",
    "LOCATION": "location_column",
    "ECHELON": "echelon_column",
    "PARENT": "parent_location_column",
    "TIME": "time_column",
    "ON_HAND": "on_hand_column",
    "ON_ORDER": "on_order_column",
    "BACKORDER": "backorder_column",
    "DEMAND": "demand_column",
    "LEAD_TIME": "lead_time_column",
    "SAFETY_STOCK": "safety_stock_column",
    "UNIT_COST": "unit_cost_column",
    "CAPACITY": "capacity_column",
    "SERVICE_LEVEL": "service_level",
    "HORIZON": "horizon_days",
    "TOP": "top",
    "DATASET": "dataset_name",
}

GALLERY_STYLE_OPTIONS = {
    "TITLE": "title",
    "SUBTITLE": "subtitle",
    "X_LABEL": "x_label",
    "Y_LABEL": "y_label",
    "THEME": "theme",
    "COLOR": "color",
    "PALETTE": "palette",
    "FIGSIZE": "figsize",
    "DPI": "dpi",
    "GRID": "grid",
    "LEGEND": "legend",
    "LEGEND_POSITION": "legend_position",
    "TEMPLATE": "template",
    "TRANSPARENT": "transparent",
}

DASHBOARD_OPTIONS = {
    "TITLE": "title",
    "SUBTITLE": "subtitle",
    "THEME": "theme",
    "STAGE": "stage",
    "SAVE": "output",
    "OUTPUT": "output",
    "MAX_CHARTS": "max_charts",
    "MAX_ROWS": "max_preview_rows",
    "CHART_IDS": "chart_ids",
    "CHARTS": "include_charts",
    "PREVIEW": "include_data_preview",
    "REFRESH": "refresh",
    "OVERWRITE": "overwrite",
    "DISPLAY": "auto_display",
}

SET_TYPE_OPTIONS = {
    "FORMAT": "datetime_format",
    "DAYFIRST": "dayfirst",
    "YEARFIRST": "yearfirst",
    "UTC": "utc",
    "DECIMALS": "decimals",
}

COMMAND_HELP = [
    {
        "command": "DATASET",
        "syntax": "DATASET \"path/to/data.csv\" [TARGET column]",
        "description": "Declare the dataset for a standalone ADQL file.",
    },
    {
        "command": "SELECT",
        "syntax": (
            "SELECT columns|aggregates FROM CURRENT|CLEANED|ENGINEERED|"
            "PREDICTIONS|dataset [WHERE ...] [GROUP BY ...] "
            "[ORDER BY ...] [LIMIT n]"
        ),
        "description": "Run a safe pandas-backed analytical query.",
    },
    {
        "command": (
            "LOAD / PROFILE / STATISTICS / INTERPRET / DIAGNOSE / "
            "RECOMMEND / DECIDE / PREVIEW"
        ),
        "syntax": (
            "LOAD [dataset]; PROFILE [dataset]; STATISTICS [dataset]; "
            "INTERPRET [dataset]; DIAGNOSE [dataset]; "
            "RECOMMEND [dataset]; DECIDE [dataset]; PREVIEW [dataset]"
        ),
        "description": (
            "Load data or run an AutoDQ analysis and decision step on the "
            "active or named dataset."
        ),
    },
    {
        "command": "ASSERT",
        "syntax": (
            "ASSERT Revenue NOT NULL; ASSERT Email FORMAT email; "
            "ASSERT ROW_COUNT > 0; "
            "ASSERT SUITE ADD release_gate Revenue MIN 0; "
            "ASSERT SUITE RUN release_gate [FAIL_ON error|warning|info|never]"
        ),
        "description": (
            "Evaluate non-mutating data-quality expectations or define, run, "
            "inspect, export, and load reusable test suites."
        ),
    },
    {
        "command": "SCHEMA",
        "syntax": (
            "SCHEMA CONTRACT CREATE name FROM dataset; "
            "SCHEMA CONTRACT VALIDATE name DATASET dataset [FAIL_ON level]"
        ),
        "description": (
            "Infer, refine, validate, inspect, export, and load versioned "
            "dataset schema contracts."
        ),
    },
    {
        "command": "CONTRACT",
        "syntax": (
            "CONTRACT name FROM dataset; "
            "CONTRACT name REQUIRE column TYPE numeric NOT NULL MIN 0; "
            "CONTRACT SHOW|LIST|SAVE|LOAD|DROP ..."
        ),
        "description": (
            "Create and manage schema contracts with concise, readable syntax. "
            "The legacy SCHEMA CONTRACT syntax remains supported."
        ),
    },
    {
        "command": "DRIFT",
        "syntax": (
            "DRIFT BASELINE CREATE name FROM dataset; "
            "DRIFT DETECT REFERENCE name DATASET dataset [CONTRACT name]"
        ),
        "description": (
            "Create reusable statistical baselines and detect schema, "
            "missingness, cardinality, range, category, and PSI drift."
        ),
    },
    {
        "command": "BASELINE",
        "syntax": (
            "BASELINE name FROM dataset; "
            "BASELINE SHOW|LIST|SAVE|LOAD|DROP ..."
        ),
        "description": (
            "Create and manage compact statistical drift baselines with "
            "concise syntax."
        ),
    },
    {
        "command": "CHECK",
        "syntax": (
            "CHECK CONTRACT name ON dataset [FAIL_ON level]; "
            "CHECK DRIFT baseline ON dataset [CONTRACT name] "
            "[SENSITIVITY strict|normal|relaxed]"
        ),
        "description": (
            "Validate a dataset against a contract or drift baseline without "
            "mutating the data."
        ),
    },
    {
        "command": "REVIEW / APPROVE / REJECT / CLEAN / VALIDATE",
        "syntax": (
            "REVIEW; APPROVE ALL|1,2; REJECT 3 REASON \"...\"; "
            "CLEAN; VALIDATE;"
        ),
        "description": "Review and explicitly apply cleaning decisions.",
    },
    {
        "command": "VISUALIZE",
        "syntax": "VISUALIZE bar X Region Y Revenue [TITLE \"Revenue\"]",
        "description": "Generate and register an AutoDQ visualization.",
    },
    {
        "command": "MODEL",
        "syntax": (
            "MODEL TARGET Revenue USING linear_regression; "
            "MODEL SAVE TO model.autodq; MODEL LOAD FROM model.autodq"
        ),
        "description": "Train, save, or load an AutoDQ model.",
    },
    {
        "command": "EXPLAIN / SHAP",
        "syntax": (
            "EXPLAIN MAX_ROWS 20; SHAP CHART summary; "
            "SHAP CHART waterfall ROW 0"
        ),
        "description": "Explain the active model and render SHAP plots.",
    },
    {
        "command": "PREDICT",
        "syntax": "PREDICT CONFIDENCE 0.95",
        "description": "Generate predictions and uncertainty diagnostics.",
    },
    {
        "command": "DASHBOARD",
        "syntax": (
            "DASHBOARD THEME executive SAVE \"reports/dashboard.html\" "
            "OVERWRITE"
        ),
        "description": "Build or export the current project dashboard.",
    },
    {
        "command": "AUTO",
        "syntax": (
            "AUTO MODE review|clean|full [VISUALIZE true|false] "
            "[REPORT path.html]"
        ),
        "description": "Run project.auto() with explicit allowlisted options.",
    },
    {
        "command": "WORKSPACE / ADD / LIST / MERGE / CONCAT",
        "syntax": (
            "WORKSPACE CREATE sales ROOT .autodq/workspaces; "
            "ADD DATASET costs FROM costs.csv; LIST DATASETS; "
            "PROFILE costs; AUTO DATASET costs MODE review; "
            "MERGE main WITH costs AS joined ON Product"
        ),
        "description": "Manage workspaces and multiple datasets.",
    },
    {
        "command": "EDIT / DOMAIN / OUTLIERS / AUDIT",
        "syntax": (
            "EDIT ROW 3 CHANGES '{\"Revenue\": 120}'; "
            "DOMAIN ADD Revenue MIN 0; DOMAIN VALIDATE; "
            "OUTLIERS REVIEW COLUMNS Revenue; AUDIT EXPORT TO audit.json"
        ),
        "description": "Perform traceable manual cleaning and domain review.",
    },
    {
        "command": "MISSING",
        "syntax": (
            "MISSING SUMMARY; MISSING FILL column VALUE value; "
            "MISSING FILL ALL STRATEGY auto; "
            "MISSING DROP ROWS [COLUMNS a,b] [HOW any|all]; "
            "MISSING DROP COLUMNS a,b|MIN_PERCENT n"
        ),
        "description": (
            "Summarize, fill, or remove missing data with a cell-level audit "
            "trail before CLEANING APPLY."
        ),
    },
    {
        "command": "DUPLICATES",
        "syntax": (
            "DUPLICATES SUMMARY; "
            "DUPLICATES DROP [KEEP first|last|none] [REASON text]"
        ),
        "description": (
            "Show every row in each exact-duplicate group or stage audited "
            "duplicate removal before CLEANING APPLY."
        ),
    },
    {
        "command": "KNOWLEDGE / CLEANING",
        "syntax": (
            "KNOWLEDGE; CLEANING PREVIEW ACTIONS 1,2 MAX_ROWS 5; "
            "CLEANING APPLY"
        ),
        "description": "Apply domain knowledge or inspect/apply review changes.",
    },
    {
        "command": "CORRELATION / READINESS / FEATURES / FEATURE",
        "syntax": (
            "CORRELATION MIN_ABS 0.3; READINESS [REFERENCE baseline]; "
            "FEATURES; "
            "FEATURE CREATE Margin METHOD difference COLUMNS Revenue,Cost"
        ),
        "description": (
            "Run analytical intelligence, transparent weighted ML readiness "
            "with optional PSI stability, and feature engineering."
        ),
    },
    {
        "command": "OPERATIONS / KPI / PROCESS / BOTTLENECKS / ROOT",
        "syntax": (
            "OPERATIONS [DATASET name] [TIME column] [DURATION column] "
            "[STATUS column] [SLA number]; KPI; PROCESS; BOTTLENECKS; "
            "ROOT CAUSE"
        ),
        "description": (
            "Recognize operational data, calculate KPIs, analyze process flow, "
            "rank bottlenecks, and surface evidence-based root-cause signals."
        ),
    },
    {
        "command": "INVENTORY",
        "syntax": (
            "INVENTORY [DATASET name] [ITEM sku] [LOCATION node] "
            "[ECHELON level] [ON_HAND stock] [DEMAND daily_demand]; "
            "INVENTORY NETWORK; INVENTORY REBALANCE"
        ),
        "description": (
            "Manage multi-echelon inventory position, coverage, shortage, "
            "excess, internal transfers, and replenishment requirements."
        ),
    },
    {
        "command": "BLUE / GALLERY",
        "syntax": (
            "BLUE; BLUE VISUALIZE; BLUE INTERPRET; BLUE PRESCRIBE; "
            "GALLERY LIST; GALLERY SAVE TO charts FORMAT png"
        ),
        "description": "Run BLUE diagnostics and manage reusable charts.",
    },
    {
        "command": "LET",
        "syntax": (
            "LET cleaned_customers = CLEANED; "
            "LET regional_sales = SELECT Region, SUM(Revenue) AS total "
            "FROM CURRENT GROUP BY Region"
        ),
        "description": (
            "Assign a stage, registered dataset, or SELECT result to a "
            "reusable named dataset snapshot."
        ),
    },
    {
        "command": "REPORT / EXPORT",
        "syntax": (
            "REPORT TO \"report.html\"; EXPORT CLEANED TO \"cleaned.csv\";"
        ),
        "description": "Export project artifacts to an explicit path.",
    },
    {
        "command": "SESSION",
        "syntax": (
            "SESSION; SESSION EVENTS [LIMIT n]; SESSION DATASETS"
        ),
        "description": (
            "Inspect the active project session, workflow events, or datasets."
        ),
    },
    {
        "command": "HELP / HISTORY",
        "syntax": "HELP [command]; HISTORY [LIMIT n]",
        "description": "Inspect ADQL syntax or recent query runs.",
    },
    {
        "command": "SET",
        "syntax": (
            "SET TARGET column; SET TYPE column datetime "
            "[FORMAT pattern] [DAYFIRST bool] [YEARFIRST bool] [UTC bool]; "
            "SET TYPE column float [DECIMALS n]"
        ),
        "description": (
            "Set the target or convert a column with explicit datetime "
            "parsing and numeric precision."
        ),
    },
    {
        "command": "USE / HEAD / TAIL / SAMPLE",
        "syntax": "USE DATASET name; HEAD 10; TAIL 10; SAMPLE 10",
        "description": "Update dataset context or inspect bounded data rows.",
    },
]
