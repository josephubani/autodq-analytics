import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import pandas as pd

from autodq import (
    ADQLCellParser,
    ADQLFileRunner,
    ADQLValidationError,
    AutoDQ,
)
from autodq.cli import main
from autodq.vscode import extension_path, install_extension


class ADQLStandaloneFileTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.data = pd.DataFrame(
            {
                "Region": ["North", "South", "North", "West"],
                "Revenue": [100.0, 150.0, 75.0, 200.0],
                "Units": [2, 3, 1, 4],
            }
        )
        self.dataset = self.root / "sales.csv"
        self.data.to_csv(self.dataset, index=False)
        self.script = self.root / "analysis.adql"
        self.script.write_text(
            """#!/usr/bin/env autodq
# %% [Dataset]
DATASET "sales.csv" TARGET Revenue;
# %% [Profile]
PROFILE;
# %% [Regional totals]
SELECT Region, SUM(Revenue) AS total_revenue
FROM CURRENT
GROUP BY Region
ORDER BY total_revenue DESC;
""",
            encoding="utf-8",
        )

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_cell_parser_reads_shebang_and_named_cells(self):
        document = ADQLCellParser().read(self.script)

        self.assertEqual(document.cell_count, 3)
        self.assertEqual(
            [cell.title for cell in document.cells],
            ["Dataset", "Profile", "Regional totals"],
        )
        self.assertIn("DATASET", document.cell(1).source)
        self.assertIn("SELECT", document.cell(3).source)

    def test_standalone_file_runs_all_cells_relative_to_its_location(self):
        result = ADQLFileRunner().run(self.script)

        self.assertTrue(result.success)
        self.assertEqual(result.completed_cell_count, 3)
        self.assertEqual(result.project.target, "Revenue")
        self.assertEqual(result.data.iloc[0]["Region"], "West")
        self.assertEqual(result.source_name, str(self.script.resolve()))

    def test_cell_only_and_through_cell_modes(self):
        runner = ADQLFileRunner()
        selected = runner.run(self.script, cell=3)
        cumulative = runner.run(self.script, through_cell=2)

        self.assertTrue(selected.success)
        self.assertEqual(len(selected.cell_runs), 1)
        self.assertEqual(selected.cell_runs[0].cell.number, 3)
        self.assertEqual(len(selected.data), 3)
        self.assertTrue(cumulative.success)
        self.assertEqual(len(cumulative.cell_runs), 2)
        self.assertIsNotNone(cumulative.project.state.profile_report)

    def test_project_run_adql_preserves_existing_project_and_cells(self):
        project = AutoDQ(str(self.dataset), target="Revenue")
        result = project.run_adql(
            self.script,
            through_cell=3,
            auto_display=False,
        )

        self.assertIs(result.project, project)
        self.assertEqual(len(result.cell_runs), 3)
        self.assertEqual(len(result.data), 3)

    def test_standalone_validation_requires_dataset_declaration_or_override(self):
        no_dataset = self.root / "no-dataset.adql"
        no_dataset.write_text("HEAD 2;", encoding="utf-8")
        runner = ADQLFileRunner()

        with self.assertRaisesRegex(ADQLValidationError, "DATASET"):
            runner.validate(no_dataset)

        document = runner.validate(no_dataset, dataset=self.dataset)
        self.assertEqual(document.cell_count, 1)

    def test_cli_runs_shorthand_lists_cells_and_writes_json(self):
        output = self.root / "result.json"
        stdout = io.StringIO()
        stderr = io.StringIO()

        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = main(
                [str(self.script), "--through-cell", "3", "--json", str(output)]
            )
            cells_code = main(["cells", str(self.script)])
            validate_code = main(["validate", str(self.script)])

        self.assertEqual(exit_code, 0, stderr.getvalue())
        self.assertEqual(cells_code, 0)
        self.assertEqual(validate_code, 0)
        self.assertIn("ADQL completed", stdout.getvalue())
        self.assertIn("Regional totals", stdout.getvalue())
        payload = json.loads(output.read_text(encoding="utf-8"))
        self.assertTrue(payload["success"])
        self.assertEqual(payload["cell_count"], 3)

    def test_vscode_extension_is_bundled_and_installable(self):
        source = extension_path()
        package = json.loads(
            (source / "package.json").read_text(encoding="utf-8")
        )
        extension = (source / "extension.js").read_text(encoding="utf-8")
        destination = self.root / "vscode-extension"
        installed = install_extension(destination)

        self.assertEqual(package["contributes"]["languages"][0]["id"], "adql")
        self.assertEqual(
            package["contributes"]["notebooks"][0]["type"],
            "autodq-adql-notebook",
        )
        self.assertIn("ADQLNotebookSerializer", extension)
        self.assertIn("--through-cell", extension)
        self.assertTrue((installed / "package.json").is_file())


if __name__ == "__main__":
    unittest.main()
