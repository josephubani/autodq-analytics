# Releasing AutoDQ

This document describes the repeatable release process for the `autodq`
Python distribution. Building a release does not publish it automatically.

## 1. Prepare the release

Start from the repository root with a clean Git working tree.

1. Update `src/autodq/_version.py` with the intended PEP 440 version.
2. Move the relevant changelog entries from `Unreleased` into the intended
   version and update or add release notes.
3. Confirm that `src/autodq/vscode/extension/package.json` and
   `src/autodq/vscode/__init__.py` use the intended VS Code extension version.
   The Python package and VS Code extension have independent version numbers.
4. Confirm that the TestPyPI and PyPI Trusted Publisher records still match the
   repository, workflow filenames, and protected environments.

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
autodq validate examples/sales_auto.adql
```

All tests and commands must complete successfully before building artifacts.
The GitHub Actions compatibility job repeats this suite on Python 3.10, 3.11,
3.12, and 3.13 across Linux, macOS, and Windows.

## 4. Build and inspect the distributions

Remove artifacts from any previous release, then build both the source archive
and wheel:

```bash
rm -rf build dist
python -m build
python -m twine check dist/*
python scripts/check_distribution.py dist
python scripts/smoke_test_wheel.py dist
```

The distribution checker verifies:

- package name, version, Python requirement, and runtime dependencies;
- the `autodq` console entry point;
- the bundled ADQL grammar, VS Code manifest, and light/dark icons;
- the license, README, release guide, tests, and examples in the source archive;
- the absence of caches and bytecode, plus wheel-only metadata rules.

The isolated smoke test creates a new virtual environment outside the source
tree, installs the wheel and its declared dependencies, and verifies:

- both `autodq` and `python -m autodq` entry points;
- Python API profiling, diagnosis, and `project.auto(mode="review")`;
- standalone ADQL validation, `AUTO`, querying, and JSON export;
- dependency integrity with `pip check`;
- the bundled VS Code extension manifest, grammar, and icons.

## 5. Publish the ADQL VSIX

The VS Code extension has an independent version. Open GitHub Actions, run
**Publish VS Code Extension**, enter the exact version from
`src/autodq/vscode/extension/package.json`, and keep GitHub Release creation
enabled. Keep Marketplace publication disabled when distributing manually.

The workflow tests and packages the extension, creates a SHA-256 checksum, and
attaches both files to an `adql-vVERSION` GitHub Release. No Microsoft account
or repository secret is required. Install the downloaded package with:

```bash
code --install-extension autodq-adql-VERSION.vsix --force
```

See `docs/VSCODE_MARKETPLACE.md` for direct download URLs, Windows steps, and
the optional Marketplace path.

## 6. Test the wheel in a clean environment

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

`scripts/smoke_test_wheel.py` performs this check automatically and must pass
before upload. Do not rely on the source checkout being importable during a
release smoke test.

## 7. Upload to TestPyPI

### Recommended: GitHub Trusted Publishing

The repository includes `.github/workflows/publish-testpypi.yml`. It builds,
tests, inspects, and publishes the distributions without storing an API token.

The configured TestPyPI Trusted Publisher uses these exact values:

- PyPI project name: `autodq`
- GitHub owner: `josephubani`
- Repository: `autodq-analytics`
- Workflow: `publish-testpypi.yml`
- Environment: `testpypi`

Run **Publish to TestPyPI** from the repository's Actions tab and enter the
exact package version. The workflow rejects version mismatches, runs the full
suite and isolated wheel smoke test, and uses short-lived OIDC credentials
without a GitHub secret.

### Manual fallback: TestPyPI API token

Create the first TestPyPI token with entire-account scope because the project
does not exist there yet. Keep the token outside the repository and run:

```bash
python -m twine upload --repository testpypi dist/*
```

Use `__token__` as the username and paste the complete token, including its
`pypi-` prefix, when prompted. After the first upload, replace the
account-scoped token with a project-scoped token if manual publishing is still
needed. Never commit `.pypirc`, `.pypi-token`, or `.env` credentials.

Install the candidate in another clean environment. The extra index allows
runtime dependencies to resolve from the main Python Package Index:

```bash
python -m pip install \
  --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  autodq==VERSION
```

Repeat the import, CLI, ADQL, and `pip check` smoke tests.

## 8. Publish the release

Publishing is irreversible for a given name and version. Only upload after the
TestPyPI candidate has passed.

### Recommended: GitHub Trusted Publishing

The repository includes `.github/workflows/publish-pypi.yml`. Its production
PyPI Trusted Publisher uses:

- PyPI project name: `autodq`
- GitHub owner: `josephubani`
- Repository: `autodq-analytics`
- Workflow: `publish-pypi.yml`
- Environment: `pypi`

Create a protected GitHub environment named `pypi` and require a reviewer for
deployment. Run **Publish to PyPI** from the Actions tab and enter the exact
version from `src/autodq/_version.py`. The workflow rejects a mismatched
version, reruns every acceptance check including an isolated wheel install,
and publishes using short-lived OIDC credentials. After publication succeeds,
the workflow creates the `vVERSION` Git tag and GitHub release and attaches the
verified wheel and source archive.

### Manual recovery

Use this only when Trusted Publishing is unavailable and the release owner has
deliberately chosen token-based publication:

```bash
python -m twine upload dist/*
git tag -a vVERSION -m "AutoDQ VERSION"
git push origin vVERSION
```

Create release notes from the tested commit and attach the wheel and source
archive if the hosting platform supports release assets.

## 8. Verify the public release

PyPI versions cannot be replaced. Verify the exact public artifact in a new
environment immediately after publication:

```bash
python -m venv .public-release-check
source .public-release-check/bin/activate
python -m pip install --upgrade pip
python -m pip install --index-url https://pypi.org/simple/ autodq==VERSION
python -m pip check
autodq --version
autodq vscode path
```

Run `examples/sales_auto.adql` or an equivalent standalone workflow against the
installed distribution. Confirm the release page, files, hashes, project links,
Python requirement, and release notes on PyPI and GitHub.

If the GitHub release step fails after PyPI publication, do not rerun the PyPI
upload for the same version. Create the missing tag and GitHub release from the
same tested commit and attach the already verified artifacts.

Finally, add a new `Unreleased` changelog section for subsequent development.
