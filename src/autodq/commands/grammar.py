"""Grammar constants for the AutoDQ Analytics Domain Query Language."""

SUPPORTED_COMMANDS = {
    "SELECT",
    "DATASET",
    "LOAD",
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
    "AUTO",
    "VISUALIZE",
    "MODEL",
    "PREDICT",
    "DASHBOARD",
    "REPORT",
    "EXPORT",
    "SET",
    "USE",
    "HEAD",
    "TAIL",
    "SAMPLE",
    "HELP",
    "HISTORY",
}

SIMPLE_COMMANDS = {
    "LOAD",
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
    "REFRESH": "refresh",
    "CONTINUE_ON_ERROR": "continue_on_error",
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
            "PREDICTIONS [WHERE ...] [GROUP BY ...] [ORDER BY ...] [LIMIT n]"
        ),
        "description": "Run a safe pandas-backed analytical query.",
    },
    {
        "command": "PROFILE / DIAGNOSE / RECOMMEND",
        "syntax": "PROFILE; DIAGNOSE; RECOMMEND;",
        "description": "Run an AutoDQ analysis workflow step.",
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
        "syntax": "MODEL TARGET Revenue USING linear_regression",
        "description": "Train a model through the project API.",
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
        "syntax": "AUTO MODE review|clean|full [VISUALIZE true|false]",
        "description": "Run project.auto() with explicit allowlisted options.",
    },
    {
        "command": "REPORT / EXPORT",
        "syntax": (
            "REPORT TO \"report.html\"; EXPORT CLEANED TO \"cleaned.csv\";"
        ),
        "description": "Export project artifacts to an explicit path.",
    },
    {
        "command": "HELP / HISTORY",
        "syntax": "HELP [command]; HISTORY [LIMIT n]",
        "description": "Inspect ADQL syntax or recent query runs.",
    },
    {
        "command": "SET / USE / HEAD / TAIL / SAMPLE",
        "syntax": (
            "SET TARGET column; USE DATASET name; HEAD 10; "
            "TAIL 10; SAMPLE 10"
        ),
        "description": "Update project context or inspect bounded data rows.",
    },
]
