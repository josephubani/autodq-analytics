from autodq.knowledge.rules import KnowledgeRule


DEFAULT_KNOWLEDGE_RULES = {
    "age": KnowledgeRule(
        name="age",
        semantic_type="continuous_numeric",
        expected_min=0,
        expected_max=120,
        allow_negative=False,
        preferred_imputation="median",
        preferred_outlier_strategy="domain_range_check",
        notes=["Age usually falls between 0 and 120."],
    ),
    "revenue": KnowledgeRule(
        name="revenue",
        semantic_type="currency",
        expected_min=0,
        allow_negative=False,
        preferred_imputation="median",
        preferred_outlier_strategy="review_or_winsorize",
        notes=["Revenue is usually non-negative and may contain valid business outliers."],
    ),
    "profit": KnowledgeRule(
        name="profit",
        semantic_type="currency",
        allow_negative=True,
        preferred_imputation="median",
        preferred_outlier_strategy="review_or_winsorize",
        notes=["Profit may be negative depending on business context."],
    ),
    "discount": KnowledgeRule(
        name="discount",
        semantic_type="percentage_or_amount",
        expected_min=0,
        allow_negative=False,
        preferred_imputation="median",
        preferred_outlier_strategy="domain_range_check",
        notes=["Discounts are usually non-negative."],
    ),
    "quantity": KnowledgeRule(
        name="quantity",
        semantic_type="discrete_numeric",
        expected_min=0,
        allow_negative=False,
        preferred_imputation="median",
        preferred_outlier_strategy="review_or_cap",
        notes=["Quantity should usually be non-negative."],
    ),
    "date": KnowledgeRule(
        name="date",
        semantic_type="datetime",
        preferred_imputation="do_not_impute_without_context",
        notes=["Date fields should be parsed as datetime."],
    ),
}