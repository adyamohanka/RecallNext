# Live Exasol Personal verification

RecallNext's Exasol boundary was verified on 12 September 2026 and repeated on
13 September 2026 against a real, containerized Exasol Personal starter-kit
deployment. The latest run exercised exact integrated functional head
`8c83f836c06325b74bb40f827ac257dbce81e23f`; it was not an offline simulation.
The first live run at `fcf2a83ee6d77c0cb47b6a7f1e16fcff4fc834bc`
remains useful as the compatibility-fix record.

## Environment

- Exasol image: `docker.io/exasol/nano:2026.2.0-nano.3-amd64`
- Exasol starter-kit status: `running`, runtime `nano`, kit level `1`
- Client: PyExasol `2.4.0` on Python `3.12.11`
- Host: Ubuntu 22.04 on AWS EC2
- Network boundary: Exasol port `8563` bound only to `127.0.0.1`
- Transport: encryption enabled with the server's SHA-256 certificate
  fingerprint pinned in the DSN; `/nocertcheck` was not used

No database password, AWS credential, or reusable connection secret is stored
in this repository. The DSN below is sanitized only by replacing the
runtime-specific certificate fingerprint.

## Verification gates

| Gate | Result |
| --- | ---: |
| Ubuntu test suite at exact functional head | 83 passed |
| Ruff | passed |
| Deterministic fixture check | passed |
| Exact-head fixture replacement and load | passed |
| Fixture shipment rows | 6 |
| Candidate edges | 14 |
| Blocking data-quality issues | 0 |
| Candidate universe complete | true |
| Complete optional-source probe | remained complete, then removed |
| Duplicate-identity safety probe | expected blocker returned, then removed |

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
    "snapshot": 172.794,
    "candidate_edges": 72.719
  }
}
Smoke check passed against real Exasol.
```

These timings are a single smoke run over the committed synthetic fixture and
must not be presented as a general Exasol performance benchmark.

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

The web application still identifies its runtime source as `SYNTHETIC_FIXTURE`.
This live boundary verification does not claim that the FastAPI request path is
already connected to Exasol.
