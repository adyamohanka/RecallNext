# Six-slide pitch outline

Replace every pending measurement with a cited result before export. Keep full
source links in the speaker notes.

## 1. Missing evidence during a recall

**Message:** A distributor may know the recalled supplier lot while incomplete
container and pick records leave several outgoing shipments plausible.

**Visual:** One source-qualified recalled lot branching through two unknown
container mappings into four uncertain shipments.

**Evidence:** Use the FDA mixed-lot and case-scanning discussion only as problem
context. It is not an endorsement or certification of RecallNext.

## 2. The RecallNext investigation loop

**Message:** Keep every supported allocation, calculate shipment bounds, rank
the obtainable record with the most decision value, require human review, then
create a versioned decision diff.

**Visual:** `uncertain scope → ranked evidence → proposal → human acceptance →
recompute → diff/retraction`.

**Demo fact:** The committed synthetic fixture has six five-case shipments and
125 complete scenarios. Four start as possible inclusions and two are excluded
under assumptions.

## 3. The precise contribution

**Message:** Traceability systems can show records and gaps. RecallNext models
how each obtainable missing fact could change decisions before the operator
retrieves it.

| Capability | Traceability view | RecallNext prototype |
|---|---|---|
| Show movement records | Yes | Yes |
| Flag missing or inconsistent data | Often | Yes |
| Preserve multiple feasible histories | Varies | Bounded supported domain |
| Simulate evidence outcomes | Not established by cited public material | Implemented for the fixture |
| Rank evidence by decision effect and effort | Not established by cited public material | One-step implementation |

Avoid universal novelty or competitor claims.

## 4. Exasol architecture

**Message:** Exasol owns relational schema, source-coverage checks, candidate
generation, aggregation and persisted history. Bounded Python reasoning turns a
small complete candidate component into scenarios and decision bounds. The API
currently uses a labelled CSV adapter.

**Visual:** Warehouse data → Exasol SQL → complete bounded scenarios → planner →
API/UI.

**Proof required:** Show one live Exasol Personal query, version, row counts and
measured database time. Remove that claim if the live run is unavailable.

## 5. Correctness and evaluation

**Message:** The model fails closed. Missing coverage, duplicates,
contradictions, bad scenarios, timeouts and retractions cannot preserve an
unjustified exclusion.

**Current evidence:** 79 offline tests on the historical Adya QA environment and
83 tests on the exact integrated functional head, including API workflow and a
separate tiny oracle. The pnpm production build passes. The real Exasol boundary
run returned six shipments, fourteen candidate edges, zero blockers, and a
complete universe. Sequential strategy measurements remain pending.

**Figures after evaluation:** false exclusions within the declared scope,
coverage, held cases, action count, simulated retrieval minutes, database time,
solver time and end-to-end time.

## 6. Demo, limits and next validation

**Message:** Show initial uncertainty, one ranked record, proposal without
decision change, human acceptance, a decision diff, and one conflict or
retraction. End with the next validation: test which records are actually
obtainable and sufficient in a real warehouse workflow.

**Visible limits:** synthetic data; bounded closed inventory; one-step ranking;
CSV-backed API; no automatic release; no certification; AI limited to proposed
fields.

**Closing line:** “RecallNext identifies the missing fact most worth checking
while showing exactly what remains uncertain.”

## Source inventory

- Exasol AI + Data Challenge 2026 rules and judging criteria.
- FDA, *Identifying Additional Flexibilities for Satisfying the Food
  Traceability Rule’s Lot-Level Tracking Requirement*, June 2026.
- FoodLogiQ, *Data Accuracy in an Investigation*.
- GS1 EPCIS/CBV 2.0.1 artefacts.
- The exact RecallNext PR revision, SQL and raw evaluation files.
