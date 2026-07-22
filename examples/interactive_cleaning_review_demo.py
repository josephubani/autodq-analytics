"""Notebook-friendly interactive cleaning and domain review example."""

from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from autodq import AutoDQ


data = pd.DataFrame(
    {
        "Age": [25, 31, -4, 39, 240, 34, 28, 30, 33],
        "Revenue": [100, 110, 125, 130, 9000, 145, 150, 160, 170],
        "Region": [
            "North",
            "South",
            "Unknown",
            "West",
            "West",
            "North",
            "South",
            None,
            "West",
        ],
    }
)

temporary_directory = TemporaryDirectory()
dataset_path = Path(temporary_directory.name) / "review.csv"
data.to_csv(dataset_path, index=False)
project = AutoDQ(str(dataset_path))

# Returning this object as the final notebook expression renders the review UI.
review = project.review_cleaning()
print(review.to_dict()["action_count"], "proposed cleaning actions")

# Approve or reject individual recommendation IDs after reviewing them.
if review.actions:
    review.approve(review.actions[0].action_id)

if len(review.actions) > 1:
    review.reject(
        [action.action_id for action in review.actions[1:]],
        reason="Requires business-owner confirmation.",
    )

# Manual corrections are cell-level audited.
review.edit_row(
    2,
    {"Age": 24, "Region": "North"},
    reason="Corrected from the source record.",
)

# Add business rules and inspect row-level violations.
review.add_domain_rule(
    "Region",
    allowed_values=["North", "South", "West"],
    nullable=False,
)
domain_report = review.validate_domain()
print("Domain violations:", domain_report.violation_count)

# Inspect and clip Revenue outliers; each changed cell enters the audit trail.
outliers = review.review_outliers("Revenue")
print("Revenue outliers:", outliers.outlier_count)
review.treat_outliers(
    "Revenue",
    strategy="clip",
    reason="Reviewed IQR cap.",
)

cleaned = project.apply_cleaning_review()
audit_path = review.export_audit(
    Path(temporary_directory.name) / "cleaning_audit.json"
)
print("Cleaned rows:", len(cleaned))
print("Audit entries:", review.audit_count)
print("Audit file:", audit_path)
temporary_directory.cleanup()
