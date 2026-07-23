"""Grammar constants for the AutoDQ Analytics Domain Query Language."""

SUPPORTED_COMMANDS = {
    "SELECT",
    "DATASET",
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
    "DOMAIN",
    "OUTLIERS",
    "AUDIT",
    "CORRELATION",
    "READINESS",
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
            "CORRELATION MIN_ABS 0.3; READINESS; FEATURES; "
            "FEATURE CREATE Margin METHOD difference COLUMNS Revenue,Cost"
        ),
        "description": "Run analytical intelligence and feature engineering.",
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
