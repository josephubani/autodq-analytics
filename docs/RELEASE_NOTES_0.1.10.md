# AutoDQ 0.1.10 Release Notes

AutoDQ 0.1.10 turns the ADQL `REVIEW` output into an interactive cleaning
workspace inside Visual Studio Code while preserving the existing command,
Python, terminal, Jupyter, and static HTML workflows. It also publishes the
formal ADQL 2.0 language specification and machine-readable grammar.

## Interactive ADQL cleaning review

Run the existing review workflow:

```adql
RECOMMEND;
DECIDE;
PREVIEW;
REVIEW;
```

With AutoDQ ADQL extension 0.3.3, the `REVIEW` result now provides:

- checkboxes for individual cleaning actions;
- **Approve selected**, **Reject selected**, and **Preview selected**;
- an optional rejection reason captured by the audit trail;
- **Approve all** and **Apply to CLEANED**;
- manual row editing with JSON column/value changes and an audit reason;
- live pending, approved, rejected, row, domain, outlier, and audit counts;
- the 25 most recent audit events; and
- the equivalent ADQL statement for every UI operation.

The interface calls the same `AutoDQ` project APIs as the language commands.
Actions remain staged in memory, and **Apply to CLEANED** does not overwrite
the source dataset. Use `EXPORT CLEANED ...` or `LET name = CLEANED` afterward
when a durable or reusable result is required.

## Saved notebook behavior

Interactive review output remains part of the existing `.adql` output cache.
After a notebook is saved, closed, and reopened, selecting a review control
automatically rebuilds the persistent AutoDQ session through that `REVIEW`
cell before applying the requested operation.

## Compatibility and safety

The interactive output is opt-in through a versioned notebook MIME protocol.
Older VSIX versions, the terminal CLI, Jupyter, and Python continue to receive
the previous static `CleaningReview.to_html()` representation. UI messages are
restricted to an allowlist of review operations, validated again by Python,
and routed through public project methods so existing validation and auditing
remain active.

## Formal ADQL 2.0 specification

The release includes the normative language specification, EBNF grammar,
execution model, data-type rules, error model, compatibility policy, and
conformance tests. See `docs/adql/SPECIFICATION.md` and
`docs/adql/grammar.ebnf` in the repository.

## Release components

- AutoDQ Python package: `0.1.10`
- AutoDQ ADQL VS Code extension: `0.3.3`

Upgrade the Python package with:

```bash
python -m pip install --upgrade autodq==0.1.10
```

Install `autodq-adql-0.3.3.vsix` through **Extensions: Install from VSIX...**
to update manually installed VS Code support.
