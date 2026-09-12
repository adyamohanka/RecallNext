# Sequential benchmark

Synthetic deterministic benchmark. Timing fields are local runtime measurements, not warehouse or database timings.

- Truth cases: 2
- Budgets: 4, 11 minutes
- Seeds: 11, 17, 23, 29, 31
- Runs: 100

| Strategy | Runs | Mean resolved cases | Mean simulated minutes | False excluded cases |
|---|---:|---:|---:|---:|
| hold_all_plausible_inventory | 20 | 0.00 | 0.00 | 0 |
| random_action_order | 20 | 10.00 | 4.90 | 0 |
| cheapest_first | 20 | 10.00 | 4.00 | 0 |
| highest_directly_involved_quantity_first | 20 | 10.00 | 4.00 | 0 |
| recallnext_ranking | 20 | 10.00 | 4.00 | 0 |
