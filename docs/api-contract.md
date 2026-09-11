# RecallNext API contract

All endpoints use incident `INC-DEMO-001` in the current prototype. Unknown incidents return 404.

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Runtime and data-source status |
| GET | `/api/incidents/INC-DEMO-001` | Current version, recalled lots and summary |
| GET | `/api/incidents/INC-DEMO-001/decisions` | Current or requested version’s shipment decisions |
| GET | `/api/incidents/INC-DEMO-001/evidence-actions` | Ranked and transparently dominated actions |
| GET | `/api/incidents/INC-DEMO-001/diff?from_version=1&to_version=2` | Versioned decision changes |
| GET | `/api/incidents/INC-DEMO-001/evidence-actions/{action_id}/example-fact` | Synthetic demo proposal for a selected action |
| POST | `/api/incidents/INC-DEMO-001/evidence` | Save a proposal without reassessment |
| POST | `/api/incidents/INC-DEMO-001/evidence/{evidence_id}/accept` | Human acceptance and deterministic reassessment |
| POST | `/api/incidents/INC-DEMO-001/evidence/{evidence_id}/reject` | Human rejection without changing decisions or version |
| POST | `/api/incidents/INC-DEMO-001/evidence/{evidence_id}/retract` | Human retraction, reconstruction from active evidence and a new version |

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
content hashes return the existing proposal. If an accepted fact eliminates
every currently feasible scenario, the new version has solver status `CONFLICT`
and every shipment is `UNRESOLVED`.

Only accepted or conflicting evidence can be retracted. The current prototype
requires reverse chronological retraction when several reviewed facts exist.
Retraction rebuilds the scenario set from the original snapshot and every
still-active accepted fact; it does not treat the previous narrowed state as
ground truth. The retraction creates a new incident version and its decision
diff identifies the retracted evidence. This prototype keeps versions in
memory, so they reset when the API process restarts.

Before a proposal is stored, the API validates its fact shape, known identifiers, integer quantities, complete allocation totals, and compatibility with the selected evidence action. Invalid or mismatched facts return 422.

The fixed decision statuses are `CONFIRMED_INCLUSION`, `POSSIBLE_INCLUSION`, `EXCLUDED_UNDER_ASSUMPTIONS`, and `UNRESOLVED`. Clients must display text labels in addition to colour.
