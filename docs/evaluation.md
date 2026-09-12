# Evaluation record

This record separates completed offline QA from pending live database and
strategy evaluation. The committed operational data is synthetic.

## Revision under test

- Harini integration base: `6450a4189fe1a67be379cd915a29a3c59361c5e8`
- Adya branch: `feat/adya-qa-docs-demo`
- Dependency state: planner PR #1 is merged into canonical `main`; the Exasol
  core and Harini integration remain part of Harini PR #3 at the tested base.

Use the final pull-request head as the exact Adya revision. The raw output file
records the base and commands; no result here is a live Exasol measurement.

## Machine and tools

| Item | Recorded value |
|---|---|
| Date | 12 September 2026 |
| Host | MacBook Air, Apple M5, 16 GB RAM |
| OS | macOS 26.5.1, arm64 |
| Python | 3.12.14 |
| pytest | 8.4.2 |
| PyExasol | 2.4.0 |
| Ruff | 0.16.7 |
| Node.js | 24.19.0 |
| pnpm | 11.19.0 |
| Exasol | Pending team deployment |

## Completed offline checks

Fixture version: deterministic `data.generate_fixture` output and adversarial
matrix `qa-v2`.

| Check | Result | Evidence |
|---|---|---|
| Editable Python install | PASS | `docs/evaluation-results/offline-qa.txt` |
| Python unit, workflow and API tests | PASS — 79 tests | `docs/evaluation-results/offline-qa.txt` |
| Deterministic fixture regeneration | PASS | `docs/evaluation-results/offline-qa.txt` |
| Ruff lint | PASS | `docs/evaluation-results/offline-qa.txt` |
| Ruff format check | PASS — 34 files | `docs/evaluation-results/offline-qa.txt` |
| pnpm frozen-lockfile install | PASS | `docs/evaluation-results/offline-qa.txt` |
| TypeScript and Vite production build | PASS | `docs/evaluation-results/offline-qa.txt` |
| Local visual workflow smoke | PASS | `docs/evaluation-results/offline-qa.txt` |

The test duration and Vite build time are local tool runtimes. They are not
database, solver or end-to-end investigation latency.

## Correctness scope exercised

The offline suite covers:

- all four fixed decision statuses and independently checked tiny bounds;
- a 125-scenario closed synthetic inventory with four possible and two excluded
  shipments;
- exact shipment and lot conservation, invalid edges, empty scenario sets and
  configured enumeration limits, including a closed inventory with a
  zero-quantity lot;
- missing required source coverage and duplicate inventory identifiers;
- source-qualified lot identity when two suppliers reuse one lot code;
- mixed-container single-case evidence that tightens only the observed case and
  cannot clear the remaining cases;
- incompatible accepted label and pick-log evidence producing `CONFLICT` and
  `UNRESOLVED`;
- rejected and unavailable evidence producing no narrowing;
- version conflicts, proposals made stale by another acceptance, current
  pending deduplication, resubmission after rejection or version advance, and
  malformed facts;
- accepted-evidence retraction rebuilding from active evidence and invalidating
  a prior exclusion;
- persistence rejection when status, bounds, solver status and completeness
  metadata disagree;
- fixture replacement refusal before deletion when another incident exists;
- partial action outcomes and conditional-value dominance behavior.

These checks establish behavior only for the declared finite inputs. They do
not certify food safety, prove warehouse-scale performance or validate the SQL
on an Exasol engine.

## Pending live Exasol experiment

The team deployment owner must supply a reachable Exasol Personal endpoint and
sanitized connection guidance. Record:

- deployment type and Exasol version;
- schema/fixture load result;
- shipment, candidate-edge and blocking-issue counts;
- exact SQL revision;
- candidate query time, planner time and end-to-end time separately;
- repetition and cold/warm-run method.

The fixture contract expects six shipments, fourteen candidate edges, complete
coverage and zero blocking issues. These values remain expected until
`python -m data.load_fixture` and `python -m backend.smoke` succeed on the live
deployment. The web API currently reads the committed CSV fixture; it must not
be described as Exasol-backed.

## Pending investigation-strategy experiment

The baseline module produces deterministic action orders. It does not yet run a
sequential experiment that applies evidence, recomputes rankings and scores
each strategy.

| Strategy | Current state |
|---|---|
| Hold all plausible inventory | Ordering implemented; sequential score pending |
| Deterministic random action | Ordering implemented; multi-seed score pending |
| Cheapest evidence first | Ordering implemented; score pending |
| Highest directly involved quantity first | Ordering implemented; score pending |
| RecallNext ranking | One-step ordering implemented; sequential score pending |
| Full-information oracle | Tiny correctness utility only |

A fair run must give every policy the same incidents, visible facts, obtainable
evidence, realized outcomes and budget. Retain per-incident seeds, ties, errors
and simple-baseline wins. Report false exclusions, affected-case coverage,
unnecessary held cases, resolved cases, actions, simulated retrieval minutes,
replay agreement and actual computation time.

## Known unavailable checks

- No local `exasol` or `exakit` command and no team endpoint were available, so
  schema compilation, SQL results and database timing were not run.
- No live document model is connected. Example facts are labelled synthetic;
  no API credits were used.
- The frontend has a production build gate and a recorded manual visual smoke,
  but no repeatable browser automation suite.
- Retraction is available through the API and covered by tests; the current UI
  has no retraction control.
- Evidence and incident versions are stored in process memory and reset when
  the API restarts.

## Reporting rules

Do not present expected counts as live database measurements. Do not claim a
faster investigation until the paired sequential experiment supports it. Keep
retrieval-minute assumptions separate from measured runtime, and never treat
`EXCLUDED_UNDER_ASSUMPTIONS` as safe or released inventory.
