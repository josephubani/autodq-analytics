"""Create, save, list, and reopen an isolated AutoDQ workspace."""

import os
import warnings
from pathlib import Path

import numpy as np

from autodq import AutoDQ


DATASET = os.getenv(
    "AUTODQ_WORKSPACE_DATASET",
    "datasets/sample/sales.csv",
)
WORKSPACE_ROOT = os.getenv(
    "AUTODQ_WORKSPACE_ROOT",
    ".autodq/workspaces",
)
WORKSPACE_NAME = os.getenv(
    "AUTODQ_WORKSPACE_NAME",
    "Sales Analysis",
)


try:
    project = AutoDQ.create_workspace(
        WORKSPACE_NAME,
        DATASET,
        target="Revenue",
        workspace_root=WORKSPACE_ROOT,
    )
except FileExistsError:
    project = AutoDQ.open_workspace(
        WORKSPACE_NAME,
        workspace_root=WORKSPACE_ROOT,
        load_model=False,
    )

project.model(
    algorithm="decision_tree_regressor",
    use_engineered=False,
)
predictions_before = project.predict()[
    "AutoDQ_Prediction"
].to_numpy()
workspace_info = project.save_workspace()

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    restored = AutoDQ.open_workspace(
        WORKSPACE_NAME,
        workspace_root=WORKSPACE_ROOT,
    )

predictions_after = restored.predict()[
    "AutoDQ_Prediction"
].to_numpy()

if not np.allclose(predictions_before, predictions_after):
    raise RuntimeError("Restored workspace predictions do not match.")

available = AutoDQ.list_workspaces(WORKSPACE_ROOT)

print(f"Workspace: {restored.workspace_name}")
print(f"Path: {Path(workspace_info['path']).resolve()}")
print(f"Datasets: {restored.dataset_manager.names()}")
print(f"Model restored: {restored.state.model_report is not None}")
print("Predictions match: True")
print(f"Available workspaces: {[item.workspace_id for item in available]}")
