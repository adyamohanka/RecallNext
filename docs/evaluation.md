# Evaluation record

## Sequential planner benchmark

Run `python -m planner.benchmark_cli` to regenerate the committed raw JSON and Markdown summary in `docs/evaluation-results/`. The benchmark uses two hidden synthetic scenarios, budgets of 4 and 11 simulated minutes, and fixed seeds 11, 17, 23, 29 and 31. It evaluates all five declared strategies. Each action reveals only its target shipment rows and filters candidates consistent with that observation; it never substitutes a hidden full scenario. Runs choose only affordable actions, so an over-budget preferred action cannot prevent another affordable action. Generated artifacts intentionally omit wall-clock timings and are byte-reproducible. `plan_incident(...)["planner_seconds"]` separately measures classification time only; no live Exasol or AWS timing is included.

This record separates four verification scopes: Adya's historical offline QA
run, local checks on the merged application, completed live Exasol runs, and
the committed synthetic investigation-strategy evaluation. The public recall
context is an official openFDA enforcement record. The private warehouse,
container, lot-allocation and shipment records remain explicitly synthetic.

## Revisions under test

- Harini integration base: `6450a4189fe1a67be379cd915a29a3c59361c5e8`
- Historical Adya branch: `feat/adya-qa-docs-demo`
- Current merged benchmark revision (PR #11): `91f7046`

The raw offline output records Adya's original base and commands. It is
historical evidence for that run, not a live Exasol measurement and not a claim
that every later integration commit ran on the same Mac.

## Historical offline QA machine and tools

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
| Exasol | Not run on this Mac; see the separate AWS live record below |

## Historical completed offline checks

Fixture version: deterministic `data.generate_fixture` output and adversarial
matrix `qa-v2`.

| Check | Result | Evidence |
|---|---|---|
| Editable Python install | PASS | `docs/evaluation-results/offline-qa.txt` |
| Python unit, workflow and API tests | PASS - 79 tests | `docs/evaluation-results/offline-qa.txt` |
| Deterministic fixture regeneration | PASS | `docs/evaluation-results/offline-qa.txt` |
| Ruff lint | PASS | `docs/evaluation-results/offline-qa.txt` |
| Ruff format check | PASS - 34 files | `docs/evaluation-results/offline-qa.txt` |
| pnpm frozen-lockfile install | PASS | `docs/evaluation-results/offline-qa.txt` |
| TypeScript and Vite production build | PASS | `docs/evaluation-results/offline-qa.txt` |
| Local visual workflow smoke | PASS | `docs/evaluation-results/offline-qa.txt` |

The test duration and Vite build time are local tool runtimes. They are not
database, solver, or end-to-end investigation latency.

## Current PR #2 synchronization checks

The current `main` branch was merged into `sakthi/exasol-core` before applying
the remaining Exasol safety fixes. The following checks ran on 13 September
2026 in Windows with Python 3.11 and pnpm 11.19.0:

| Check | Result |
|---|---|
| Python tests | PASS - 102 tests, one dependency deprecation warning |
| Ruff lint | PASS |
| Ruff format check on Python files changed from `main` | PASS - 7 files |
| Deterministic fixture regeneration | PASS |
| pnpm frozen-lockfile install | PASS |
| TypeScript and Vite production build | PASS |

The full repository format check also reports seven inherited planner files in
current `main` that Ruff would reformat. PR #2 does not modify those files, so
they were not mechanically reformatted in this Exasol-only change.

## Final application branch checks

The final integration branch was checked on 13 September 2026 after the
cross-worker persistence fixes:

| Check | Result |
|---|---|
| Python tests | PASS - 112 tests, two dependency deprecation warnings |
| Ruff lint | PASS |
| Changed Python file format check | PASS |
| Deterministic fixture regeneration | PASS |
| Frontend component tests | PASS - 8 tests |
| TypeScript and Vite production build | PASS |
| Edge proposal, acceptance and retraction workflow | PASS - 1 browser test |
| Edge live Exasol source check | PASS - 1 browser test |
| Secret-pattern and ASCII punctuation checks | PASS |

## Correctness scope exercised

The combined suite covers:

- all four fixed decision statuses and independently checked tiny bounds;
- a 125-scenario closed synthetic inventory with four possible and two excluded
  shipments;
- exact shipment and lot conservation, invalid edges, empty scenario sets, and
  configured enumeration limits, including a zero-quantity lot;
- missing required source coverage, optional complete coverage, and duplicate
  inventory identifiers;
- recalled-lot product mismatch and a shipment mapping that references a
  missing container;
- source-qualified lot identity when two suppliers reuse one lot code;
- mixed-container single-case evidence that tightens only the observed case;
- incompatible accepted evidence producing `CONFLICT` and `UNRESOLVED`;
- rejected and unavailable evidence producing no narrowing;
- stale proposals, current pending deduplication, and resubmission rules;
- stale cross-worker Exasol writes and worker resynchronization;
- retraction rebuilding from all remaining active accepted or conflicting
  evidence;
- persistence rejection when status, bounds, solver status, and completeness
  metadata disagree;
- fixture replacement refusal before deletion when another incident exists;
- timestamp serialization at the PyExasol wire boundary; and
- rejection of certificate bypass and disabled transport encryption.

These checks establish behavior only for the declared finite inputs. They do
not certify food safety or prove warehouse-scale performance.

## Live Exasol verification status

The Exasol boundary was run successfully on 12 September 2026 against a real,
containerized Exasol Personal starter-kit deployment on AWS EC2. The first run
verified revision `fcf2a83ee6d77c0cb47b6a7f1e16fcff4fc834bc`.

The same load, smoke, and safety checks were repeated on 13 September 2026 at
integrated functional head `8c83f836c06325b74bb40f827ac257dbce81e23f`,
then again at the current PR #2 functional head
`64e4c51f1f7683ab3ca9cab401662a75b04bf236`. The latest run established:

- Exasol image `docker.io/exasol/nano:2026.2.0-nano.3-amd64`;
- successful schema and synthetic-fixture loading;
- six shipments and fourteen candidate edges;
- zero blocking data-quality issues;
- `candidate_universe_complete: true`;
- encrypted PyExasol transport with a pinned certificate fingerprint;
- recalled-lot product mismatch and missing-container blockers;
- rejection of a caller attempt to upgrade canonical completeness; and
- rejection of a scenario shipment/lot pair outside the candidate view.

The latest smoke run measured 164.668 ms for the snapshot query and 79.505
ms for the candidate-edge query. These are single-run database timings over the
small synthetic fixture, not a performance benchmark. All exact probe rows were
removed and the clean post-probe read returned the original counts. The earlier
`8c83f83` run separately verified optional complete coverage and duplicate
source-qualified lot detection.

The credential-free execution record is in
`docs/live-exasol-verification.md`. The documentation-only commit that records
this result does not change the tested SQL, loader, configuration, or service
code.

## Final Exasol-backed application measurement

On 13 September 2026, the visible FastAPI workflow was run with
`RECALLNEXT_DATA_SOURCE=EXASOL_PERSONAL` against the encrypted,
certificate-pinned Exasol Personal deployment. The database contained the
six-shipment synthetic warehouse fixture and official openFDA recall context
`H-1259-2026`. The raw result is in
`docs/evaluation-results/live-final.json`.

| Measured path | Runs | Median | p95 |
|---|---:|---:|---:|
| Exasol incident snapshot | 5 | 667.514 ms | 694.854 ms |
| Exasol candidate edges | 5 | 225.356 ms | 234.974 ms |
| Complete scenario enumeration | 5 | 1455.046 ms | 1957.188 ms |
| API incident read after initialization | 5 | 1.792 ms | 5.075 ms |
| API decision read after initialization | 5 | 1.459 ms | 2.344 ms |
| API evidence ranking after initialization | 5 | 116.672 ms | 141.611 ms |

Application initialization took 3827.759 ms. A second concurrent worker
initialized in 4138.260 ms, and its stale write was rejected with HTTP 409. A
proposal took 202.972 ms, human acceptance plus Exasol persistence took 160.460
ms, and a fresh workflow reconstruction restored version 2 in 3747.842 ms.
Retraction plus persistence took 254.219 ms, and a second reconstruction
restored retracted version 3 in 3959.047 ms.

These are five-run measurements of one small bounded fixture over an SSH
tunnel, not warehouse-scale throughput claims. API read timings exclude
startup. The measurement reset the exact incident state after completion so
the demo starts at version 1.

## Sequential investigation-strategy experiment

The benchmark applies action-scoped synthetic evidence, recomputes rankings,
and scores every strategy under equal scenarios, budgets, and seeds. Raw runs
and the aggregate summary are committed in `docs/evaluation-results/`.

| Strategy | Current state |
|---|---|
| Hold all plausible inventory | Sequential score recorded |
| Deterministic random action | Multi-seed sequential score recorded |
| Cheapest evidence first | Sequential score recorded |
| Highest directly involved quantity first | Sequential score recorded |
| RecallNext ranking | Sequential score recorded |
| Full-information oracle | Tiny correctness utility only |

A fair run must give every policy the same incidents, visible facts, obtainable
evidence, realized outcomes, and budget. Retain per-incident seeds, ties,
errors, and simple-baseline wins. Report false exclusions, affected-case
coverage, unnecessary held cases, resolved cases, actions, simulated retrieval
minutes, and replay agreement. Machine-dependent computation timings are
reported separately rather than committed in deterministic benchmark artifacts.

## Known unavailable integrations

- No live document model is connected. Example facts are labelled synthetic;
  no API credits were used and no rule-based parser is presented as an LLM.
- The frontend has eight component tests, a production build gate, a repeatable
  full browser workflow test, and a separate live Exasol browser-source check.
- The visible UI includes retraction. In Exasol-backed mode, reviewed evidence,
  versions and retractions survive API workflow reconstruction and restart.
- No production ERP or WMS connector is included. The warehouse side is a
  deterministic synthetic fixture because public recall data does not expose a
  distributor's private pick, container and shipment records.

## Reporting rules

Do not present fixture expectations as live database measurements. Do not claim
a faster investigation until the paired sequential experiment supports it.
Keep retrieval-minute assumptions separate from measured runtime, and never
treat `EXCLUDED_UNDER_ASSUMPTIONS` as safe or released inventory.
