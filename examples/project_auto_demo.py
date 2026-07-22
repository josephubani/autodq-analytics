"""Safe and full project.auto() workflows."""

from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import pandas as pd

from autodq import AutoDQ


rng = np.random.default_rng(42)
row_count = 100
sales = pd.DataFrame(
    {
        "Units": rng.integers(1, 50, row_count),
        "Price": rng.uniform(10, 130, row_count),
        "Discount": rng.uniform(0, 0.25, row_count),
        "Region": rng.choice(["North", "South", "West"], row_count),
    }
)
sales["Revenue"] = (
    sales["Units"] * sales["Price"] * (1 - sales["Discount"])
    + rng.normal(0, 25, row_count)
)
sales.loc[4, "Units"] = np.nan
sales = pd.concat([sales, sales.iloc[[0]]], ignore_index=True)

temporary_directory = TemporaryDirectory()
dataset_path = Path(temporary_directory.name) / "sales.csv"
sales.to_csv(dataset_path, index=False)
project = AutoDQ(str(dataset_path), target="Revenue")

# Safe default: analyze everything and stop at the cleaning review.
review_run = project.auto(visualize=False, auto_display=False)
print("Review run success:", review_run.success)
print("Pending actions:", review_run.review.pending_count)
print("Next actions:", review_run.next_actions)

# Explicit full mode: approve, clean, validate, train, and predict.
full_run = project.auto(
    mode="full",
    algorithm="decision_tree_regressor",
    explain_model=False,
    visualize=False,
    auto_display=False,
)
print("Full run success:", full_run.success)
print("Completed stages:", full_run.completed_count)
print("Prediction rows:", len(project.state.prediction_data))
temporary_directory.cleanup()
