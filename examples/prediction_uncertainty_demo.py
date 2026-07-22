"""End-to-end prediction uncertainty example."""

import numpy as np
import pandas as pd
from pathlib import Path
from tempfile import TemporaryDirectory

from autodq import AutoDQ


rng = np.random.default_rng(42)
row_count = 160
sales = pd.DataFrame(
    {
        "units": rng.integers(1, 60, row_count),
        "price": rng.uniform(10, 150, row_count),
        "discount": rng.uniform(0, 0.3, row_count),
        "region": rng.choice(["North", "South", "West"], row_count),
    }
)
sales["revenue"] = (
    sales["units"] * sales["price"] * (1 - sales["discount"])
    + rng.normal(0, 45, row_count)
)

temporary_directory = TemporaryDirectory()
dataset_path = Path(temporary_directory.name) / "sales.csv"
sales.to_csv(dataset_path, index=False)
project = AutoDQ(str(dataset_path), target="revenue")
project.model(algorithm="random_forest_regressor", use_engineered=False)
predictions = project.predict(confidence_level=0.9)
report = project.state.prediction_report

print(
    predictions[
        [
            "AutoDQ_Prediction",
            "AutoDQ_Prediction_Lower",
            "AutoDQ_Prediction_Upper",
            "AutoDQ_Interval_Width",
        ]
    ].head()
)
print(f"Method: {report.uncertainty_method}")
print(f"Calibration rows: {report.calibration_size}")
print(f"Observed coverage: {report.empirical_coverage:.1%}")
print(f"Mean interval width: {report.mean_interval_width:.2f}")

# For classifiers, project.predict() also adds AutoDQ_Confidence,
# AutoDQ_Uncertainty, AutoDQ_Prediction_Margin, AutoDQ_Entropy,
# AutoDQ_Low_Confidence, and one probability column per class.
temporary_directory.cleanup()
