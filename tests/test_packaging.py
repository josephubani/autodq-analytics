import json
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
from autodq.vscode import EXTENSION_VERSION


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
        self.assertIn("Documentation", project["urls"])
        self.assertIn("Changelog", project["urls"])
        self.assertIn("Release notes", project["urls"])
        self.assertIn("Programming Language :: Python :: 3.13", project["classifiers"])

    def test_ci_covers_every_supported_python_version(self):
        workflow = (
            ROOT / ".github" / "workflows" / "tests.yml"
        ).read_text(encoding="utf-8")

        for version in ("3.10", "3.11", "3.12", "3.13"):
            self.assertIn(version, workflow)

        self.assertIn("actions/checkout@v6", workflow)
        self.assertIn("actions/setup-python@v6", workflow)
        self.assertIn("python scripts/smoke_test_wheel.py dist", workflow)
        self.assertIn("npx --yes @vscode/vsce@3.9.2 package", workflow)
        self.assertIn("actions/setup-node@v6", workflow)

    def test_testpypi_workflow_uses_trusted_publishing(self):
        workflow = (
            ROOT / ".github" / "workflows" / "publish-testpypi.yml"
        ).read_text(encoding="utf-8")

        self.assertIn("workflow_dispatch", workflow)
        self.assertIn("EXPECTED_VERSION", workflow)
        self.assertIn("id-token: write", workflow)
        self.assertIn("environment:\n      name: testpypi", workflow)
        self.assertIn("https://test.pypi.org/legacy/", workflow)
        self.assertIn("pypa/gh-action-pypi-publish@release/v1", workflow)
        self.assertIn("actions/checkout@v6", workflow)
        self.assertIn("actions/setup-python@v6", workflow)
        self.assertIn("actions/upload-artifact@v7", workflow)
        self.assertIn("actions/download-artifact@v8", workflow)
        self.assertIn("python scripts/smoke_test_wheel.py dist", workflow)
        self.assertNotIn("TWINE_PASSWORD", workflow)
        self.assertNotIn("API_TOKEN", workflow)

    def test_pypi_workflow_has_version_and_approval_gates(self):
        workflow = (
            ROOT / ".github" / "workflows" / "publish-pypi.yml"
        ).read_text(encoding="utf-8")

        self.assertIn("workflow_dispatch", workflow)
        self.assertIn("EXPECTED_VERSION", workflow)
        self.assertIn("environment:\n      name: pypi", workflow)
        self.assertIn("id-token: write", workflow)
        self.assertIn("https://pypi.org/p/autodq", workflow)
        self.assertIn("pypa/gh-action-pypi-publish@release/v1", workflow)
        self.assertIn("actions/checkout@v6", workflow)
        self.assertIn("actions/setup-python@v6", workflow)
        self.assertIn("actions/upload-artifact@v7", workflow)
        self.assertIn("actions/download-artifact@v8", workflow)
        self.assertIn("python scripts/smoke_test_wheel.py dist", workflow)
        self.assertIn("contents: write", workflow)
        self.assertIn("gh release create", workflow)
        self.assertIn("--generate-notes", workflow)
        self.assertNotIn("test.pypi.org", workflow)
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
        self.assertTrue((extension / "CHANGELOG.md").is_file())
        self.assertTrue((extension / "LICENSE").is_file())
        self.assertTrue((extension / "notebook-persistence.js").is_file())

        manifest = json.loads(
            (extension / "package.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["publisher"], "autodq")
        self.assertEqual(manifest["name"], "adql")
        self.assertEqual(manifest["version"], EXTENSION_VERSION)
        self.assertEqual(manifest["license"], "SEE LICENSE IN LICENSE")
        self.assertEqual(
            manifest["repository"]["url"],
            "https://github.com/josephubani/autodq-analytics.git",
        )
        self.assertIn("README.md", manifest["files"])
        self.assertIn("notebook-persistence.js", manifest["files"])
        self.assertFalse(
            manifest["capabilities"]["untrustedWorkspaces"]["supported"]
        )

    def test_vscode_marketplace_workflow_is_version_gated(self):
        workflow = (
            ROOT / ".github" / "workflows" / "publish-vscode.yml"
        ).read_text(encoding="utf-8")

        self.assertIn("workflow_dispatch", workflow)
        self.assertIn("EXPECTED_VERSION", workflow)
        self.assertIn('mkdir -p "${GITHUB_WORKSPACE}/dist"', workflow)
        self.assertIn("@vscode/vsce@${VSCE_VERSION} package", workflow)
        self.assertIn("github_release", workflow)
        self.assertIn("sha256sum", workflow)
        self.assertIn("contents: write", workflow)
        self.assertIn('tag="adql-v${VERSION}"', workflow)
        self.assertIn("gh release create", workflow)
        self.assertIn("gh release upload", workflow)
        self.assertIn("@vscode/vsce@${VSCE_VERSION} publish", workflow)
        self.assertIn("environment:\n      name: vscode-marketplace", workflow)
        self.assertIn("VSCE_PAT: ${{ secrets.VSCE_PAT }}", workflow)
        self.assertIn("actions/checkout@v6", workflow)
        self.assertIn("actions/setup-node@v6", workflow)
        self.assertIn("actions/upload-artifact@v7", workflow)
        self.assertIn("actions/download-artifact@v8", workflow)
        self.assertNotIn("Marketplace (Manage)", workflow)
        self.assertTrue((ROOT / "docs" / "VSCODE_MARKETPLACE.md").is_file())

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

    def test_public_release_documentation_is_current(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        notes = (
            ROOT / "docs" / "RELEASE_NOTES_0.1.0.md"
        ).read_text(encoding="utf-8")
        roadmap = (ROOT / "docs" / "ROADMAP.md").read_text(encoding="utf-8")

        self.assertIn("https://pypi.org/project/autodq/", readme)
        self.assertNotIn("Until the first PyPI release", readme)
        self.assertIn("first complete alpha release.", notes)
        self.assertIn("production PyPI", notes)
        self.assertIn(
            "All items in the original AutoDQ development roadmap are complete.",
            roadmap,
        )
        self.assertTrue((ROOT / "docs" / "QUICKSTART.md").is_file())
        self.assertTrue((ROOT / "docs" / "TROUBLESHOOTING.md").is_file())
        self.assertTrue((ROOT / "scripts" / "smoke_test_wheel.py").is_file())
        self.assertTrue((ROOT / "tests" / "test_release_acceptance.py").is_file())


if __name__ == "__main__":
    unittest.main()
