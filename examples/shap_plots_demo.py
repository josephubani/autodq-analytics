"""
Run from the AutoDQ repository root:

    python examples/shap_plots_demo.py

The same statements can be copied into a Jupyter notebook cell. Set
DISPLAY_IN_NOTEBOOK to True when running in Jupyter.
"""

import os
from pathlib import Path

from autodq import AutoDQ


DATASET = os.getenv(
    "AUTODQ_SHAP_DATASET",
    "datasets/sample/sales.csv",
)
TARGET = os.getenv("AUTODQ_SHAP_TARGET", "Revenue")
OUTPUT_DIR = Path(
    os.getenv("AUTODQ_SHAP_OUTPUT", "exports/shap")
)
DISPLAY_IN_NOTEBOOK = (
    os.getenv("AUTODQ_SHAP_DISPLAY", "false").lower()
    == "true"
)


project = AutoDQ(
    DATASET,
    target=TARGET,
)

model_report = project.model(
    algorithm="decision_tree_regressor",
    use_engineered=False,
)
project.predict()
explanation_report = project.explain(
    max_rows=50,
    use_engineered=False,
)

if not explanation_report.has_shap_artifacts:
    warnings = "\n".join(explanation_report.warnings)
    raise RuntimeError(
        "SHAP artifacts were not generated:\n"
        f"{warnings}"
    )

available_features = (
    explanation_report.shap_artifacts.feature_names
)
dependence_feature = (
    "Quantity"
    if "Quantity" in available_features
    else available_features[0]
)

project.visualize_shap(
    chart="summary",
    save=str(OUTPUT_DIR / "summary.png"),
    display=DISPLAY_IN_NOTEBOOK,
)
project.visualize_shap(
    chart="bar",
    save=str(OUTPUT_DIR / "bar.png"),
    display=DISPLAY_IN_NOTEBOOK,
)
project.visualize_shap(
    chart="beeswarm",
    save=str(OUTPUT_DIR / "beeswarm.png"),
    display=DISPLAY_IN_NOTEBOOK,
)
project.visualize_shap(
    chart="waterfall",
    row=0,
    save=str(OUTPUT_DIR / "waterfall.png"),
    display=DISPLAY_IN_NOTEBOOK,
)
project.visualize_shap(
    chart="dependence",
    feature=dependence_feature,
    save=str(OUTPUT_DIR / "dependence.png"),
    display=DISPLAY_IN_NOTEBOOK,
)

print(f"Model: {model_report.algorithm}")
print(f"SHAP method: {explanation_report.method}")
print(f"Explained rows: {explanation_report.explanation_count}")
print(f"Dependence feature: {dependence_feature}")
print(f"Plots saved to: {OUTPUT_DIR.resolve()}")
