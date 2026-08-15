import unittest
from pathlib import Path
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
        self.assertIn("No BLUE prescriptions are available.", markup)

    def test_exporter_avoids_multiline_fallbacks_inside_fstrings(self):
        source = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "autodq"
            / "reporting"
            / "html_exporter.py"
        ).read_text(encoding="utf-8")

        self.assertNotIn('or """', source)


if __name__ == "__main__":
    unittest.main()
