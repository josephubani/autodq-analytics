import re
import unittest
from pathlib import Path

from autodq import (
    ADQL_LANGUAGE_VERSION,
    ADQLParser,
    ADQLSyntaxError,
    ADQLValidationError,
    ADQLValidator,
)
from autodq.commands.grammar import SUPPORTED_COMMANDS


ROOT = Path(__file__).resolve().parents[1]
SPEC_ROOT = ROOT / "docs" / "adql"


class ADQLSpecificationConformanceTests(unittest.TestCase):
    def test_public_language_version_matches_normative_documents(self):
        specification = (SPEC_ROOT / "SPECIFICATION.md").read_text(
            encoding="utf-8"
        )
        grammar = (SPEC_ROOT / "grammar.ebnf").read_text(encoding="utf-8")

        self.assertEqual(ADQL_LANGUAGE_VERSION, "2.0")
        self.assertIn(
            f"| Language version | {ADQL_LANGUAGE_VERSION} |",
            specification,
        )
        self.assertIn(
            f'language-version = "{ADQL_LANGUAGE_VERSION}" ;',
            grammar,
        )

    def test_grammar_inventory_matches_runtime_command_inventory(self):
        grammar = (SPEC_ROOT / "grammar.ebnf").read_text(encoding="utf-8")
        specified_commands = set(
            re.findall(r"\(\* command: ([A-Z]+) \*\)", grammar)
        )

        self.assertSetEqual(specified_commands, SUPPORTED_COMMANDS)

    def test_grammar_references_only_defined_productions(self):
        grammar = (SPEC_ROOT / "grammar.ebnf").read_text(encoding="utf-8")
        grammar = re.sub(r"\(\*.*?\*\)", "", grammar, flags=re.DOTALL)
        grammar_without_terminals = re.sub(
            r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'',
            "",
            grammar,
        )
        definitions = set(
            re.findall(
                r"(?m)^([a-z][a-z0-9-]*)\s*=",
                grammar_without_terminals,
            )
        )
        references = set(
            re.findall(r"\b[a-z][a-z0-9-]*\b", grammar_without_terminals)
        )
        host_character_classes = {
            "any-character",
            "bare-character",
            "character-except-single-quote",
            "character-except-double-quote",
            "character-except-backtick",
        }

        self.assertSetEqual(
            references - definitions,
            host_character_classes,
        )

    def test_normative_companion_documents_exist_and_are_linked(self):
        specification = (SPEC_ROOT / "SPECIFICATION.md").read_text(
            encoding="utf-8"
        )
        companions = {
            "grammar.ebnf",
            "execution-model.md",
            "data-types.md",
            "errors.md",
            "compatibility.md",
        }

        for filename in companions:
            with self.subTest(filename=filename):
                self.assertTrue((SPEC_ROOT / filename).is_file())
                self.assertIn(f"({filename})", specification)

    def test_normative_workflow_examples_parse_and_validate(self):
        source = """
        DATASET "sales.csv" TARGET Revenue;
        ADD DATASET customers FROM "customers.csv";
        PROFILE customers;
        MISSING DATASET customers SUMMARY;
        MISSING DATASET customers FILL ALL STRATEGY auto;
        DUPLICATES DATASET customers SUMMARY;
        DUPLICATES DATASET customers DROP KEEP first REASON "Imported twice";
        CLEANING DATASET customers APPLY;
        LET clean_customers = CLEANED;
        SET DATASET customers TYPE Created_At datetime FORMAT ISO8601 UTC true;
        SELECT Region, SUM(Revenue) AS total_revenue
        FROM CURRENT
        WHERE Region IN ("North", "South") AND Revenue >= 100
        GROUP BY Region
        ORDER BY total_revenue DESC
        LIMIT 25;
        SESSION DATASETS;
        """
        script = ADQLParser().parse(source)

        ADQLValidator().validate(script)
        self.assertEqual(script.statement_count, 12)

    def test_normative_safety_limits_match_runtime(self):
        validator = ADQLValidator()

        self.assertEqual(validator.MAX_SOURCE_LENGTH, 100_000)
        self.assertEqual(validator.MAX_STATEMENTS, 100)
        self.assertEqual(validator.MAX_QUERY_ROWS, 10_000)
        self.assertEqual(validator.MAX_WHERE_CONDITIONS, 50)

        with self.assertRaises(ADQLValidationError):
            script = ADQLParser().parse(
                "SELECT * FROM CURRENT LIMIT 10001;"
            )
            validator.validate(script)

    def test_adql_2_rejects_or_with_versioned_diagnostic(self):
        with self.assertRaisesRegex(ADQLSyntaxError, r"ADQL 2\.0"):
            ADQLParser().parse(
                "SELECT * FROM CURRENT WHERE Region = North OR Region = South;"
            )


if __name__ == "__main__":
    unittest.main()
