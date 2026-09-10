# Synthetic Exasol fixture

The committed CSV files describe one fictional apple-distribution incident.
They contain three source-qualified lots, three containers, and six shipments.
Two container-to-lot mappings and two pick-record identifiers are deliberately
missing. `FARM-A:REC-2026-01` is recalled; `FARM-B:REC-2026-01` deliberately
reuses the lot code under another source and must not be treated as recalled.

This is synthetic test data, not a real recall or operational safety record.
There is no hidden true allocation in these files. Feasible histories must be
derived from accepted facts and constraints.

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
fixture and no user-owned incident data shares its identifiers.
