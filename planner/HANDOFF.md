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

Use `planner_input_from_candidate_rows` when the SQL result has the required
columns: `SCENARIO_ID`, `SHIPMENT_ID`, `LOT_SOURCE_ID`, `LOT_CODE`, and
`QUANTITY_CASES`. It groups rows by `SCENARIO_ID` and produces the object above.
Rows without a complete scenario grouping, duplicate rows, or malformed fields
fail closed as an incomplete candidate universe.

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

## Evidence-ranking input

Every evidence action must include `action_id`, `action_type`, `target_id`,
`question`, `estimated_minutes` (positive), and `availability`. Supply a
complete `outcome_scenarios` mapping keyed by `action_id`. Each outcome has an
`outcome` value (`VALID`, `UNAVAILABLE`, `ILLEGIBLE`, `CONFLICTING`, or
`REJECTED`) and a full list of shipment decisions in the same shape returned by
`classify_shipments`. Never omit a credible outcome to improve a rank. A
missing scenario receives a conservative zero worst-case score; unavailable,
illegible, conflicting, rejected, and retracted evidence must not narrow scope.

## Human review and reassessment

1. Store proposed evidence without changing planner inputs.
2. Require a human to accept it.
3. Create a new incident version.
4. Rebuild candidates and outcome scenarios deterministically.
5. Re-run the calls above and display the before/after diff.

Conflicting, rejected, unavailable, illegible, or retracted evidence must not
narrow scope. The test fixture at `tests/fixtures/planner_demo.json` is
synthetic and can be used until Sakthi supplies a real candidate export.
