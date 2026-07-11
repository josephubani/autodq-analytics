from autodq import AutoDQ

project = AutoDQ("datasets/sample/sales.csv")

project.add_dataset(
    name="customers",
    dataset_path="datasets/sample/customers.csv",
)

project.list_datasets()

merged = project.merge_datasets(
    left="main",
    right="customers",
    on="Customer_ID",
    how="left",
    validate="many_to_one",
    suffixes=("", "_customer"),
)

project.show_merge_report()

print(merged.head())
print(merged.shape)
project.set_type("Date", "datetime")
project.set_target("Revenue")

project.apply_knowledge()
project.show_knowledge()

project.profile()
project.show_profile()

project.statistics()
project.show_statistics()

project.interpret()
project.show_interpretations()

project.diagnose()
project.show_diagnosis()

project.recommend()
project.show_recommendations()

project.decide()
project.preview()
project.show_preview()

project.approve_all()
project.clean()
project.show_cleaning_report()

project.validate_cleaning()
project.show_validation()

project.visualize( chart = "auto")

project.visualize(chart="histogram", column="Revenue")
project.generate_report("reports/histogram_report.html", style="executive")

project.visualize(chart="boxplot", column="Revenue")
project.generate_report("reports/boxplot_report.html", style="executive")

project.visualize(chart="correlation_heatmap")
project.generate_report("reports/correlation_report.html", style="executive")

print(project.head())
print(project.tail())
print(project.sample(3))
project.info()

project.set_target("Revenue")

project.correlation()
project.show_correlation()

project.ml_readiness()
project.show_ml_readiness()

project.features()
project.show_features()

project.apply_features(["profit_margin", "Date_month", "revenue_per_unit"])
project.create_feature(
      name="log_unit_price",
      method="log",
      column="Unit_Price",
)

print(project.state.engineered_data.head())

project.model(algorithm="auto", exclude_leakage=True)
project.show_model()

project.predict()
project.show_predictions()
project.explain(max_rows=20)
project.show_explanations()

print(project.state.model_report is None)

print(project.state.prediction_report is None)

project.export_engineered("exports/engineered_sales.csv")
project.export_engineered("exports/manual_features_sales.xlsx")
project.export_engineered("exports/engineered_sales.xlsx")

project.export_current("exports/current_sales.csv")
project.export_cleaned("exports/cleaned_sales.csv")
project.export_cleaned("exports/cleaned_sales.xlsx")

project.generate_report("reports/autodq_executive.html", style="executive")
project.generate_report("reports/autodq_dark.html", style="dark")
project.generate_report("reports/autodq_print.html", style="print")
project.generate_report("reports/autodq_explainability.html",style="executive",)
project.generate_report("reports/ml_prediction_report.html",style="executive",)
project.generate_report("reports/ml_prediction_report_dark.html",style="dark",
)

project.show_session()

