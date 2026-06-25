from autodq.knowledge.library import DEFAULT_KNOWLEDGE_RULES
from autodq.knowledge.rules import KnowledgeRule


class KnowledgeEngine:
    """
    Provides domain-aware rules for common dataset columns.
    """

    def __init__(self, rules: dict[str, KnowledgeRule] | None = None):
        self.rules = rules or DEFAULT_KNOWLEDGE_RULES

    def get_rule(self, column_name: str) -> KnowledgeRule | None:
        column_lower = column_name.lower().strip()

        if column_lower in self.rules:
            return self.rules[column_lower]

        for keyword, rule in self.rules.items():
            if keyword in column_lower:
                return rule

        return None

    def get_rules_for_columns(self, columns: list[str]) -> dict[str, KnowledgeRule | None]:
        return {
            column: self.get_rule(column)
            for column in columns
        }