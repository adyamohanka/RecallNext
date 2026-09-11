# RecallNext planner

This package is a pure, deterministic evidence planner. It has no database or
LLM dependency: adapters supply the finite complete set of feasible allocation
scenarios produced from Exasol candidate data.

## Contract

`classify_shipments(lots, shipments, candidate_allocations, recalled_lot_ids, assumptions)` returns JSON-serializable shipment decisions with the fixed RecallNext statuses.

`candidate_allocations` must contain complete feasible scenarios. Every row has
`shipment_id`, `lot_id`, and non-negative integer `quantity_cases`. If the
candidate universe is incomplete, a solver does not return `SUCCESS`, or there
are no feasible scenarios, every affected shipment is `UNRESOLVED`.

## Run tests

```bash
python3 -m pytest
```

The exhaustive oracle is deliberately limited to tiny cases and exists only to
validate production bounds. It must not supply hidden ground truth to the
planner.

## Lot identity and adapters

Pass `lot_id` as a source-qualified stable identifier, for example
`SUPPLIER-A:LOT-42`. The planner deliberately treats `SUPPLIER-A:LOT-42` and
`SUPPLIER-B:LOT-42` as distinct lots. Sakthi's Exasol adapter should construct
that identity from `LOT_SOURCE_ID` and `LOT_CODE` before creating scenarios.

## Benchmark baselines

`baseline_action_orders` produces the documented comparison policies: retain
all plausible inventory, deterministic random order, cheapest-first, highest
directly involved quantity first, and RecallNext's conservative ranking. It
only returns reproducible orders; a fixture runner must measure actions,
minutes, holds, coverage, and false exclusions from real simulated outcomes.

The shared API-ready fixture is `tests/fixtures/planner_demo.json`. It is
synthetic and intentionally contains no hidden ground truth.

`evaluate_decision_trace` is test/evaluation-only. It accepts explicitly
provided synthetic ground truth to report false exclusions, resolved cases,
unnecessary holds, action count, simulated minutes, and evaluation time. Never
pass its ground truth input to `classify_shipments` or `rank_actions`.

## Handoff to Harini

For the API adapter, call `classify_shipments` with Exasol's complete feasible
candidate scenarios and send its list output directly as `decisions`. Call
`rank_actions` with those current decisions plus complete outcome decision
scenarios. Both outputs are JSON serializable. The planner itself does not
connect to Exasol and must not accept or verify human evidence; Harini's API
creates a new incident version only after a human accepts it, then triggers
deterministic reassessment.
