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
from autodq.commands.grammar import COMMAND_HELP, SUPPORTED_COMMANDS


ROOT = Path(__file__).resolve().parents[1]
SPEC_ROOT = ROOT / "docs" / "adql"


class ADQLSpecificationConformanceTests(unittest.TestCase):
    @staticmethod
    def _mixed_case(value):
        return "".join(
            character.lower() if index % 2 else character.upper()
            for index, character in enumerate(value)
        )

    def test_public_language_version_matches_normative_documents(self):
        specification = (SPEC_ROOT / "SPECIFICATION.md").read_text(
            encoding="utf-8"
        )
        grammar = (SPEC_ROOT / "grammar.ebnf").read_text(encoding="utf-8")

        self.assertEqual(ADQL_LANGUAGE_VERSION, "2.1")
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

    def test_every_public_command_accepts_mixed_case(self):
        examples = {
            "ADD": 'ADD DATASET CustomerData FROM "customers.csv"',
            "APPROVE": "APPROVE ALL",
            "ASSERT": "ASSERT Revenue NOT NULL",
            "AUDIT": 'AUDIT EXPORT TO "audit.json"',
            "AUTO": "AUTO MODE review VISUALIZE false",
            "BLUE": "BLUE MAX_FEATURES 4",
            "CLEAN": "CLEAN",
            "CLEANING": "CLEANING PREVIEW MAX_ROWS 5",
            "CONCAT": "CONCAT SalesData,CustomerData AS Combined",
            "CORRELATION": "CORRELATION MIN_ABS 0.2",
            "DASHBOARD": "DASHBOARD THEME dark DISPLAY false",
            "DATASET": 'DATASET "sales.csv" TARGET Revenue',
            "DECIDE": "DECIDE",
            "DIAGNOSE": "DIAGNOSE",
            "DOMAIN": "DOMAIN ADD Revenue MIN 0 NULLABLE false",
            "DUPLICATES": "DUPLICATES SUMMARY",
            "EDIT": "EDIT ROW 1 CHANGES '{\"Revenue\": 10}'",
            "EXPLAIN": "EXPLAIN MAX_ROWS 5",
            "EXPORT": 'EXPORT CURRENT TO "current.csv" OVERWRITE',
            "FEATURE": (
                "FEATURE CREATE Margin METHOD difference "
                "COLUMNS Revenue,Cost"
            ),
            "FEATURES": "FEATURES",
            "GALLERY": "GALLERY LIST TYPE bar STAGE current",
            "HEAD": "HEAD 5",
            "HELP": "HELP MODEL",
            "HISTORY": "HISTORY LIMIT 5",
            "INTERPRET": "INTERPRET",
            "KNOWLEDGE": "KNOWLEDGE",
            "LET": "LET CleanSnapshot = CLEANED",
            "LIST": "LIST DATASETS",
            "LOAD": "LOAD",
            "MERGE": (
                "MERGE SalesData WITH CustomerData AS Combined "
                "ON Customer_ID"
            ),
            "MISSING": "MISSING FILL Revenue STRATEGY median",
            "MODEL": "MODEL TARGET Revenue USING decision_tree_regressor",
            "OUTLIERS": "OUTLIERS REVIEW COLUMNS Revenue IQR 1.5",
            "PREDICT": "PREDICT CONFIDENCE 0.9 UNCERTAINTY true",
            "PREVIEW": "PREVIEW",
            "PROFILE": "PROFILE",
            "READINESS": "READINESS",
            "RECOMMEND": "RECOMMEND",
            "REJECT": 'REJECT 1 REASON "Domain decision"',
            "REPORT": 'REPORT TO "report.html" STYLE executive OVERWRITE',
            "REVIEW": "REVIEW",
            "SAMPLE": "SAMPLE 5 RANDOM_STATE 7",
            "SELECT": "SELECT Revenue FROM CURRENT LIMIT 1",
            "SESSION": "SESSION EVENTS LIMIT 5",
            "SET": "SET TYPE Revenue float DECIMALS 2",
            "SHAP": "SHAP CHART beeswarm",
            "STATISTICS": "STATISTICS",
            "TAIL": "TAIL 5",
            "USE": "USE DATASET CustomerData",
            "VALIDATE": "VALIDATE",
            "VISUALIZE": "VISUALIZE bar X Region Y Revenue",
            "WORKSPACE": "WORKSPACE INFO",
        }

        self.assertSetEqual(set(examples), SUPPORTED_COMMANDS)

        parser = ADQLParser()
        for command, source in sorted(examples.items()):
            mixed = re.sub(
                rf"^{command}",
                self._mixed_case(command),
                source,
                count=1,
                flags=re.IGNORECASE,
            )
            with self.subTest(command=command, source=mixed):
                statement = parser.parse(mixed).statements[0]
                self.assertEqual(statement.kind, command)

    def test_language_words_ignore_case_but_user_values_retain_spelling(self):
        source = """
        aDd DaTaSeT CustomerData FrOm "CustomerData.csv" oVeRwRiTe No;
        pRoFiLe DaTaSeT CustomerData;
        vIsUaLiZe DaTaSeT CustomerData BaR X Region Y Gross_Sales
            ThEmE DaRk TiTlE "Revenue CASE" dIsPlAy OfF;
        mOdEl DaTaSeT CustomerData TaRgEt Gross_Sales
            uSiNg DeCiSiOn_TrEe_ReGrEsSoR uSe_EnGiNeErEd No;
        sHaP DaTaSeT CustomerData ChArT BeEsWaRm FeAtUrE Gross_Sales;
        mIsSiNg DaTaSeT CustomerData FiLl Gross_Sales StRaTeGy MeDiAn;
        dUpLiCaTeS DaTaSeT CustomerData DrOp KeEp FiRsT;
        sEt DaTaSeT CustomerData TyPe Gross_Sales FlOaT dEcImAlS 2;
        rEpOrT DaTaSeT CustomerData To "ExecutiveReport.HTML"
            StYlE ExEcUtIvE OvErWrItE YeS;
        sElEcT Region, SuM(Gross_Sales) As TotalRevenue
        fRoM CustomerData GrOuP bY Region OrDeR bY TotalRevenue DeSc;
        """
        script = ADQLParser().parse(source)

        ADQLValidator().validate(script)
        add, profile, chart, model, shap, missing, duplicates, set_type, report, query = (
            statement.parameters for statement in script.statements
        )
        self.assertEqual(add["name"], "CustomerData")
        self.assertEqual(add["dataset_path"], "CustomerData.csv")
        self.assertFalse(add["overwrite"])
        self.assertEqual(profile["dataset_name"], "CustomerData")
        self.assertEqual(chart["dataset_name"], "CustomerData")
        self.assertEqual(chart["chart"], "bar")
        self.assertEqual(chart["x"], "Region")
        self.assertEqual(chart["y"], "Gross_Sales")
        self.assertEqual(chart["title"], "Revenue CASE")
        self.assertFalse(chart["display"])
        self.assertEqual(model["algorithm"], "decision_tree_regressor")
        self.assertEqual(model["target"], "Gross_Sales")
        self.assertEqual(shap["chart"], "beeswarm")
        self.assertEqual(shap["feature"], "Gross_Sales")
        self.assertEqual(missing["strategy"], "median")
        self.assertEqual(duplicates["keep"], "first")
        self.assertEqual(set_type["column"], "Gross_Sales")
        self.assertEqual(set_type["dtype"], "float")
        self.assertEqual(report["output"], "ExecutiveReport.HTML")
        self.assertEqual(report["style"], "executive")
        self.assertTrue(report["overwrite"])
        self.assertEqual(query["source"], "CustomerData")
        self.assertEqual(query["select"][1]["column"], "Gross_Sales")
        self.assertEqual(query["select"][1]["alias"], "TotalRevenue")

    def test_help_inventory_covers_every_public_command(self):
        documented = {
            command.strip()
            for item in COMMAND_HELP
            for command in item["command"].split("/")
        }

        self.assertSetEqual(documented, SUPPORTED_COMMANDS)

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
        ASSERT DATASET customers ROW_COUNT > 0;
        ASSERT DATASET customers SUITE ADD release_gate Customer_ID UNIQUE;
        ASSERT DATASET customers SUITE RUN release_gate FAIL_ON error;
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
        self.assertEqual(script.statement_count, 15)

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
        with self.assertRaisesRegex(ADQLSyntaxError, r"ADQL 2\.1"):
            ADQLParser().parse(
                "SELECT * FROM CURRENT WHERE Region = North OR Region = South;"
            )


if __name__ == "__main__":
    unittest.main()
