# Final live measurement

Measured 13 September 2026 against Exasol Personal with encrypted,
certificate-pinned PyExasol transport. The public recall context is official
openFDA record `H-1259-2026`; the private warehouse fixture is synthetic.

| Path | Runs | Median | p95 |
|---|---:|---:|---:|
| Exasol incident snapshot | 5 | 1017.404 ms | 3157.902 ms |
| Exasol candidate edges | 5 | 240.035 ms | 247.363 ms |
| Complete scenario enumeration | 5 | 808.680 ms | 1235.980 ms |
| API incident read after initialization | 5 | 1.080 ms | 5.158 ms |
| API decisions read after initialization | 5 | 0.961 ms | 1.281 ms |
| API evidence ranking after initialization | 5 | 40.228 ms | 41.794 ms |

Application initialization took 3747.735 ms. Proposal creation took 173.241
ms. Acceptance and Exasol persistence took 162.389 ms. A new workflow instance
restored accepted version 2 in 2970.808 ms. Retraction and persistence took
202.501 ms; a second new workflow instance restored retracted version 3 in
4911.399 ms.

Scope: six shipments, fourteen candidate edges and 125 complete feasible
scenarios. These are small-fixture measurements over an SSH tunnel, not a
warehouse-scale throughput claim. The exact raw result is in `live-final.json`.
