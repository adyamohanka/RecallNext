# Final live measurement

Measured 13 September 2026 against Exasol Personal with encrypted,
certificate-pinned PyExasol transport. The public recall context is official
openFDA record `H-1259-2026`; the private warehouse fixture is synthetic.

| Path | Runs | Median | p95 |
|---|---:|---:|---:|
| Exasol incident snapshot | 5 | 667.514 ms | 694.854 ms |
| Exasol candidate edges | 5 | 225.356 ms | 234.974 ms |
| Complete scenario enumeration | 5 | 1455.046 ms | 1957.188 ms |
| API incident read after initialization | 5 | 1.792 ms | 5.075 ms |
| API decisions read after initialization | 5 | 1.459 ms | 2.344 ms |
| API evidence ranking after initialization | 5 | 116.672 ms | 141.611 ms |

Application initialization took 3827.759 ms. A second concurrent worker
initialized in 4138.260 ms and its stale write was rejected with HTTP 409.
Proposal creation took 202.972 ms. Acceptance and Exasol persistence took
160.460 ms. A new workflow instance restored accepted version 2 in 3747.842
ms. Retraction and persistence took 254.219 ms; a second new workflow instance
restored retracted version 3 in 3959.047 ms.

Scope: six shipments, fourteen candidate edges and 125 complete feasible
scenarios. These are small-fixture measurements over an SSH tunnel, not a
warehouse-scale throughput claim. The exact raw result is in `live-final.json`.
