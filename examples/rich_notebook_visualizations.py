"""Notebook-friendly AutoDQ visualization customization example."""

import os
from pathlib import Path

from autodq import AutoDQ


DATASET = os.getenv(
    "AUTODQ_NOTEBOOK_DATASET",
    "datasets/sample/sales.csv",
)
OUTPUT_DIR = Path(
    os.getenv(
        "AUTODQ_NOTEBOOK_OUTPUT",
        ".autodq/notebook_gallery",
    )
)


project = AutoDQ(DATASET, target="Revenue")

# In Jupyter, this call displays a rich HTML chart card automatically.
report = project.visualize(
    chart="bar",
    x="Region",
    y="Revenue",
    title="Revenue by Region",
    subtitle="Current sales dataset",
    x_label="Region",
    y_label="Revenue (CAD)",
    theme="light",
    palette="colorblind",
    figsize=(10, 6),
    dpi=180,
    grid=True,
    legend=False,
)

# Every result is reusable and can be restyled, shown, cloned, or saved.
chart = report.latest
chart.save(OUTPUT_DIR / "revenue_by_region.png")

publication_chart = chart.clone(
    "revenue_by_region_publication"
).reset_style().customize(
    template="publication",
    subtitle="AutoDQ publication-ready output",
)
publication_chart.save(OUTPUT_DIR / "revenue_by_region.pdf")

project.visualize(
    chart="scatter",
    x="Quantity",
    y="Revenue",
    title="Quantity and Revenue",
    theme="dark",
    color="#38bdf8",
    display=False,
)

exported = project.save_visualizations(
    str(OUTPUT_DIR / "gallery"),
    format="svg",
)

print(f"Gallery charts: {project.visualization_gallery.chart_count}")
print(f"Reusable chart: {chart.chart_id}")
print(f"Exported files: {len(exported) + 2}")
print(f"Output directory: {OUTPUT_DIR.resolve()}")
