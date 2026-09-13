# Three-minute demo script

Target length: 2 minutes 55 seconds. All numbers below come from the committed
live result or deterministic fixture.

## 0:00-0:20 - Problem

**Screen:** Incident header and recalled lot.

“An official FDA recall tells a distributor which product and lot are affected,
but it does not contain that distributor's private container and shipment
history. RecallNext asks which missing warehouse record is most useful to check
next. The public recall shown here is real; the private warehouse demo is
synthetic and labelled.”

## 0:20-0:45 - Initial uncertain hold

**Screen:** Six shipment decisions, safety notice and 125 histories.

“The bounded model preserves 125 feasible histories. Four shipments remain
possible inclusions. Two are excluded under the recorded assumptions because
their source-qualified homogeneous container belongs to another supplier.
Unknown coverage would be unresolved; it would not become an exclusion.”

Point to the lower and upper case bounds. Do not sum per-shipment maxima as one
actual recalled total.

## 0:45-1:15 - Ranked next evidence

**Screen:** Evidence queue and selected dispatch manifest.

“The operator can retrieve a label, pick log, retained-case scan or manifest.
The queue includes unavailable outcomes, so guaranteed benefit may be zero.
Successful-outcome value is visibly labelled conditional, and effort is a
fixture estimate.”

## 1:15-1:45 - Human verification

**Screen:** Proposed manifest fields and version 1.

“The example document proposes a structured shipment allocation. Saving the
proposal does not change any shipment. A person checks the source, enters their
name and explicitly accepts it.”

Save first and show that the incident remains at version 1. Then accept.

## 1:45-2:08 - Decision diff and retraction

**Screen:** Version 1 → 2 diff for S-200.

“Acceptance creates version 2 and reruns the deterministic model. S-200 changes
from possible inclusion to the status justified by the reviewed manifest. The
diff retains the evidence reference and both bounds.”

Click retract in the UI: “Withdrawing that source creates version 3 and restores
uncertainty from the remaining active evidence. The review log and version are
persisted in Exasol, so reconstruction does not erase the audit trail.”

## 2:08-2:35 - Exasol and measured proof

**Screen:** Real Exasol Personal command and sanitized result.

“The visible API is running on Exasol Personal with encrypted, pinned transport.
Five live runs returned six shipments, fourteen candidate edges and 125 complete
histories. Median database times were 668 milliseconds for the incident snapshot
and 225 milliseconds for candidate edges. Complete scenario enumeration took a
median 1.455 seconds. Human acceptance persisted in 160 milliseconds, and a
fresh workflow reconstruction restored it from Exasol.”

Show `docs/evaluation-results/live-final.json`. Describe these as small-fixture
measurements over an SSH tunnel, not warehouse-scale results.

## 2:35-2:55 - Limits and impact

**Screen:** Limitations slide.

“RecallNext is bounded decision support. It ranks one step ahead and never
releases stock automatically. There is no live LLM or production ERP connector
in this build. Its value is a replayable queue of missing evidence with explicit
uncertainty, ready for validation with a warehouse or quality team.”

Before committing the video, confirm its duration is at most three minutes,
links and audio work, the synthetic-data notice is visible, and no credential,
private tab or unsupported control appears.
