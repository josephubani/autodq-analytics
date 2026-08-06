import tempfile
import unittest
from pathlib import Path

import pandas as pd

from autodq import AutoDQ
from autodq.knowledge.engine import KnowledgeEngine
from autodq.knowledge.library import (
    DEFAULT_KNOWLEDGE_ALIASES,
    DEFAULT_KNOWLEDGE_RULES,
)
from autodq.knowledge.rules import KnowledgeRule


def rule_name(engine: KnowledgeEngine, column: str) -> str | None:
    rule = engine.get_rule(column)
    return rule.name if rule else None


class KnowledgeEngineTests(unittest.TestCase):
    def test_default_catalog_has_broad_reusable_coverage(self):
        self.assertGreaterEqual(len(DEFAULT_KNOWLEDGE_RULES), 80)
        self.assertGreaterEqual(
            sum(len(values) for values in DEFAULT_KNOWLEDGE_ALIASES.values()),
            350,
        )

        covered_domains = {
            domain
            for rule in DEFAULT_KNOWLEDGE_RULES.values()
            for domain in rule.metadata.get("domains", [])
        }
        self.assertTrue(
            {
                "banking",
                "education",
                "healthcare",
                "hr",
                "insurance",
                "iot",
                "logistics",
                "marketing",
                "retail",
            }.issubset(covered_domains)
        )

    def test_existing_common_rules_remain_available(self):
        engine = KnowledgeEngine()

        self.assertEqual(rule_name(engine, "age"), "age")
        self.assertEqual(rule_name(engine, "Revenue"), "revenue")
        self.assertEqual(rule_name(engine, "Gross_Profit"), "profit")
        self.assertEqual(rule_name(engine, "Discount_Amount"), "discount")
        self.assertEqual(rule_name(engine, "Quantity"), "quantity")
        self.assertEqual(rule_name(engine, "Order_Date"), "date")
        self.assertEqual(rule_name(engine, "Unit_Price"), "unit_price")
        self.assertEqual(rule_name(engine, "Region"), "region")
        self.assertEqual(rule_name(engine, "Gender"), "gender")
        self.assertEqual(rule_name(engine, "Product"), "product")

    def test_matching_understands_common_column_naming_styles(self):
        engine = KnowledgeEngine()

        self.assertEqual(rule_name(engine, "CustomerAge"), "age")
        self.assertEqual(rule_name(engine, "postal-code"), "postal_code")
        self.assertEqual(rule_name(engine, "Created At"), "date")
        self.assertEqual(rule_name(engine, "GEO.LATITUDE"), "latitude")
        self.assertEqual(rule_name(engine, "conversionRate"), "conversion_rate")
        self.assertEqual(rule_name(engine, "patient_mrn"), "patient_id")

    def test_specific_aliases_win_over_generic_words(self):
        engine = KnowledgeEngine()

        self.assertEqual(rule_name(engine, "unit_price"), "unit_price")
        self.assertEqual(rule_name(engine, "transaction_amount"), "amount")
        self.assertEqual(rule_name(engine, "annual_salary"), "salary")
        self.assertEqual(rule_name(engine, "air_temperature"), "temperature")
        self.assertEqual(rule_name(engine, "order_status"), "status")

    def test_token_matching_avoids_accidental_substring_rules(self):
        engine = KnowledgeEngine()

        self.assertEqual(rule_name(engine, "average_revenue"), "revenue")
        self.assertEqual(rule_name(engine, "mortgage_balance"), "balance")
        self.assertEqual(rule_name(engine, "candidate_status"), "status")
        self.assertIsNone(rule_name(engine, "unknown_blob"))

    def test_rules_cover_representative_dataset_families(self):
        engine = KnowledgeEngine()
        columns = {
            # Retail and finance
            "InvoiceNumber": "order_id",
            "GrossSales": "sales",
            "AvailableBalance": "balance",
            "FICOScore": "credit_score",
            # Healthcare and education
            "PatientNumber": "patient_id",
            "BloodPressureReading": "blood_pressure",
            "GradePointAverage": "gpa",
            "AttendanceRate": "attendance",
            # HR, logistics, IoT, and marketing
            "EmployeeNumber": "employee_id",
            "JobRole": "job_title",
            "ShipmentWeight": "weight",
            "TrackingID": "tracking_number",
            "SensorIdentifier": "sensor_id",
            "RelativeHumidity": "humidity",
            "AdImpressions": "impressions",
            "ClickCount": "clicks",
        }

        self.assertEqual(
            {column: rule_name(engine, column) for column in columns},
            columns,
        )

    def test_custom_rule_api_remains_compatible_and_supports_aliases(self):
        custom = KnowledgeRule(
            name="lot_code",
            semantic_type="manufacturing_identifier",
            metadata={"aliases": ["batch_number"]},
        )
        engine = KnowledgeEngine(rules={"lot_code": custom})

        self.assertIs(engine.get_rule("LotCode"), custom)
        self.assertIs(engine.get_rule("production_batch_number"), custom)
        self.assertIsNone(engine.get_rule("revenue"))

    def test_get_rules_for_columns_preserves_column_mapping(self):
        engine = KnowledgeEngine()
        rules = engine.get_rules_for_columns(
            ["Customer_ID", "Order_Date", "Revenue", "Unmapped_Field"]
        )

        self.assertEqual(
            list(rules),
            ["Customer_ID", "Order_Date", "Revenue", "Unmapped_Field"],
        )
        self.assertEqual(rules["Customer_ID"].name, "customer_id")
        self.assertEqual(rules["Order_Date"].name, "date")
        self.assertEqual(rules["Revenue"].name, "revenue")
        self.assertIsNone(rules["Unmapped_Field"])

    def test_adql_knowledge_uses_the_expanded_catalog(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            dataset = Path(temporary_directory) / "cross_domain.csv"
            pd.DataFrame(
                {
                    "InvoiceNumber": ["INV-1", "INV-2"],
                    "GrossSales": [120.0, 85.0],
                    "PatientNumber": ["P-1", "P-2"],
                    "BloodPressureReading": ["120/80", "118/76"],
                    "SensorIdentifier": ["S-1", "S-2"],
                    "RelativeHumidity": [48.0, 52.0],
                    "AdImpressions": [1000, 800],
                    "ClickCount": [80, 55],
                }
            ).to_csv(dataset, index=False)

            project = AutoDQ(str(dataset))
            run = project.query("KNOWLEDGE;", auto_display=False)

            self.assertTrue(run.success)
            self.assertEqual(
                {
                    column: rule.name
                    for column, rule in project.state.knowledge_rules.items()
                },
                {
                    "InvoiceNumber": "order_id",
                    "GrossSales": "sales",
                    "PatientNumber": "patient_id",
                    "BloodPressureReading": "blood_pressure",
                    "SensorIdentifier": "sensor_id",
                    "RelativeHumidity": "humidity",
                    "AdImpressions": "impressions",
                    "ClickCount": "clicks",
                },
            )


if __name__ == "__main__":
    unittest.main()
