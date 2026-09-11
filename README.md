# RecallNext

RecallNext is an Exasol-powered prototype for food-recall investigations with incomplete lot-to-shipment records. It preserves every feasible allocation for a bounded incident, calculates recalled-case bounds, and ranks which obtainable record could resolve the most uncertainty for the effort required.

AI-assisted extraction may propose a structured fact. A human must accept it before deterministic reassessment creates a new incident version. The application never authorizes a physical stock release.

## What works

- deterministic generation of 125 feasible histories for the committed six-shipment fixture;
- four conservative decision states: `CONFIRMED_INCLUSION`, `POSSIBLE_INCLUSION`, `EXCLUDED_UNDER_ASSUMPTIONS`, and `UNRESOLVED`;
- outcome-aware evidence ranking, including unavailable outcomes and explicitly conditional benefits;
- FastAPI endpoints for incident scope, decisions, evidence actions, proposal, acceptance, rejection and decision differences;
- React investigation UI with text-and-colour statuses, source review and version changes;
- Exasol schema, candidate-generation SQL, fixture loader, persistence services and a smoke check;
- adversarial checks for invalid scenario coverage, conflicts, stale reviews, source-qualified lot identity and bounded computation.

The integrated web application currently starts in `SYNTHETIC_FIXTURE` mode and says so in the health response and UI. Its planner and evidence workflow are real; its data comes directly from the committed CSV fixture. The Exasol loader and smoke path are implemented separately, but still require validation against the team’s Exasol Personal instance. Do not describe the web API as Exasol-backed until that live check passes and the API repository adapter is connected.

## Demo flow

1. Open incident `INC-DEMO-001`. Four shipments are possible inclusions; two are excluded under assumptions because their homogeneous container is source-qualified to another supplier.
2. Compare label, pick-log, retained-case scan and dispatch-manifest actions. Failed retrieval is included, so guaranteed benefit can be zero; valid-outcome benefits are labelled conditional.
3. Select an action and review the synthetic proposed fact. Saving it does not alter decisions.
4. Enter a reviewer name and accept it. The API checks the expected incident version, filters feasible histories and creates a decision diff.
5. Submit an impossible source-qualified allocation to see a conflict create an `UNRESOLVED` version rather than a false exclusion.

## Quick start

Prerequisites: Python 3.10+, Node.js 24+, and pnpm 11. From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m uvicorn backend.app:app --reload
```

In a second terminal:

```bash
cd frontend
pnpm install --frozen-lockfile
pnpm dev
```

Open <http://127.0.0.1:5173>. Run `python -m pytest -q` and `pnpm build` before committing.

See [docs/run-guide.md](docs/run-guide.md) for Exasol setup, smoke checks and troubleshooting. The API payloads are documented in [docs/api-contract.md](docs/api-contract.md).

## Architecture

```text
warehouse fixture / Exasol candidate views
                 │
       completeness and quality gates
                 │
 bounded complete-scenario enumerator
                 │
 recalled quantity bounds per shipment
                 │
 evidence outcome simulation and ranking
                 │
 proposed fact → human acceptance → new version → decision diff
```

Exasol is responsible for relational validation, candidate generation, aggregation and result storage. The Python component operates only on a bounded incident component. It aborts without partial output when its configured combination or scenario limit is exceeded.

## Safety boundaries

- Unknown coverage, invalid scenarios, conflicts and computation limits return `UNRESOLVED`.
- Empty feasible sets are conflicts, never proof of zero exposure.
- Lot identity combines lot source and lot code.
- A single case scan does not establish the contents of an unverified mixed container.
- Saving unreviewed evidence never changes a decision.
- Every acceptance uses an expected incident version to prevent a stale review.
- “Excluded under assumptions” is specific to this synthetic recall model. It does not mean safe to consume.

The fixture is synthetic and describes fictional warehouse records. This project is a hackathon decision-support prototype, not regulatory advice, food-safety certification or a production warehouse integration.

## Project layout

- `backend/` — API, request models, Exasol services and workflow orchestration
- `planner/` — scenario enumeration, bounds, ranking, models and independent tiny oracle
- `sql/` — Exasol schema, quality views and candidate queries
- `data/` — deterministic generator, CSV fixture and Exasol loader
- `frontend/` — React/TypeScript investigation interface
- `tests/` — unit, API and adversarial workflow tests
- `docs/` — run guide, API, architecture, evaluation and safety notes

## Team

- Sakthi — Exasol core and data services
- Bhavyasha — allocation and evidence planner
- Harini — API, UI, integration and release
- Adya — QA, documentation and demo

Licensed under the MIT License. Third-party packages retain their own licenses.
