def pretty_algorithm_name(name: str | None) -> str:
    """
    Convert internal ML algorithm names into clean display names.
    """

    if name is None:
        return "Unknown"

    mapping = {
        "linear_regression": "Linear Regression",
        "logistic_regression": "Logistic Regression",

        "decision_tree_regressor": "Decision Tree Regressor",
        "decision_tree_classifier": "Decision Tree Classifier",

        "random_forest_regressor": "Random Forest Regressor",
        "random_forest_classifier": "Random Forest Classifier",

        "gradient_boosting_regressor": "Gradient Boosting Regressor",
        "gradient_boosting_classifier": "Gradient Boosting Classifier",

        "xgboost_regressor": "XGBoost Regressor",
        "xgboost_classifier": "XGBoost Classifier",

        "lightgbm_regressor": "LightGBM Regressor",
        "lightgbm_classifier": "LightGBM Classifier",

        "knn_classifier": "K-Nearest Neighbors Classifier",
        "svm_classifier": "Support Vector Machine Classifier",

        "kmeans": "K-Means Clustering",
        "dbscan": "DBSCAN Clustering",
        "pca": "Principal Component Analysis",
    }

    return mapping.get(name, name.replace("_", " ").title())