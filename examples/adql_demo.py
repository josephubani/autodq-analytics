"""Run safe analytical and workflow queries with AutoDQ ADQL."""

from autodq import ADQLFileRunner, AutoDQ


project = AutoDQ("datasets/sample/sales.csv", target="Revenue")

result = project.query(
    """
    PROFILE;
    DIAGNOSE;

    SELECT Region,
           SUM(Revenue) AS total_revenue,
           AVG(Profit) AS average_profit,
           COUNT(*) AS transactions
    FROM CURRENT
    WHERE Revenue > 100
    GROUP BY Region
    ORDER BY total_revenue DESC
    LIMIT 10;
    """,
    auto_display=False,
)

print(result.data)

# Execute a reusable ADQL script file.
script_result = project.run_adql(
    "examples/sales_analysis.adql",
    auto_display=False,
)
print(script_result.success)

# The same file runs by itself; no Python project or notebook is required.
standalone_result = ADQLFileRunner().run(
    "examples/sales_analysis.adql",
    auto_display=False,
)
print(standalone_result.success)
