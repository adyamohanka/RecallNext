# Planner handoff for Harini

The planner is pure Python. It does not access Exasol, accept evidence, or
decide that stock is safe. Harini's API owns human acceptance and versioning.

## Required adapter input

Convert the bounded solver's **complete feasible scenarios** into:

```json
{
  "shipments": [{"shipment_id": "S-100", "quantity_cases": 12}],
  "candidate_allocations": [
    [{"shipment_id": "S-100", "lot_id": "FARM-A:LOT-42", "quantity_cases": 12}]
  ],
  "recalled_lot_ids": ["FARM-A:LOT-42"],
  "assumptions": {
    "candidate_universe_complete": true,
    "solver_status": "SUCCESS"
  }
}
```

`lot_id` must be the stable source-qualified identity
`LOT_SOURCE_ID:LOT_CODE`. Do not pass lot code alone. A missing candidate
universe, conflict, timeout, or malformed/over-capacity allocation produces
`UNRESOLVED` by design.

## Calls

```python
from planner import classify_shipments, rank_actions

decisions = classify_shipments([], shipments, candidate_allocations, recalled_lot_ids, assumptions)
actions = rank_actions(decisions, evidence_actions, outcome_scenarios)
```

Return `decisions` as the `/decisions` response and `actions` as the
`/evidence-actions` response. The objects are JSON serializable.

## Human review and reassessment

1. Store proposed evidence without changing planner inputs.
2. Require a human to accept it.
3. Create a new incident version.
4. Rebuild candidates and outcome scenarios deterministically.
5. Re-run the calls above and display the before/after diff.

Conflicting, rejected, unavailable, illegible, or retracted evidence must not
narrow scope. The test fixture at `tests/fixtures/planner_demo.json` is
synthetic and can be used until Sakthi supplies a real candidate export.
