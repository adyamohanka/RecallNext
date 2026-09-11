# Evaluation

## Reproducible fixture

- Incident: `INC-DEMO-001`
- Product: synthetic apples
- Lots: three source-qualified lots, 30 cases total
- Containers: three, including two unknown/unverified lot mappings
- Shipments: six, five cases each
- Recalled lot: `FARM-A:REC-2026-01`, 12 cases
- Initial complete feasible scenarios: 125
- Initial decisions: four possible inclusions and two exclusions under assumptions

## Required measurements

Record actual values after the commands run. Do not substitute offline Python results for Exasol timing.

| Measurement | Status |
|---|---|
| Fixture generator consistency | Implemented; run in release verification |
| Python/API tests | Implemented; run in release verification |
| Frontend production build | Implemented; run in release verification |
| Exasol schema compilation and load | Pending team deployment |
| Exasol candidate count | Expected 14; pending live smoke output |
| Exasol query timings | Pending live smoke output |
| Random, cheapest and quantity-first strategy metrics | Baseline orders exist; full sequential experiment pending |

Report false exclusions, affected-case coverage, unresolved cases, unnecessary held cases, actions, simulated minutes and replay agreement. Use the same visible facts and evidence budget for every strategy. Keep database, solver and end-to-end timings separate.
