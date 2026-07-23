# Releasing AutoDQ

This document describes the repeatable release process for the `autodq`
Python distribution. Building a release does not publish it automatically.

## 1. Prepare the release

Start from the repository root with a clean Git working tree.

1. Update `src/autodq/_version.py` with the intended PEP 440 version.
2. Update user-facing documentation and the changelog or release notes.
3. Confirm that `src/autodq/vscode/extension/package.json` and
   `src/autodq/vscode/__init__.py` use the intended VS Code extension version.
   The Python package and VS Code extension have independent version numbers.
4. Confirm ownership of the `autodq` project name on PyPI before the first
   upload.

## 2. Create an isolated release environment

```bash
python -m venv .release-venv
source .release-venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

On Windows PowerShell:

```powershell
python -m venv .release-venv
.release-venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## 3. Run the acceptance suite

```bash
python -m unittest discover -s tests
autodq --version
autodq validate examples/sales_analysis.adql
```

All tests and commands must complete successfully before building artifacts.

## 4. Build and inspect the distributions

Remove artifacts from any previous release, then build both the source archive
and wheel:

```bash
rm -rf build dist
python -m build
python -m twine check dist/*
python scripts/check_distribution.py dist
```

The distribution checker verifies:

- package name, version, Python requirement, and runtime dependencies;
- the `autodq` console entry point;
- the bundled ADQL grammar, VS Code manifest, and light/dark icons;
- the license, README, release guide, tests, and examples in the source archive;
- the absence of caches and bytecode, plus wheel-only metadata rules.

## 5. Test the wheel in a clean environment

```bash
python -m venv .build-venv
source .build-venv/bin/activate
python -m pip install --upgrade pip
python -m pip install dist/autodq-*.whl

python -c "import autodq; print(autodq.__version__)"
autodq --version
autodq cells examples/sales_analysis.adql
autodq vscode path
python -m pip check
```

Run a small ADQL workflow from a temporary directory as a final smoke test.
Do not rely on the source checkout being importable during this check.

## 6. Upload to TestPyPI

Configure a TestPyPI API token, then run:

```bash
python -m twine upload --repository testpypi dist/*
```

Install the candidate in another clean environment. The extra index allows
runtime dependencies to resolve from the main Python Package Index:

```bash
python -m pip install \
  --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  autodq==VERSION
```

Repeat the import, CLI, ADQL, and `pip check` smoke tests.

## 7. Publish the release

Publishing is irreversible for a given name and version. Only upload after the
TestPyPI candidate has passed.

```bash
python -m twine upload dist/*
git tag -a vVERSION -m "AutoDQ VERSION"
git push origin vVERSION
```

Create release notes from the tested commit and attach the wheel and source
archive if the hosting platform supports release assets.
