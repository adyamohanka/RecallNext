# Safety and limitations

RecallNext is an internal investigation prototype built on synthetic data. It
does not certify food safety, determine legal compliance, issue public alerts
or authorize a physical stock release. Qualified people remain responsible for
holds, release decisions, notifications and regulatory procedures.

## Enforced boundaries

- The only shipment statuses are `CONFIRMED_INCLUSION`, `POSSIBLE_INCLUSION`,
  `EXCLUDED_UNDER_ASSUMPTIONS` and `UNRESOLVED`.
- Missing required source coverage, duplicate inventory identifiers, invalid
  scenarios, conflicts, infeasibility, unsupported input and computation limits
  prevent narrowing.
- A decision with an incomplete candidate universe or failed solver cannot be
  persisted as an inclusion or exclusion.
- Persisted statuses must agree with their minimum and maximum recalled-case
  bounds.
- Lot identity contains both source and lot code.
- Proposed, rejected or unavailable evidence has no decision effect.
- Human acceptance and an exact current version are required before
  reassessment; an older pending proposal cannot cross a version boundary.
- A pending review locks the displayed action, source and structured fact.
  Rejected, retracted and older evidence hashes cannot strand a later proposal.
- Retraction rebuilds the result from the original scenarios and remaining
  active evidence.
- One observed case can tighten that shipment by one case but cannot establish
  every case in a mixed container; a lot incompatible with the target shipment
  is rejected before review.

## Interpretation

`EXCLUDED_UNDER_ASSUMPTIONS` means no successful feasible allocation contains
the incident’s recalled lot in that shipment under the recorded finite inputs.
It does not establish that the product is fit to consume, free from another
hazard, legally releasable or outside another incident.

Minimum and maximum recalled cases are calculated per shipment. Maxima for
different shipments may come from different scenarios, so summing them does not
produce one actual recalled total. Shipment quantity, possibly recalled
quantity and operational hold quantity must remain separate.

Evidence content hashes detect repeated content; they do not establish a
document’s authenticity or truth. A source reference does not prove that a
record describes what physically shipped.

## Supported model and current gaps

The model covers intact cases, one product, one location and one closed
synthetic inventory window. It does not cover transformations,
cross-contamination, returns, losses, opening inventory, arbitrary unit
conversion or warehouse-scale optimization.

- The running web application reads committed CSVs. The Exasol schema, loader,
  queries and persistence path were verified separately against a real Exasol
  deployment, but the API repository adapter remains unconnected.
- Destructive demo-fixture replacement is allowed only when no other incident
  exists in the schema. The loader aborts before deletion in a shared schema.
- The scenario enumerator is capped at 250,000 combinations and 10,000 feasible
  scenarios. It returns no partial universe when a limit is exceeded.
- The evidence queue ranks one step ahead and does not claim a globally optimal
  investigation plan.
- Retrieval minutes are fixture estimates, not measured operational time.
- Example document facts are synthetic. No live LLM or document service is
  connected.
- Incident and evidence versions are in memory and reset at API restart.
- Retraction is implemented in the API, uses reverse chronological order for
  multiple reviewed facts, and is not exposed in the current UI.
- Sequential baseline evaluation is recorded against committed synthetic
  scenarios. Single-run live Exasol query timings are recorded separately, but
  they are not a performance benchmark.

## Data and AI boundary

All committed operational data must stay fictional and labelled synthetic. Do
not commit credentials, private documents, database files, deployment state,
generated secrets or personal information.

An AI system may propose fields from a controlled document. It cannot accept
evidence, change constraints or make a release decision. Document text is
untrusted content. A saved model response must be visibly described as replay
data. The classifier and evidence ranking continue to work without an LLM.
