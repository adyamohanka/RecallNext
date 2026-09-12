# Live Exasol Personal verification

RecallNext's Exasol boundary was verified on 12 September 2026 and repeated on
13 September 2026 against a real, containerized Exasol Personal starter-kit
deployment. The latest run exercised exact integrated functional head
`64e4c51f1f7683ab3ca9cab401662a75b04bf236`; it was not an offline simulation.
The first live run at `fcf2a83ee6d77c0cb47b6a7f1e16fcff4fc834bc`
and the prior integration run at
`8c83f836c06325b74bb40f827ac257dbce81e23f` remain useful as revision-scoped
compatibility records.

## Environment

- Exasol image: `docker.io/exasol/nano:2026.2.0-nano.3-amd64`
- Exasol starter-kit status during verification: `running`, runtime `nano`, kit
  level `1`
- Client: PyExasol `2.4.0` on Python `3.12.11`
- Host: Ubuntu 22.04 on AWS EC2
- Network boundary: Exasol port `8563` bound only to `127.0.0.1`
- Transport: encryption enabled with the server's SHA-256 certificate
  fingerprint pinned in the DSN; `/nocertcheck` was not used

No database password, AWS credential, or reusable connection secret is stored
in this repository. The DSN below is sanitized only by replacing the
runtime-specific certificate fingerprint.

## Verification gates

| Gate | Result | Revision |
|---|---:|---|
| Ubuntu test suite | 102 passed | `64e4c51` |
| Ruff lint | passed | `64e4c51` |
| Deterministic fixture check | passed | `64e4c51` |
| Fixture replacement and load | passed | `64e4c51` |
| Fixture shipment rows | 6 | `64e4c51` |
| Candidate edges | 14 | `64e4c51` |
| Blocking data-quality issues | 0 | `64e4c51` |
| Candidate universe complete | true | `64e4c51` |
| Recalled-product mismatch probe | expected blocker returned, then removed | `64e4c51` |
| Missing-container probe | expected blocker returned, then removed | `64e4c51` |
| Canonical-completeness upgrade probe | rejected before mutation | `64e4c51` |
| Non-candidate scenario membership probe | rejected before mutation | `64e4c51` |
| Complete optional-source probe | remained complete, then removed | `8c83f83` |
| Duplicate-identity safety probe | expected blocker returned, then removed | `8c83f83` |

## Loader output

```text
Loaded synthetic fixture into RECALLNEXT: INCIDENT=1, LOT=3,
INCIDENT_RECALLED_LOT=1, CONTAINER=3, SHIPMENT=6,
SHIPMENT_CONTAINER=6, EVENT=12, REQUIRED_SOURCE_SYSTEM=3,
SOURCE_COVERAGE=3, EVIDENCE_ACTION=4, ACTION_SHIPMENT=7
```

## Read-only smoke output

```json
{
  "database": {
    "dsn": "127.0.0.1/<pinned-sha256-certificate-fingerprint>:8563",
    "user": "sys",
    "password": "<redacted>",
    "schema": "RECALLNEXT",
    "encryption": true,
    "compression": true,
    "query_timeout_seconds": 30
  },
  "incident_id": "INC-DEMO-001",
  "incident_version": 1,
  "candidate_universe": {
    "candidate_universe_complete": true,
    "blocking_issue_count": 0
  },
  "data_quality_issues": [],
  "shipment_count": 6,
  "candidate_edge_count": 14,
  "timing_ms": {
    "snapshot": 164.668,
    "candidate_edges": 79.505
  }
}
Smoke check passed against real Exasol.
```

These timings are a single smoke run over the committed synthetic fixture and
must not be presented as a general Exasol performance benchmark.

## Final PR #2 safety probes

Four probes exercised the review fixes on the real database at `64e4c51`:

1. Attaching the temporary existing lot `LIVE-PROBE:OTHER-PRODUCT` to the
   incident returned `RECALLED_LOT_PRODUCT_MISMATCH` and made the canonical
   universe incomplete.
2. A balanced temporary shipment mapping to
   `LIVE-MISSING-CONTAINER-PROBE` produced no candidate edges for that shipment
   and returned `UNKNOWN_SHIPMENT_CONTAINER_REFERENCE`.
3. Scenario persistence rejected a caller attempt to upgrade the canonically
   incomplete universe before deleting or inserting any scenario row.
4. After cleanup, scenario persistence rejected an unknown shipment/lot pair
   because it was absent from `V_CANDIDATE_ALLOCATION`.

The exact temporary lot, incident-lot link, shipment, and shipment-container
rows were removed. The post-cleanup read returned 6 shipments, 14 candidate
edges, zero blockers, and `candidate_universe_complete: true`.

## Live duplicate-identity safety probe

A temporary lot row with the exact ID `LIVE-DQ-PROBE-EXACT-HEAD` reused
`FARM-A:REC-2026-01` with a different `LOT_ID`. The real Exasol view returned
the expected blocker:

```text
ISSUE_CODE,ENTITY_ID
DUPLICATE_LOT_SOURCE_CODE,FARM-A:REC-2026-01
```

The probe deleted only its exact row. A post-cleanup smoke run again returned 6
shipments, 14 candidate edges, zero blockers, and a complete candidate
universe.

## Live optional-source coverage probe

A temporary, non-required source named `OPTIONAL_AUDIT_FEED` was inserted with
complete coverage. The real Exasol completeness query remained true with zero
blocking issues. The probe then removed that exact row. This matches the SQL
contract: every required source must be complete, while an additional complete
source must not make the required universe incomplete.

## Compatibility findings fixed during the live run

1. Exasol rejected a `UNIQUE` table constraint. RecallNext now detects duplicate
   `LOT_SOURCE_ID:LOT_CODE` identities through a blocking data-quality rule.
2. PyExasol prepared statements require JSON-serializable values. The loader now
   validates timestamps as `datetime` values and converts them to ISO strings at
   the wire boundary.
3. The starter-kit certificate is self-signed. RecallNext uses fingerprint
   pinning and explicitly rejects PyExasol's `/nocertcheck` bypass.
4. Transport encryption is mandatory; `EXASOL_ENCRYPTION=false` is rejected.
5. Cross-entity product and container-reference defects now block completeness.
6. Persisted successful scenarios must agree with canonical Exasol
   completeness and candidate membership.

The web application still identifies its runtime source as `SYNTHETIC_FIXTURE`.
This live boundary verification does not claim that the FastAPI request path is
already connected to Exasol.
