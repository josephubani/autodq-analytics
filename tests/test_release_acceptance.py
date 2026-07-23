import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class PublicReleaseAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.dataset = self.root / "acceptance.csv"
        self.workflow = self.root / "acceptance.adql"
        self.output = self.root / "result.json"
        self._write_dataset()
        self._write_workflow()

    def tearDown(self):
        self.temporary_directory.cleanup()

    def _write_dataset(self):
        with self.dataset.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(["Order_ID", "Units", "Price", "Region", "Revenue"])

            for index in range(48):
                units = 1 + index % 12
                price = 10 + (index % 9) * 3.5
                region = ("North", "South", "East")[index % 3]
                revenue = round(units * price, 2)
                writer.writerow([index + 1, units, price, region, revenue])

            writer.writerow([49, "", 24, "", 240])

    def _write_workflow(self):
        self.workflow.write_text(
            "# %% [Dataset]\n"
            "DATASET \"acceptance.csv\" TARGET Revenue;\n"
            "# %% [Automatic review]\n"
            "AUTO MODE review VISUALIZE false CONTINUE_ON_ERROR false;\n"
            "# %% [Summary]\n"
            "SELECT Region, SUM(Revenue) AS total_revenue, COUNT(*) AS rows\n"
            "FROM CURRENT WHERE Region IS NOT NULL GROUP BY Region\n"
            "ORDER BY total_revenue DESC;\n",
            encoding="utf-8",
        )

    def _run_module(self, *arguments):
        return subprocess.run(
            [sys.executable, "-m", "autodq", *arguments],
            cwd=self.root,
            check=True,
            capture_output=True,
            text=True,
        )

    def test_python_api_runs_outside_the_source_tree(self):
        code = (
            "import sys; from autodq import AutoDQ; "
            "project = AutoDQ(sys.argv[1], target='Revenue'); "
            "profile = project.profile(); diagnosis = project.diagnose(); "
            "assert profile['rows'] == 49; "
            "assert diagnosis.quality_score < 100; "
            "result = project.auto(mode='review', visualize=False, "
            "auto_display=False); assert result.success; print('api-ok')"
        )
        completed = subprocess.run(
            [sys.executable, "-c", code, str(self.dataset)],
            cwd=self.root,
            check=True,
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.stdout.strip(), "api-ok")

    def test_adql_auto_runs_outside_the_source_tree(self):
        validation = self._run_module("validate", str(self.workflow))
        completed = self._run_module(
            "run",
            str(self.workflow),
            "--json",
            str(self.output),
        )
        payload = json.loads(self.output.read_text(encoding="utf-8"))

        self.assertIn("valid", validation.stdout.lower())
        self.assertIn("ADQL completed", completed.stdout)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["completed_cell_count"], 3)
        self.assertEqual(payload["failed_cell_count"], 0)

    def test_installed_extension_assets_are_discoverable(self):
        completed = self._run_module("vscode", "path")
        extension = Path(completed.stdout.strip().splitlines()[-1])

        self.assertTrue((extension / "package.json").is_file())
        self.assertTrue((extension / "icons" / "adql-light.svg").is_file())
        self.assertTrue((extension / "icons" / "adql-dark.svg").is_file())
        self.assertTrue(
            (extension / "syntaxes" / "adql.tmLanguage.json").is_file()
        )


if __name__ == "__main__":
    unittest.main()
