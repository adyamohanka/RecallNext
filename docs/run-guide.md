# RecallNext run guide

## Application demo

Tested project targets are Python 3.10 or newer, Node.js 24+, and pnpm 11. The committed web flow uses labelled synthetic CSV data and does not require a database credential or LLM key.

```bash
git clone https://github.com/harinidev1507/RecallNext.git
cd RecallNext
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m data.generate_fixture --check
python -m pytest -q
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
```

Open another terminal:

```bash
cd RecallNext/frontend
pnpm install --frozen-lockfile
pnpm build
pnpm dev --host 127.0.0.1
```

Open <http://127.0.0.1:5173>. The yellow notice and header badge must say that the data source is the synthetic fixture. `GET http://127.0.0.1:8000/api/health` must return `database_connected: false` in this mode.

Stop each development server with `Ctrl-C`.

## Exasol Personal path

The event requires Exasol Personal. On macOS, the current official local starter kit requires Python 3.11+, at least 8 GB RAM and 10 GB free disk. Follow its reviewed install instructions at <https://github.com/exasol-labs/exasol-personal-local-starterkit>.

After installation:

```bash
exakit status
exakit info
```

Copy `.env.example` to a local `.env` if your shell tooling loads it, or export the values returned by the deployment. Never commit the password.

```bash
export EXASOL_DSN="127.0.0.1:8563"
export EXASOL_USER="<database-user>"
export EXASOL_PASSWORD="<database-password>"
export EXASOL_SCHEMA="RECALLNEXT"
export EXASOL_ENCRYPTION="true"
python -m data.load_fixture
python -m backend.smoke
```

The smoke check expects six shipments, 14 candidate edges, complete source coverage and no blocking quality issues. Save its raw output and Exasol version in `docs/evaluation.md` only after running it against the actual deployment.

The loader uses `connection.execute_sql_script()`, so the project now requires PyExasol 2.2.3 or newer. Do not lower this bound without testing the schema loader.

## Troubleshooting

- `pytest` missing: activate `.venv`, then reinstall `.[dev]`.
- frontend fetch failure: confirm the API listens on port 8000 and Vite on port 5173.
- fixture mismatch: run `python -m data.generate_fixture --check`; regenerate only if the contract change is intentional.
- stale evidence acceptance: refresh the page and submit against the displayed current version.
- `LIMIT_REACHED`: reduce the incident component or raise the bounded limits only after measuring memory/runtime. Never use partial scenarios for an exclusion.
- Exasol certificate failure: use the trust/fingerprint configuration supplied by the deployment owner. Do not disable verification in committed code.
