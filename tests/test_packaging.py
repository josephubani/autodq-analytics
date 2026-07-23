import re
import subprocess
import sys
import unittest
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib

import autodq

from autodq._version import __version__


ROOT = Path(__file__).resolve().parents[1]


def dependency_name(requirement: str) -> str:
    match = re.match(r"[A-Za-z0-9][A-Za-z0-9._-]*", requirement)

    if match is None:
        raise ValueError(f"Invalid dependency: {requirement}")

    return re.sub(r"[-_.]+", "-", match.group(0)).lower()


class PackagingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.configuration = tomllib.loads(
            (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        )

    def test_version_is_single_sourced_and_exposed(self):
        project = self.configuration["project"]
        dynamic = self.configuration["tool"]["setuptools"]["dynamic"]

        self.assertNotIn("version", project)
        self.assertIn("version", project["dynamic"])
        self.assertEqual(
            dynamic["version"]["attr"],
            "autodq._version.__version__",
        )
        self.assertEqual(autodq.__version__, __version__)
        self.assertRegex(__version__, r"^\d+\.\d+\.\d+(?:[a-z]+\d+)?$")

    def test_project_metadata_is_release_ready(self):
        project = self.configuration["project"]

        self.assertEqual(project["name"], "autodq")
        self.assertEqual(project["requires-python"], ">=3.10")
        self.assertEqual(project["license"], "MIT")
        self.assertEqual(project["license-files"], ["LICENSE"])
        self.assertEqual(project["readme"], "README.md")
        self.assertIn("Repository", project["urls"])
        self.assertIn("Programming Language :: Python :: 3.13", project["classifiers"])

    def test_ci_covers_every_supported_python_version(self):
        workflow = (
            ROOT / ".github" / "workflows" / "tests.yml"
        ).read_text(encoding="utf-8")

        for version in ("3.10", "3.11", "3.12", "3.13"):
            self.assertIn(version, workflow)

        self.assertIn("actions/checkout@v6", workflow)
        self.assertIn("actions/setup-python@v6", workflow)

    def test_testpypi_workflow_uses_trusted_publishing(self):
        workflow = (
            ROOT / ".github" / "workflows" / "publish-testpypi.yml"
        ).read_text(encoding="utf-8")

        self.assertIn("workflow_dispatch", workflow)
        self.assertIn("id-token: write", workflow)
        self.assertIn("environment:\n      name: testpypi", workflow)
        self.assertIn("https://test.pypi.org/legacy/", workflow)
        self.assertIn("pypa/gh-action-pypi-publish@release/v1", workflow)
        self.assertIn("actions/checkout@v6", workflow)
        self.assertIn("actions/setup-python@v6", workflow)
        self.assertIn("actions/upload-artifact@v7", workflow)
        self.assertIn("actions/download-artifact@v8", workflow)
        self.assertNotIn("TWINE_PASSWORD", workflow)
        self.assertNotIn("API_TOKEN", workflow)

    def test_runtime_dependencies_cover_all_shipped_features(self):
        dependencies = {
            dependency_name(value)
            for value in self.configuration["project"]["dependencies"]
        }
        expected = {
            "joblib",
            "matplotlib",
            "numpy",
            "openpyxl",
            "pandas",
            "scikit-learn",
            "scipy",
            "shap",
            "statsmodels",
            "xlrd",
        }

        self.assertEqual(dependencies, expected)
        self.assertNotIn("streamlit", dependencies)
        self.assertNotIn("pyyaml", dependencies)
        self.assertNotIn("seaborn", dependencies)

    def test_console_entry_point_and_module_report_same_version(self):
        project = self.configuration["project"]
        self.assertEqual(project["scripts"]["autodq"], "autodq.cli:main")

        completed = subprocess.run(
            [sys.executable, "-m", "autodq", "--version"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.stdout.strip(), f"AutoDQ {__version__}")

    def test_vscode_assets_are_declared_as_package_data(self):
        package_data = self.configuration["tool"]["setuptools"]["package-data"]
        patterns = package_data["autodq.vscode"]
        extension = ROOT / "src" / "autodq" / "vscode" / "extension"

        self.assertIn("extension/icons/*", patterns)
        self.assertIn("extension/syntaxes/*", patterns)
        self.assertTrue((extension / "package.json").is_file())
        self.assertTrue((extension / "icons" / "adql-light.svg").is_file())
        self.assertTrue((extension / "icons" / "adql-dark.svg").is_file())

    def test_requirements_files_delegate_to_pyproject(self):
        runtime = (ROOT / "requirements.txt").read_text(encoding="utf-8").strip()
        development = (
            ROOT / "requirements-dev.txt"
        ).read_text(encoding="utf-8").strip()

        self.assertEqual(runtime, "-e .")
        self.assertEqual(development, "-e .[dev]")

    def test_source_manifest_includes_release_material(self):
        manifest = (ROOT / "MANIFEST.in").read_text(encoding="utf-8")

        self.assertIn("recursive-include docs *.md", manifest)
        self.assertIn("recursive-include examples *.adql *.py", manifest)
        self.assertIn("recursive-include .github *.yml", manifest)
        self.assertIn("recursive-include scripts *.py", manifest)
        self.assertIn("recursive-include tests *.py", manifest)


if __name__ == "__main__":
    unittest.main()
