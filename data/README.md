# Synthetic Exasol fixture

The committed CSV files describe one fictional apple-distribution incident.
They contain three source-qualified lots, three containers, and six shipments.
Two container-to-lot mappings and two pick-record identifiers are deliberately
missing. `FARM-A:REC-2026-01` is recalled; `FARM-B:REC-2026-01` deliberately
reuses the lot code under another source and must not be treated as recalled.
`required_source_system.csv` explicitly lists the three source systems whose
coverage must be declared before candidate generation can be called complete.

This is synthetic test data, not a real recall or operational safety record.
There is no hidden true allocation in these files. Feasible histories must be
derived from accepted facts and constraints.

The independent QA matrix is stored in
`tests/fixtures/adversarial_cases.json`. Every required case records the
expected result and the reason for it, including missing source coverage,
duplicate inventory, mixed-container scanning, contradictions, solver failure,
rejection and retraction.

Verify that the committed data still matches the deterministic generator:

```bash
python -m data.generate_fixture --check
```

Regenerate only when intentionally changing the fixture contract:

```bash
python -m data.generate_fixture
```

Loading requires a real Exasol target in environment variables. The loader
does not provide SQLite or mock fallback behavior:

```bash
python -m data.load_fixture
```

The loader refuses to overwrite an existing `INC-DEMO-001` incident. Pass
`--replace-demo` only when you intentionally want to replace this synthetic
fixture in a schema dedicated to the demo. Replacement aborts before any
deletion when another incident exists because global shipment, container, lot
and event identifiers do not carry ownership metadata.
