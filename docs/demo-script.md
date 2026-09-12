# Three-minute demo script

Record only after the live Exasol segment and final values are verified. Replace
every bracketed database cue with the actual result or remove that claim.

## 0:00–0:20 — Problem

**Screen:** Incident header and recalled lot.

“A distributor knows one supplier lot is recalled, but two container mappings
are incomplete. RecallNext asks which obtainable record is most useful to check
next. This demo uses synthetic warehouse data.”

## 0:20–0:45 — Initial uncertain hold

**Screen:** Six shipment decisions, safety notice and 125 histories.

“The bounded model preserves 125 feasible histories. Four shipments remain
possible inclusions. Two are excluded under the recorded assumptions because
their source-qualified homogeneous container belongs to another supplier.
Unknown coverage would be unresolved; it would not become an exclusion.”

Point to the lower and upper case bounds. Do not sum per-shipment maxima as one
actual recalled total.

## 0:45–1:15 — Ranked next evidence

**Screen:** Evidence queue and selected dispatch manifest.

“The operator can retrieve a label, pick log, retained-case scan or manifest.
The queue includes unavailable outcomes, so guaranteed benefit may be zero.
Successful-outcome value is visibly labelled conditional, and effort is a
fixture estimate.”

## 1:15–1:45 — Human verification

**Screen:** Proposed manifest fields and version 1.

“The example document proposes a structured shipment allocation. Saving the
proposal does not change any shipment. A person checks the source, enters their
name and explicitly accepts it.”

Save first and show that the incident remains at version 1. Then accept.

## 1:45–2:10 — Decision diff

**Screen:** Version 1 → 2 diff for S-200.

“Acceptance creates version 2 and reruns the deterministic model. S-200 changes
from possible inclusion to the status justified by the reviewed manifest. The
diff retains the evidence reference and both bounds.”

Show retraction through the tested API if it is included in the final capture:
“Withdrawing that source creates version 3 and restores uncertainty from the
remaining active evidence.”

## 2:10–2:40 — Exasol and correctness

**Screen:** Real Exasol Personal command and sanitized result.

"This is a live candidate query on the Exasol Personal starter-kit deployment.
For the synthetic fixture, it returned six shipments and fourteen candidate
edges with zero blockers and a complete candidate universe. The one recorded
smoke run measured 164.668 milliseconds for the snapshot query and 79.505
milliseconds for candidate edges."

Use the sanitized output in `docs/live-exasol-verification.md` on screen. Do not
describe these single-run query timings as a performance benchmark. Do not give
a planner or end-to-end latency until that separate measurement has actually
been recorded. The exact integrated functional head has 102 passing tests; the
web demo remains a clearly labelled CSV-backed application.

## 2:40–3:00 — Limits and impact

**Screen:** Limitations slide.

“RecallNext is a bounded decision-support prototype. It uses synthetic data,
ranks one step ahead and never releases stock. Its value is a replayable queue
of missing evidence with explicit uncertainty. The next validation is testing
record availability and acceptance rules with a warehouse or quality expert.”

Before committing the video, confirm its duration is at most three minutes,
links and audio work, the synthetic-data notice is visible, and no credential,
private tab or unsupported control appears.
