# RecallNext API contract

Incident identifiers are discovered at runtime. Unknown incidents return 404.

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Runtime and data-source status |
| GET | `/api/incidents` | Discover incidents exposed by the configured data source |
| GET | `/api/incidents/INC-DEMO-001` | Current version, recalled lots and summary |
| GET | `/api/incidents/INC-DEMO-001/decisions` | Current or requested version’s shipment decisions |
| GET | `/api/incidents/INC-DEMO-001/evidence` | Versioned evidence review and retraction log |
| GET | `/api/incidents/INC-DEMO-001/evidence-actions` | Ranked and transparently dominated actions |
| GET | `/api/incidents/INC-DEMO-001/diff?from_version=1&to_version=2` | Versioned decision changes |
| GET | `/api/incidents/INC-DEMO-001/evidence-actions/{action_id}/example-fact` | Synthetic demo proposal for a selected action |
| POST | `/api/incidents/INC-DEMO-001/evidence-actions/{action_id}/extract-document` | Extract a bounded, review-only fact from an uploaded source |
| POST | `/api/incidents/INC-DEMO-001/evidence` | Save a proposal without reassessment |
| POST | `/api/incidents/INC-DEMO-001/evidence/{evidence_id}/accept` | Human acceptance and deterministic reassessment |
| POST | `/api/incidents/INC-DEMO-001/evidence/{evidence_id}/reject` | Human rejection without changing decisions or version |
| POST | `/api/incidents/INC-DEMO-001/evidence/{evidence_id}/retract` | Human retraction, reconstruction from active evidence and a new version |

Authentication defaults to enabled. Without a valid
`RECALLNEXT_ADMIN_TOKEN`, the API refuses to start. When
`RECALLNEXT_REQUIRE_AUTH=true`, every POST route requires
`Authorization: Bearer <reviewer-token>`. The token is supplied at runtime and
is never returned by the API. GET routes remain read-only and public. An
operator must explicitly set `RECALLNEXT_REQUIRE_AUTH=false` to run an
unauthenticated local development server.

Document extraction accepts multipart field `document` with PDF, PNG, JPEG,
WebP, plain text, CSV, or JSON content. It uses the selected action's target,
known lot identifiers, and expected quantities as a strict output boundary.
The Responses API request uses structured JSON output and `store: false`. A
successful response has this form:

```json
{
  "action_id": "ACT-MANIFEST-S200",
  "proposed_fact": {
    "fact_type": "shipment_allocation",
    "shipment_id": "S-200",
    "allocations": {"FARM-A:REC-2026-01": 5}
  },
  "source_reference": "upload://sha256/<sha256>#manifest.csv",
  "content_hash": "<sha256>",
  "extraction_mode": "OPENAI_RESPONSES_API",
  "model": "<runtime-model>",
  "provider_response_id": "<provider-response-id>",
  "requires_human_review": true
}
```

Extraction never creates an evidence record and never changes a decision. The
returned fact passes the same action-specific validator used by proposal
submission. Missing provider configuration returns 503, provider failures
return 502, and incomplete or incompatible source content returns 422.

Evidence proposal:

```json
{
  "action_id": "ACT-MANIFEST-S200",
  "source_reference": "synthetic/manifest-S-200.json",
  "proposed_fact": {
    "fact_type": "shipment_allocation",
    "shipment_id": "S-200",
    "allocations": {"FARM-A:REC-2026-01": 5}
  },
  "content_hash": "<sha256-hex>",
  "review_status": "PENDING_REVIEW"
}
```

Acceptance:

```json
{"verified_by": "Reviewer name", "expected_version": 1}
```

Rejection:

```json
{
  "verified_by": "Reviewer name",
  "expected_version": 1,
  "reason": "Source does not support the proposed fact."
}
```

Retraction uses the same fields as rejection:

```json
{
  "verified_by": "Reviewer name",
  "expected_version": 2,
  "reason": "The source owner withdrew this record."
}
```

A stale `expected_version` returns 409. A proposal is also rejected as stale if
another acceptance advances the incident after it was submitted. Duplicate
content hashes return the existing proposal only when it is pending for the
same action and current incident version. Rejected, retracted and older-version
records do not prevent a new review. If an accepted fact eliminates every
currently feasible scenario, the new version has solver status `CONFLICT` and
every shipment is `UNRESOLVED`.

Only accepted or conflicting evidence can be retracted. The current prototype
requires reverse chronological retraction when several reviewed facts exist.
Retraction rebuilds the scenario set from the original snapshot and every
still-active accepted fact; it does not treat the previous narrowed state as
ground truth. The retraction creates a new incident version and its decision
diff identifies the retracted evidence. In `EXASOL_PERSONAL` mode, evidence,
versions and retractions are persisted in the `WORKFLOW_STATE` table and
restored only when the stored scenario and validation-input fingerprint matches
the current database snapshot. State writes use compare-and-swap semantics, so
a stale API worker receives a 409 instead of overwriting another worker's audit
history. Fixture mode is intentionally process-local.

Before a proposal is stored, the API validates its fact shape, known identifiers, integer quantities, complete allocation totals, and compatibility with the selected evidence action. Invalid or mismatched facts return 422.

After the UI saves a proposal, its selected action, source reference and
structured fact are locked until the reviewer accepts or rejects it. The
displayed proposal therefore stays identical to the stored evidence targeted
by the review request.

The fixed decision statuses are `CONFIRMED_INCLUSION`, `POSSIBLE_INCLUSION`, `EXCLUDED_UNDER_ASSUMPTIONS`, and `UNRESOLVED`. Clients must display text labels in addition to colour.
