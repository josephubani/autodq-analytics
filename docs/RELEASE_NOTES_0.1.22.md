# AutoDQ 0.1.22 Release Notes

AutoDQ 0.1.22 adds built-in structural email validation to executable data
quality assertions. ADQL authors can now state the intent directly instead of
maintaining a regular expression:

```adql
ASSERT Email FORMAT email;
```

## Email format checks

`FORMAT email` validates every non-null value in the selected column. It
checks practical ASCII mailbox structure, including:

- exactly one `@` separator;
- local-part characters, length, and dot placement;
- a dotted domain with valid label lengths and hyphen placement;
- a conventional alphabetic or punycode top-level domain;
- total address length and the absence of whitespace.

The check is structural. It does not query DNS, send email, or prove that a
mailbox exists. Missing values remain independent so completeness can carry a
different severity:

```adql
ASSERT Email NOT NULL
    SEVERITY error NAME "Email is required";
ASSERT Email FORMAT email
    SEVERITY warning NAME "Email has a valid structure";
```

## Reusable quality suites

The format predicate works in named suites, JSON suite exports, and explicit
named-dataset runs:

```adql
ASSERT SUITE ADD customer_gate Email FORMAT email
    SEVERITY warning NAME "Valid email";
ASSERT DATASET cleaned_customers SUITE RUN customer_gate FAIL_ON warning;
```

The equivalent Python assertion is:

```python
from autodq import QualityAssertion

email_test = QualityAssertion(
    subject="column",
    column="Email",
    predicate="format",
    expected="email",
    severity="warning",
)
report = project.assert_quality(email_test, fail_on="warning")
```

## Compatibility and versions

- AutoDQ Python package: `0.1.22`
- ADQL language: `2.4`
- AutoDQ ADQL VS Code extension: `0.3.15`
- Quality-suite JSON format: unchanged at `1`

Every valid ADQL 2.3 workflow remains valid. `MATCHES` remains available for
custom regular expressions, while `FORMAT email` is the clearer built-in form.

Upgrade AutoDQ with:

```bash
python -m pip install --upgrade autodq==0.1.22
```

For manual VS Code installation, download `autodq-adql-0.3.15.vsix` from the
matching GitHub release and install it with **Extensions: Install from VSIX**.
