# Architecture

RecallNext separates relational candidate generation from bounded allocation reasoning. Exasol stores traceability records, runs quality checks and produces possible lot-to-shipment edges. Python accepts only a small component, enumerates complete integer allocations under conservation constraints and calculates shipment bounds across the complete result.

```text
Official openFDA recall     Private warehouse events
          |                            |
          +-------------+--------------+
                        |
                        v
Exasol source context, schema and source-coverage gates
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
accepted evidence --human retraction--> rebuild from active evidence
        |
        v
Exasol WORKFLOW_STATE --restart--> restored review history and version
```

The offline adapter reconstructs the candidate semantics from committed CSVs and
labels that source in each incident and health response. In
`EXASOL_PERSONAL` mode, the API loads the same contract from live database rows,
persists review state in Exasol, and fails during startup if that database path
is unavailable. Persisted writes compare the exact previously loaded state, so
concurrent stale workers fail and resynchronize instead of losing evidence. The
API never silently falls back to fixture mode.

The scenario generator deliberately returns no scenarios if its search bound is exceeded. Classification independently validates shipment totals, known lot limits and closed-inventory conservation before allowing an exclusion.

The CSV adapter reads the required-source and source-coverage records before it
calls the generator. Missing or incomplete coverage and duplicate primary
inventory identifiers make the candidate universe incomplete. Decision
persistence separately rejects status/bounds/solver/completeness combinations
that disagree.
