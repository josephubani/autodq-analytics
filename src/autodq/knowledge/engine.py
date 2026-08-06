from __future__ import annotations

import re
from collections.abc import Iterable

from autodq.knowledge.library import (
    DEFAULT_KNOWLEDGE_ALIASES,
    DEFAULT_KNOWLEDGE_RULES,
)
from autodq.knowledge.rules import KnowledgeRule


class KnowledgeEngine:
    """
    Provides domain-aware rules for common dataset columns.

    Matching remains column-name based, but understands snake_case, kebab-case,
    spaces, punctuation, and CamelCase. Multi-word aliases win over generic
    words, so ``UnitPrice`` resolves to the unit-price rule while names such as
    ``average_revenue`` no longer accidentally match ``age``.
    """

    def __init__(
        self,
        rules: dict[str, KnowledgeRule] | None = None,
        aliases: dict[str, Iterable[str]] | None = None,
    ):
        using_defaults = rules is None
        self.rules = DEFAULT_KNOWLEDGE_RULES if using_defaults else rules

        base_aliases = DEFAULT_KNOWLEDGE_ALIASES if using_defaults else {}
        self.aliases = {
            key: tuple(values)
            for key, values in base_aliases.items()
        }
        if aliases:
            for key, values in aliases.items():
                self.aliases[key] = tuple(values)

        self._matchers = self._build_matchers()

    @staticmethod
    def _normalize(value: object) -> str:
        text = str(value).strip()
        text = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", text)
        text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
        return " ".join(re.findall(r"[a-z0-9]+", text.lower()))

    @staticmethod
    def _contains_phrase(
        column_tokens: tuple[str, ...],
        alias_tokens: tuple[str, ...],
    ) -> bool:
        width = len(alias_tokens)
        if width == 0 or width > len(column_tokens):
            return False
        return any(
            column_tokens[index : index + width] == alias_tokens
            for index in range(len(column_tokens) - width + 1)
        )

    def _build_matchers(
        self,
    ) -> list[tuple[str, KnowledgeRule, str, tuple[str, ...], int]]:
        matchers = []
        seen = set()

        for order, (key, rule) in enumerate(self.rules.items()):
            candidates = [key, rule.name]
            candidates.extend(self.aliases.get(key, ()))

            metadata_aliases = rule.metadata.get("aliases", ())
            if isinstance(metadata_aliases, str):
                candidates.append(metadata_aliases)
            else:
                candidates.extend(metadata_aliases)

            for candidate in candidates:
                normalized = self._normalize(candidate)
                marker = (key, normalized)
                if not normalized or marker in seen:
                    continue
                seen.add(marker)
                matchers.append(
                    (key, rule, normalized, tuple(normalized.split()), order)
                )

        return matchers

    def get_rule(self, column_name: str) -> KnowledgeRule | None:
        normalized = self._normalize(column_name)
        if not normalized:
            return None

        column_tokens = tuple(normalized.split())
        collapsed = normalized.replace(" ", "")
        matches = []

        for key, rule, alias, alias_tokens, order in self._matchers:
            exact = normalized == alias or collapsed == alias.replace(" ", "")
            phrase = self._contains_phrase(column_tokens, alias_tokens)
            if not exact and not phrase:
                continue

            # Exact full-name matches beat phrase matches. Longer aliases then
            # beat generic ones; catalog order provides stable final tie-breaking.
            score = (int(exact), len(alias_tokens), len(alias), -order)
            matches.append((score, key, rule))

        if not matches:
            return None

        return max(matches, key=lambda item: item[0])[2]

    def get_rules_for_columns(
        self,
        columns: list[str],
    ) -> dict[str, KnowledgeRule | None]:
        return {column: self.get_rule(column) for column in columns}
