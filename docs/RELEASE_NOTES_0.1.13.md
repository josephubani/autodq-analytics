# AutoDQ 0.1.13 Release Notes

AutoDQ 0.1.13 is a focused ADQL editor-visibility release. It corrects the
syntax scope used by data-quality assertion predicates and bundles the updated
VS Code extension with the Python package.

## Visible assertion predicates

The AutoDQ ADQL VS Code extension now assigns a visible control-keyword scope
to assertion predicates. In common light and dark themes, the predicate in
this statement is now clearly distinguished from dataset identifiers:

```adql
ASSERT Revenue NOT NULL SEVERITY warning;
```

The same correction applies to all assertion predicates:

```adql
ASSERT Revenue BETWEEN 0 AND 1000000;
ASSERT Customer_Id EXISTS;
ASSERT Email MATCHES "^[^@]+@[^@]+$";
```

`NOT NULL`, `BETWEEN`, `EXISTS`, and `MATCHES` remain case-insensitive. This is
only a syntax-presentation correction; assertion parsing and runtime behavior
are unchanged.

## Regression protection

The extension grammar test now requires quality predicates to use the
`keyword.control.quality.adql` TextMate scope. This prevents them from falling
back to generic operator coloring that some VS Code themes render like normal
text.

ADQL remains at language version `2.1` because no syntax or runtime contract
changed.

## Release components

- AutoDQ Python package: `0.1.13`
- ADQL language: `2.1`
- AutoDQ ADQL VS Code extension: `0.3.6`

Upgrade the Python package with:

```bash
python -m pip install --upgrade autodq==0.1.13
```

Install `autodq-adql-0.3.6.vsix` through **Extensions: Install from VSIX...**
to update manually installed Visual Studio Code support. Then run
**Developer: Reload Window**.
