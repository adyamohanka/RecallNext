# Architecture

RecallNext separates relational candidate generation from bounded allocation reasoning. Exasol stores traceability records, runs quality checks and produces possible lot-to-shipment edges. Python accepts only a small component, enumerates complete integer allocations under conservation constraints and calculates shipment bounds across the complete result.

```text
CSV / warehouse events
        |
        v
Exasol schema and source-coverage gates
        |
        v
V_CANDIDATE_ALLOCATION (possible edges, not histories)
        |
        v
bounded scenario generator --limit/conflict--> UNRESOLVED
        |
        v
shipment min/max recalled cases
        |
        v
action outcome simulation and ranking
        |
        v
FastAPI ---- React investigation UI
        |
        v
proposed evidence --human acceptance--> new incident version and diff
```

The integrated demo adapter reconstructs the same candidate semantics from the committed CSVs and labels that source in every incident and health response. Connecting the API runtime to Exasol is the next adapter step after live schema validation; the API must not claim that connection before it exists.

The scenario generator deliberately returns no scenarios if its search bound is exceeded. Classification independently validates shipment totals, known lot limits and closed-inventory conservation before allowing an exclusion.
