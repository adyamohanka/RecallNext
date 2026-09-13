# RecallNext run guide

The clean Adya QA run used macOS 26.5.1 on Apple silicon, Python 3.12.14,
Node.js 24.19.0 and pnpm 11.19.0. Python 3.10+ is supported by project
metadata; the current frontend and CI use Node 24 and pnpm 11.19.0.

## Offline fixture mode

Tested project targets are Python 3.10 or newer, Node.js 24+, and pnpm 11.
Fixture mode uses labelled synthetic CSV data and does not require a database
credential or LLM key.

```bash
git clone https://github.com/harinidev1507/RecallNext.git
cd RecallNext
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m data.generate_fixture --check
python -m pytest -q
export RECALLNEXT_REQUIRE_AUTH=false
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
```

Open another terminal at the repository root:

```bash
pnpm --dir frontend install --frozen-lockfile
pnpm --dir frontend build
pnpm --dir frontend dev --host 127.0.0.1
```

Open <http://127.0.0.1:5173>. The yellow notice and header badge must say that the data source is the synthetic fixture. `GET http://127.0.0.1:8000/api/health` must return `database_connected: false` in this mode.

Stop each development server with `Ctrl-C`.

The repeatable browser test starts its own fixture API and frontend:

```bash
pnpm --dir frontend test:e2e
```

The following read-only calls should succeed while the API is running:

```bash
curl --fail http://127.0.0.1:8000/api/health
curl --fail http://127.0.0.1:8000/api/incidents/INC-DEMO-001
curl --fail http://127.0.0.1:8000/api/incidents/INC-DEMO-001/decisions
curl --fail http://127.0.0.1:8000/api/incidents/INC-DEMO-001/evidence-actions
```

Use the UI for proposal, acceptance, rejection and latest-reviewed-evidence
retraction. The frontend discovers the incident from `GET /api/incidents`; it
does not embed an incident ID, reviewer name, source path or product title.

## Exasol Personal path

The event requires Exasol Personal. On macOS, the current official local starter kit requires Python 3.11+, at least 8 GB RAM and 10 GB free disk. Follow its reviewed install instructions at <https://github.com/exasol-labs/exasol-personal-local-starterkit>.

After installation:

```bash
exakit status
exakit info
```

Export the values returned by the deployment owner. RecallNext reads process
environment variables and does not load `.env` automatically. Never commit the
password. The examples explicitly disable write authentication only for a
loopback development session. Public deployments must keep authentication on.

```bash
export EXASOL_DSN="127.0.0.1/<sha256-certificate-fingerprint>:8563"
export EXASOL_USER="<database-user>"
export EXASOL_PASSWORD="<database-password>"
export EXASOL_SCHEMA="RECALLNEXT"
export EXASOL_ENCRYPTION="true"
python -m data.load_fixture
python -m backend.smoke
```

Import an official food enforcement record. An openFDA API key is optional for
this one-record demo; pass the recall number at runtime.

```bash
python -m data.import_openfda \
  --incident-id "<incident-id>" \
  --recall-number "<openfda-recall-number>"
```

Start the API in fail-closed Exasol mode, then start the frontend using the same
commands as above. Startup fails if the database, incident, public-source table
or contract rows cannot be read.

```bash
export RECALLNEXT_DATA_SOURCE="EXASOL_PERSONAL"
export RECALLNEXT_INCIDENT_ID="<incident-id>"
export RECALLNEXT_REQUIRE_AUTH=false
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
```

With both services running, the live browser check must see a connected Exasol
source and official public recall context:

```bash
export RECALLNEXT_LIVE_BASE_URL="http://127.0.0.1:5173"
pnpm --dir frontend test:e2e:live
```

`GET /api/health` must now report `database_connected: true`. Reviewed evidence
and incident versions are stored in `RECALLNEXT.WORKFLOW_STATE` and restored
after an API restart.

Capture a fresh credential-free performance record with:

```bash
python -m data.measure_live \
  --incident-id "<incident-id>" \
  --reviewer "<reviewer-name>" \
  --runs 15 \
  --reset-before \
  --reset-after \
  --output docs/evaluation-results/live-final.json
```

`python -m data.load_fixture --replace-demo` is intentionally restricted to a
demo-only schema. It refuses to delete anything when an incident other than
`INC-DEMO-001` exists. Use a separate schema instead of forcing replacement in
a shared database.

The smoke check expects six shipments, 14 candidate edges, complete source coverage and no blocking quality issues. The sanitized result from the verified deployment is recorded in `docs/live-exasol-verification.md`. Record new measurements only after running them against the named deployment and revision.

The public FDA record supplies recall number, classification, firm, product,
code information, distribution and reason. It does not supply private warehouse
container, pick or shipment records. RecallNext keeps that boundary visible.

The loader uses `connection.execute_sql_script()`, so the project now requires PyExasol 2.2.3 or newer. Do not lower this bound without testing the schema loader.

## Troubleshooting

- `pytest` missing: activate `.venv`, then reinstall `.[dev]`.
- frontend fetch failure: confirm the API listens on port 8000 and Vite on port 5173.
- fixture mismatch: run `python -m data.generate_fixture --check`; regenerate only if the contract change is intentional.
- stale evidence acceptance: refresh the page and submit against the displayed current version.
- `LIMIT_REACHED`: reduce the incident component or raise the bounded limits only after measuring memory/runtime. Never use partial scenarios for an exclusion.
- `INCOMPLETE_CANDIDATE_UNIVERSE`: check that every source in `required_source_system.csv` has one complete row in `source_coverage.csv`.
- a duplicate identifier issue: correct the input snapshot; the adapter deliberately keeps decisions unresolved rather than choosing one duplicate.
- `--replace-demo` reports another incident: use a dedicated demo schema; the
  loader will not risk deleting globally keyed records from a shared schema.
- Exasol certificate failure: use the trust/fingerprint configuration supplied by the deployment owner. Do not disable verification in committed code.
