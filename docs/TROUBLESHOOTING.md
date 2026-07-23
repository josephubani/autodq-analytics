# AutoDQ Troubleshooting

## `autodq: command not found`

Activate the environment where AutoDQ was installed:

```bash
source .venv/bin/activate
python -m pip install autodq
autodq --version
```

On Windows PowerShell, use `.venv\Scripts\Activate.ps1`. You can always invoke
the same command through the active interpreter:

```bash
python -m autodq --version
```

## A notebook still uses old method arguments

Jupyter retains imported Python modules in its kernel. After upgrading or
editing AutoDQ, restart the kernel and import the project again. Confirm which
package is loaded with:

```python
import autodq
print(autodq.__version__)
print(autodq.__file__)
```

Current visualization customization names include `title`, `subtitle`,
`x_label`, `y_label`, `theme`, `palette`, `figsize`, `dpi`, `grid`, and
`legend`.

## ADQL prints a chart message instead of showing a chart

Terminal execution is intentionally text-oriented. For rich tables,
collapsible output, and inline charts, install the bundled VS Code extension:

```bash
autodq vscode install
```

Restart VS Code, reopen the `.adql` file with the ADQL notebook editor, and use
**Run Cell** or **Run through Cell**. Use **ADQL: Restart Session** if state from
an earlier run should be discarded.

## The first command appears slow

Scientific plotting and modeling libraries can build caches on their first
import. Matplotlib may also build its font cache. Let the first run complete;
later runs should be faster. Ensure your user cache directory is writable if
the cache is rebuilt every time.

## Large ADQL output is truncated

The VS Code notebook deliberately previews large results. Expand the output
section to show or hide its preview. The complete structured result remains in
the ADQL session and is available to later statements and exports. Prefer
`SELECT ... LIMIT ...` for focused tabular output.

## Trusted Publishing reports `invalid-publisher`

TestPyPI and production PyPI are separate services with separate accounts and
publisher records. Configure the production publisher on `pypi.org`, not
`test.pypi.org`, and match all claims exactly:

- owner: `josephubani`
- repository: `autodq-analytics`
- workflow filename: `publish-pypi.yml`
- environment: `pypi`

The workflow field is the filename only, not `.github/workflows/publish-pypi.yml`.

## A saved model cannot be loaded safely

AutoDQ model bundles use joblib/pickle internally. Load model bundles only from
sources you trust. Never treat an untrusted model file as passive data.

## Confirm the installed release

For a clean installation check:

```bash
python -m venv autodq-check
source autodq-check/bin/activate
python -m pip install autodq
python -m pip check
autodq --version
autodq vscode path
```

If a problem persists, open an issue with the AutoDQ version, Python version,
operating system, command used, and the complete error message.
