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

## Database, projects, and personal workspace

The first successful sign-in registers the user and creates a personal
workspace. Local development uses an ignored SQLite database at
`.autodq-studio/studio.db` by default, so the account and workspace survive
application restarts.

Each workspace can contain multiple named projects and datasets. Studio keeps
the original uploaded file and automatically versions the latest current,
cleaned, and engineered data as typed Parquet snapshots. The local object
store defaults to `.autodq-studio/objects`.

To place dataset objects on a separate persistent volume, set:

```bash
export AUTODQ_OBJECT_STORE_PATH="/persistent/autodq/objects"
```

On Windows PowerShell:

```powershell
$env:AUTODQ_OBJECT_STORE_PATH = "D:\\AutoDQ\\objects"
```

Set `AUTODQ_DATABASE_URL` to use PostgreSQL in a hosted deployment:

```bash
export AUTODQ_DATABASE_URL="postgresql+psycopg://USER:PASSWORD@HOST/DATABASE"
```

On Windows PowerShell:

```powershell
$env:AUTODQ_DATABASE_URL = "postgresql+psycopg://USER:PASSWORD@HOST/DATABASE"
```

AutoDQ applies pending Alembic migrations when Studio starts. Migrations can
also be applied manually from the repository root:

```bash
python -m alembic -c app/alembic.ini upgrade head
```

Do not commit production database URLs. Configure them with the hosting
platform's environment-variable or secrets manager.

The v1.1 workflow supports durable projects, CSV and Excel uploads, profiling and diagnosis,
evidence-backed cleaning review, missing-value and duplicate treatments,
before/after validation, AutoDQ visualizations, ADQL execution, and CSV/Excel
downloads.
