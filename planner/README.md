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
