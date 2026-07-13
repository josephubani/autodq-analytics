from autodq import AutoDQ


# ============================================================
# 1. CREATE PROJECT AND REGISTER DATASETS
# ============================================================

project = AutoDQ(
    "datasets/sample/sales.csv",
    target="Revenue",
)

project.add_dataset(
    name="customers",
    dataset_path="datasets/sample/customers.csv",
)

project.list_datasets()


# ============================================================
# 2. MERGE DATASETS
# ============================================================

merged = project.merge_datasets(
    left="main",
    right="customers",
    output_name="sales_with_customers",
    on="Customer_ID",
    how="left",
    validate="many_to_one",
    suffixes=("", "_customer"),
    make_active=True,
)

project.show_merge_report()

print("\nMerged Dataset Preview:")
print(merged.head())

print("\nMerged Dataset Shape:")
print(merged.shape)


# ============================================================
# 3. DATA TYPE AND TARGET CONFIGURATION
# ============================================================

project.set_type(
    column="Date",
    dtype="datetime",
)

project.set_target("Revenue")


# ============================================================
# 4. KNOWLEDGE LAYER
# ============================================================

project.apply_knowledge()
project.show_knowledge()


# ============================================================
# 5. DATA PROFILING
# ============================================================

project.profile()
project.show_profile()


# ============================================================
# 6. STATISTICAL ANALYSIS AND INTERPRETATION
# ============================================================

project.statistics()
project.show_statistics()

project.interpret()
project.show_interpretations()


# ============================================================
# 7. DATA QUALITY DIAGNOSIS
# ============================================================

project.diagnose()
project.show_diagnosis()


# ============================================================
# 8. CLEANING RECOMMENDATIONS AND DECISION PLAN
# ============================================================

project.recommend()
project.show_recommendations()

project.decide()

project.preview()
project.show_preview()


# ============================================================
# 9. APPLY CLEANING
# ============================================================

project.approve_all()

project.clean()
project.show_cleaning_report()

project.validate_cleaning()
project.show_validation()


# ============================================================
# 10. DATA PREVIEW
# ============================================================

print("\nFirst 5 Rows:")
print(project.head())

print("\nLast 5 Rows:")
print(project.tail())

print("\nRandom Sample:")
print(project.sample(3))

project.info()


# ============================================================
# 11. VISUALIZATION ENGINE
# ============================================================

# Automatically recommended visualizations
project.visualize(
    chart="auto",
    stage="after",
)

# Manually selected visualizations
project.visualize(
    chart="histogram",
    column="Revenue",
    stage="after",
)

project.visualize(
    chart="boxplot",
    column="Revenue",
    stage="after",
)

project.visualize(
    chart="correlation_heatmap",
    stage="after",
)

project.show_visualizations()


# ============================================================
# 12. CORRELATION ANALYSIS
# ============================================================

project.correlation()
project.show_correlation()


# ============================================================
# 13. MACHINE LEARNING READINESS
# ============================================================

project.ml_readiness()
project.show_ml_readiness()


# ============================================================
# 14. FEATURE ENGINEERING RECOMMENDATIONS
# ============================================================

project.features()
project.show_features()


# ============================================================
# 15. APPLY SELECTED RECOMMENDED FEATURES
# ============================================================

project.apply_features(
    [
        "profit_margin",
        "Date_month",
        "revenue_per_unit",
    ]
)


# ============================================================
# 16. CREATE MANUAL FEATURES
# ============================================================

project.create_feature(
    name="log_unit_price",
    method="log",
    column="Unit_Price",
)

print("\nEngineered Dataset Preview:")
print(project.state.engineered_data.head())


# ============================================================
# 17. BLUE REGRESSION DIAGNOSTICS
# ============================================================

project.blue(
    source="data",
    use_engineered=True,
    exclude_leakage=True,
    max_features=15,
    leakage_threshold=0.98,
)

project.show_blue()

blue_visuals = project.visualize_blue(

    display=True,

)

print(

    "BLUE charts generated:",

    blue_visuals.chart_count,

)

# ============================================================
# 18. MODEL TRAINING AND COMPARISON
# ============================================================

project.model(
    algorithm="auto",
    exclude_leakage=True,
)

project.show_model()


# ============================================================
# 19. PREDICTION
# ============================================================

project.predict()
project.show_predictions()


# ============================================================
# 20. SHAP EXPLAINABILITY
# ============================================================

project.explain(
    max_rows=20,
    use_engineered=True,
)

project.show_explanations()


# ============================================================
# 21. VERIFY ML STATE
# ============================================================

print(
    "\nModel Report Available:",
    project.state.model_report is not None,
)

print(
    "Prediction Report Available:",
    project.state.prediction_report is not None,
)

print(
    "Explainability Report Available:",
    project.state.explainability_report is not None,
)

print(
    "BLUE Report Available:",
    project.state.blue_report is not None,
)


# ============================================================
# 22. EXPORT DATASETS
# ============================================================

project.export_current(
    "exports/current_sales.csv",
)

project.export_cleaned(
    "exports/cleaned_sales.csv",
)

project.export_cleaned(
    "exports/cleaned_sales.xlsx",
)

project.export_engineered(
    "exports/engineered_sales.csv",
)

project.export_engineered(
    "exports/engineered_sales.xlsx",
)

project.export_engineered(
    "exports/manual_features_sales.xlsx",
)


# ============================================================
# 23. GENERATE FINAL REPORTS
# ============================================================

# Generate final reports only after cleaning, statistics,
# visualizations, BLUE, modelling, prediction, and SHAP.

project.generate_report(
    "reports/autodq_executive.html",
    style="executive",
)

project.generate_report(
    "reports/autodq_dark.html",
    style="dark",
)

project.generate_report(
    "reports/autodq_print.html",
    style="print",
)


# ============================================================
# 24. SESSION SUMMARY
# ============================================================

project.show_session()