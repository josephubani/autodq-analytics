"""Train, save, load, predict, and explain a persisted AutoDQ model."""

import os
from pathlib import Path

import numpy as np

from autodq import AutoDQ


DATASET = os.getenv(
    "AUTODQ_MODEL_DATASET",
    "datasets/sample/sales.csv",
)
MODEL_DIR = Path(
    os.getenv(
        "AUTODQ_MODEL_OUTPUT",
        "models/revenue_model",
    )
)


training_project = AutoDQ(
    DATASET,
    target="Revenue",
)
training_project.model(
    algorithm="decision_tree_regressor",
    use_engineered=False,
)
predictions_before = training_project.predict()[
    "AutoDQ_Prediction"
].to_numpy()
bundle = training_project.save_model(
    str(MODEL_DIR),
    overwrite=True,
)

loaded_project = AutoDQ(DATASET)
loaded_report = loaded_project.load_model(str(MODEL_DIR))
predictions_after = loaded_project.predict()[
    "AutoDQ_Prediction"
].to_numpy()

if not np.allclose(predictions_before, predictions_after):
    raise RuntimeError(
        "Loaded model predictions do not match the original model."
    )

explanation = loaded_project.explain(
    max_rows=20,
    use_engineered=False,
)
shap_output = MODEL_DIR.parent / (
    f"{MODEL_DIR.name}_shap_summary.png"
)
loaded_project.visualize_shap(
    chart="summary",
    save=str(shap_output),
    display=False,
)

print(f"Bundle: {bundle.path}")
print(f"Format version: {bundle.manifest.format_version}")
print(f"Algorithm: {loaded_report.algorithm}")
print(f"Target: {loaded_report.target}")
print(f"Predictions match: True")
print(f"SHAP restored: {explanation.has_shap_artifacts}")
print(f"SHAP plot: {shap_output.resolve()}")
