"""Build an interactive AutoDQ dashboard in a notebook or Python script."""

from autodq import AutoDQ


project = AutoDQ("data/sales.csv", target="Revenue")

# The dashboard prepares missing profile, diagnosis, and automatic charts.
# In Jupyter, leave auto_display=True to render the result automatically.
dashboard = project.dashboard(
    title="Sales Quality & Performance",
    subtitle="Latest data-quality, cleaning, and modeling results",
    theme="executive",
    max_preview_rows=25,
    auto_display=False,
)

dashboard.show()

# The exported file contains its CSS, JavaScript, data preview, and chart images.
dashboard.save("reports/sales-dashboard.html", overwrite=True)

# Reuse and inspect the generated dashboard object.
print(dashboard.get_metric("quality_score").display)
print(dashboard.chart_count)
print(dashboard.to_dict()["stage"])
