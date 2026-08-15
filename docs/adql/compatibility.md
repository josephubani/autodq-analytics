# ADQL Language Compatibility Policy

This policy applies to the ADQL language. AutoDQ Python package, VS Code
extension, notebook protocol, and persisted artifact versions are independent.

## 1. Current version

The current language version is **ADQL 2.3**. A conforming AutoDQ installation
exposes it as:

```python
from autodq import ADQL_LANGUAGE_VERSION

assert ADQL_LANGUAGE_VERSION == "2.3"
```

The language version does not equal the AutoDQ package or ADQL VS Code
extension version. Multiple package and extension releases may implement the
same ADQL language version.

## 2. Version form

ADQL language versions use `MAJOR.MINOR`:

- **MAJOR** changes may remove syntax, change existing statement semantics, or
  alter state transitions incompatibly.
- **MINOR** changes add commands, clauses, literals, stages, or semantics while
  retaining valid programs from earlier minor versions of the same major.
- Editorial corrections and implementation bug fixes do not change the
  language version when they restore already specified behavior.

Specification files in source control MAY receive document revisions without
changing the language version when normative meaning is unchanged.

## 3. ADQL 2.x guarantee

Within ADQL 2.x, a program valid under ADQL 2.0 SHOULD continue to parse and
retain its documented state-changing behavior. Compatible additions include:

- new commands and options that do not capture previously valid syntax;
- new optional structured result fields;
- new renderers and output MIME types;
- new non-reserved enum values where accepting them cannot change an existing
  program; and
- increased implementation limits.

Security fixes, corrections to behavior that contradicted this specification,
and fixes for programs whose outcome depended on an implementation defect MAY
change observed behavior without a major language version.

## 4. Changes requiring ADQL 3.0

The following require a new major version unless introduced behind explicit
new syntax that leaves ADQL 2.x programs unchanged:

- changing statement delimiters or comment rules;
- changing `LET` from snapshot to live-reference semantics;
- changing a dataset selector from persistent activation to temporary scope;
- making review mutations modify `CURRENT` directly;
- changing the meaning of an existing built-in stage;
- removing a command, option, literal, or accepted dtype;
- changing `SELECT` clause order or aggregate meaning; or
- silently enabling arbitrary host-language or shell execution.

## 5. Deprecation

When an ADQL feature must be replaced, documentation SHOULD identify:

- the deprecated form;
- the replacement;
- the first language version containing the warning; and
- the earliest major version in which removal may occur.

A deprecation warning MUST NOT make an otherwise successful ADQL 2.x statement
fail. Removal occurs only in a later major version unless necessary to resolve
a security vulnerability.

## 6. Unknown syntax

ADQL is allowlisted. An implementation MUST reject an unknown command, unknown
option, or unsupported command form rather than silently ignoring it. This
prevents a workflow written for a newer runtime from appearing to succeed on
an older runtime while skipping intended operations.

Authors distributing reusable `.adql` files SHOULD document their minimum
required AutoDQ package and ADQL language versions.

## 7. Independent protocol versions

These versions do not change the ADQL language version by themselves:

- AutoDQ package version;
- VS Code extension version;
- `autodq-notebook-v1` transport protocol;
- saved notebook output-cache version;
- model bundle format;
- workspace manifest format; and
- exported report or dashboard schema.

Changing a protocol may require coordinated package and extension releases,
but it requires a new ADQL version only when accepted source syntax or
normative execution semantics also change.

## 8. Conformance declaration

A tool claiming ADQL compatibility SHOULD state both its supported language
version and conformance level:

```text
ADQL 2.3 parser
ADQL 2.3 AutoDQ runtime
ADQL 2.3 notebook host
```

A parser-only tool such as a formatter or syntax highlighter need not execute
project operations. A runtime-conforming tool MUST implement the full command
inventory and state model. A notebook host additionally implements cell and
result transport behavior.
