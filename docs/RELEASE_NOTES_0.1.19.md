# AutoDQ 0.1.19 Release Notes

AutoDQ 0.1.19 removes the fixed 100-statement limit from ADQL. Large
notebook-style workflows can now contain as many parsed statements as needed,
provided the source remains within the separate source-size safeguard.

## Unlimited statement count

Earlier releases rejected an ADQL script when its parsed statement count
exceeded 100. That check has been removed from the validator, so the same
behavior applies in:

- standalone `.adql` files;
- cell-by-cell and **Run All** execution in VS Code;
- `autodq validate` and `autodq run`; and
- Python API execution through `project.query()`.

This release does not weaken the independent safety controls. ADQL still uses
an allowlisted command grammar, explicit mutation commands, bounded query
results, a 10,000-row explicit `LIMIT` maximum, a 50-condition WHERE maximum,
and a 100,000-character source limit.

## Compatibility

No ADQL syntax changed. Existing files continue to run unchanged, while files
with more than 100 statements no longer need to be split solely to satisfy an
arbitrary statement-count cap.

Regression coverage validates a 250-statement script, and the complete Python,
extension, distribution, and clean-wheel acceptance checks are run before
publication.

## Versions

- AutoDQ Python package: `0.1.19`
- ADQL language: `2.3`
- AutoDQ ADQL VS Code extension: `0.3.12`

## Upgrade

```bash
python -m pip install --upgrade autodq==0.1.19
```

For manual VS Code installation, download `autodq-adql-0.3.12.vsix` from the
matching GitHub release and use **Extensions: Install from VSIX...**.
