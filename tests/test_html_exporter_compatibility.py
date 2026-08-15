import unittest
from types import SimpleNamespace

from autodq.reporting.html_exporter import HTMLExporter


class HTMLExporterCompatibilityTests(unittest.TestCase):
    def test_blue_visual_fallback_renders_without_pep701_fstring_syntax(self):
        blue = SimpleNamespace(
            overall_status="warning",
            assumptions=[],
            vif_results=[],
            features_used=[],
            excluded_features=[],
            recommendations=[],
            warnings=[],
            visual_insights=[],
            prescriptions=[],
            suitability_score=0,
            rows_analyzed=0,
            features_analyzed=0,
        )

        markup = HTMLExporter()._build_blue_section(blue)

        self.assertIn("BLUE Regression Diagnostics", markup)
        self.assertIn("No BLUE visual interpretations are available.", markup)


if __name__ == "__main__":
    unittest.main()
