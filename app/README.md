# AutoDQ Studio

AutoDQ Studio is the Streamlit interface for the AutoDQ Python API and ADQL.

## Run locally

```bash
cd "/Users/admin/Desktop/Auto DQ/autodq-analytics"
python -m pip install -r requirements-web.txt
AUTODQ_AUTH_MODE=development python -m streamlit run app/streamlit_app.py
```

On Windows PowerShell:

```powershell
$env:AUTODQ_AUTH_MODE = "development"
python -m streamlit run app/streamlit_app.py
```

The development identity is intentionally opt-in and should only be used on a
trusted local machine. Production deployments default to required OIDC login.
AutoDQ Studio uses Streamlit's native authentication flow, so AutoDQ does not
store user passwords.

## Configure production sign-in

1. Create a regular web application in Auth0 or another OIDC provider.
2. Register `http://localhost:8501/oauth2callback` as the local callback URL.
3. Copy `.streamlit/secrets.example.toml` to `.streamlit/secrets.toml` and add
   the provider values. The copied file is ignored by Git.
4. Select the named provider and start the app:

```bash
AUTODQ_AUTH_PROVIDER=auth0 python -m streamlit run app/streamlit_app.py
```

On Windows PowerShell, set `$env:AUTODQ_AUTH_PROVIDER = "auth0"` before the
Streamlit command.

For a hosted deployment, replace the callback URL with the public HTTPS app
URL followed by `/oauth2callback`, then add the same secret values through the
hosting platform's secrets manager.

The v1 workflow supports CSV and Excel uploads, profiling and diagnosis,
evidence-backed cleaning review, missing-value and duplicate treatments,
before/after validation, AutoDQ visualizations, ADQL execution, and CSV/Excel
downloads.
