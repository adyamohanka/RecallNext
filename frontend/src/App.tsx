import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Action, Decision, Incident, Status } from "./types";

const INCIDENT_ID = "INC-DEMO-001";
const labels: Record<Status, string> = {
  CONFIRMED_INCLUSION: "Confirmed inclusion",
  POSSIBLE_INCLUSION: "Possible inclusion",
  EXCLUDED_UNDER_ASSUMPTIONS: "Excluded under assumptions",
  UNRESOLVED: "Unresolved",
};

function sourceFor(action: Action): string {
  const kind = action.action_type.toLowerCase().replaceAll("_", "-");
  return `synthetic/${kind}-${action.target_id.toLowerCase()}.json`;
}

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(body.detail || "Request failed");
  }
  return response.json();
}

function StatusPill({ status }: { status: Status }) {
  return <span className={`status status--${status.toLowerCase()}`}><i />{labels[status]}</span>;
}

export default function App() {
  const [incident, setIncident] = useState<Incident | null>(null);
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [actions, setActions] = useState<Action[]>([]);
  const [selected, setSelected] = useState<Action | null>(null);
  const [fact, setFact] = useState("{}");
  const [source, setSource] = useState("synthetic/manifest-S-200.json");
  const [reviewer, setReviewer] = useState("Harini");
  const [rejectionReason, setRejectionReason] = useState("Source does not support the proposed fact.");
  const [evidenceId, setEvidenceId] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const exampleRequest = useRef<AbortController | null>(null);

  function cancelExample() {
    exampleRequest.current?.abort();
    exampleRequest.current = null;
  }

  const load = useCallback(async () => {
    const [incidentData, decisionData, actionData] = await Promise.all([
      json<Incident>(`/api/incidents/${INCIDENT_ID}`),
      json<{ decisions: Decision[] }>(`/api/incidents/${INCIDENT_ID}/decisions`),
      json<{ actions: Action[] }>(`/api/incidents/${INCIDENT_ID}/evidence-actions`),
    ]);
    setIncident(incidentData);
    setDecisions(decisionData.decisions);
    setActions(actionData.actions);
    setSelected((current) => current ? actionData.actions.find((item) => item.action_id === current.action_id) || actionData.actions[0] : actionData.actions[0]);
  }, []);

  useEffect(() => { load().catch((reason) => setError(reason.message)); }, [load]);
  useEffect(() => {
    if (!selected) return;
    const controller = new AbortController();
    exampleRequest.current = controller;
    setFact("{}");
    setSource(sourceFor(selected));
    json<{ proposed_fact: object }>(`/api/incidents/${INCIDENT_ID}/evidence-actions/${selected.action_id}/example-fact`, { signal: controller.signal })
      .then((data) => {
        if (!controller.signal.aborted) setFact(JSON.stringify(data.proposed_fact, null, 2));
      })
      .catch((reason) => {
        if (!controller.signal.aborted) setError(reason.message);
      });
    setEvidenceId(null);
    setMessage(null);
    return () => controller.abort();
  }, [selected?.action_id]);

  const openCases = useMemo(() => decisions.filter((item) => item.status === "POSSIBLE_INCLUSION" || item.status === "UNRESOLVED").reduce((sum, item) => sum + item.held_cases, 0), [decisions]);

  async function propose() {
    if (!selected || !incident || busy || evidenceId) return;
    // Invalidate before hashing or posting; even a queued response must not
    // replace the draft or the server-confirmed evidence shown for review.
    cancelExample();
    setBusy(true); setError(null); setMessage(null);
    try {
      const parsed = JSON.parse(fact);
      const contentHash = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(`${source}:${fact}`));
      const hash = [...new Uint8Array(contentHash)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
      const evidence = await json<{ evidence_id: string; duplicate: boolean; status: string; source_reference: string; proposed_fact: object }>(`/api/incidents/${INCIDENT_ID}/evidence`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action_id: selected.action_id, source_reference: source, proposed_fact: parsed, content_hash: hash, review_status: "PENDING_REVIEW" }),
      });
      const reviewable = evidence.status === "PENDING_REVIEW";
      setSource(evidence.source_reference);
      setFact(JSON.stringify(evidence.proposed_fact, null, 2));
      setEvidenceId(reviewable ? evidence.evidence_id : null);
      setMessage(evidence.duplicate ? `This document is already ${evidence.status.toLowerCase().replaceAll("_", " ")}.` : "Proposal saved. Decisions have not changed.");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not save proposal"); }
    finally { setBusy(false); }
  }

  async function accept() {
    if (!evidenceId || !incident) return;
    setBusy(true); setError(null);
    try {
      const result = await json<{ current_version: number; solver_status: string }>(`/api/incidents/${INCIDENT_ID}/evidence/${evidenceId}/accept`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ verified_by: reviewer, expected_version: incident.current_version }),
      });
      setMessage(result.solver_status === "SUCCESS" ? `Accepted into incident version ${result.current_version}.` : `Version ${result.current_version} is unresolved because the evidence conflicts.`);
      setEvidenceId(null);
      await load();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not accept evidence"); }
    finally { setBusy(false); }
  }

  async function reject() {
    if (!evidenceId || !incident) return;
    setBusy(true); setError(null);
    try {
      await json(`/api/incidents/${INCIDENT_ID}/evidence/${evidenceId}/reject`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ verified_by: reviewer, expected_version: incident.current_version, reason: rejectionReason }),
      });
      setMessage("Proposal rejected. Shipment decisions and the incident version are unchanged.");
      setEvidenceId(null);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not reject evidence"); }
    finally { setBusy(false); }
  }

  if (!incident) return <main className="loading"><span>RN</span><p>{error || "Loading investigation…"}</p></main>;

  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand"><span>RN</span><strong>RecallNext</strong></div>
        <nav><a className="active">Investigation</a><a>Evidence log</a><a>Model notes</a></nav>
        <div className="source-badge"><i />{incident.data_source.replaceAll("_", " ")}</div>
      </header>

      <main>
        <section className="incident-head">
          <div>
            <p className="eyebrow">Active investigation · version {incident.current_version}</p>
            <h1>Apple lot exposure review</h1>
            <p className="lede">Trace the recalled lot through incomplete container records, then choose the evidence that resolves the most uncertainty.</p>
          </div>
          <div className="identity">
            <span>Incident</span><strong>{incident.incident_id}</strong>
            <span>Recalled lot</span><strong>{incident.recalled_lots[0]}</strong>
          </div>
        </section>

        <aside className="notice"><strong>Decision support only.</strong> Excluded under recorded assumptions does not mean safe. A qualified person controls holds and releases. <span>{incident.data_source_detail}</span></aside>

        <section className="metrics">
          <article><span>Cases still uncertain</span><strong>{openCases}</strong><small>across current shipment scope</small></article>
          <article><span>Feasible histories</span><strong>{incident.summary.feasible_scenarios}</strong><small>deterministically enumerated</small></article>
          <article><span>Next evidence</span><strong>{actions[0]?.estimated_minutes || "—"}<em> min</em></strong><small>estimated retrieval effort</small></article>
          <article><span>Computation</span><strong className="word">{incident.summary.solver_status}</strong><small>{incident.model_version}</small></article>
        </section>

        <section className="workspace">
          <div className="shipments panel">
            <div className="panel-title"><div><p className="eyebrow">Current decisions</p><h2>Shipment exposure</h2></div><span>{decisions.length} shipments</span></div>
            <div className="table-wrap"><table><thead><tr><th>Shipment</th><th>Decision</th><th>Recalled-case bound</th><th>Held</th></tr></thead><tbody>
              {decisions.map((decision) => <tr key={decision.shipment_id}><td><strong>{decision.shipment_id}</strong><small>STORE-{Number(decision.shipment_id.split("-")[1]) / 100}</small></td><td><StatusPill status={decision.status} /></td><td><div className="bounds"><span>{decision.min_recalled_cases}</span><i /><span>{decision.max_recalled_cases}</span></div></td><td>{decision.status === "EXCLUDED_UNDER_ASSUMPTIONS" ? "0" : decision.held_cases} cases</td></tr>)}
            </tbody></table></div>
          </div>

          <aside className="actions panel">
            <div className="panel-title"><div><p className="eyebrow">Ranked investigation queue</p><h2>Next evidence</h2></div></div>
            <div className="action-list">
              {actions.map((action, index) => <button key={action.action_id} className={selected?.action_id === action.action_id ? "action selected" : "action"} disabled={busy || Boolean(evidenceId)} onClick={() => setSelected(action)}>
                <span className="rank">{String(index + 1).padStart(2, "0")}</span><span className="action-copy"><strong>{action.question}</strong><small>{action.action_type.replaceAll("_", " ")} · {action.target_id}</small><span className="impact">Up to {action.conditional_best_case_resolved_cases} cases conditionally · {action.estimated_minutes} min</span></span><span className="arrow">→</span>
              </button>)}
            </div>
            <p className="method"><strong>Why this rank</strong>{selected?.ranking_reason} <span>Possible outcomes: {selected?.possible_outcomes.join(", ").toLowerCase().replaceAll("_", " ")}.</span></p>
          </aside>
        </section>

        <section className="review panel">
          <div className="panel-title"><div><p className="eyebrow">Human review boundary</p><h2>Review proposed evidence</h2></div><span className="pending">{evidenceId ? "Awaiting acceptance" : "No decision change yet"}</span></div>
          <div className="review-grid">
            <div className="source-preview"><span className="doc-label">Synthetic source preview</span><div className="document"><p>{selected?.action_type.replaceAll("_", " ")}</p><strong>{selected?.target_id}</strong><dl><dt>Scope</dt><dd>{selected?.affected_shipments.join(", ")}</dd><dt>Retrieval</dt><dd>{selected?.estimated_minutes} min</dd><dt>Availability</dt><dd>{selected?.availability}</dd></dl></div><small>{selected?.question} Example content comes from the committed synthetic incident.</small></div>
            <div className="form">
              <label>Source reference<input value={source} disabled={busy || Boolean(evidenceId)} onChange={(event) => { cancelExample(); setSource(event.target.value); }} /></label>
              <label>Proposed structured fact<textarea rows={9} value={fact} disabled={busy || Boolean(evidenceId)} onChange={(event) => { cancelExample(); setFact(event.target.value); }} spellCheck={false} /></label>
              <label>Verified by<input value={reviewer} onChange={(event) => setReviewer(event.target.value)} /></label>
              {evidenceId && <label>Rejection reason<input value={rejectionReason} onChange={(event) => setRejectionReason(event.target.value)} /></label>}
              {error && <p className="feedback error">{error}</p>}{message && <p className="feedback success">{message}</p>}
              <div className="controls"><button className="secondary" disabled={busy || Boolean(evidenceId)} onClick={propose}>Save proposal</button><button className="danger" disabled={busy || !evidenceId || !rejectionReason.trim()} onClick={reject}>Reject</button><button className="primary" disabled={busy || !evidenceId} onClick={accept}>Accept &amp; reassess</button></div>
              <p className="boundary">Saving a proposal never changes a shipment decision. While review is pending, its action, source and structured fact are locked so approval always applies to the displayed proposal. Acceptance checks the current incident version and runs deterministic reassessment.</p>
            </div>
          </div>
        </section>

        {incident.latest_diff.length > 0 && <section className="diff panel"><div className="panel-title"><div><p className="eyebrow">Version {incident.current_version - 1} → {incident.current_version}</p><h2>Decision changes</h2></div></div>{incident.latest_diff.map((change) => <div className="diff-row" key={change.shipment_id}><strong>{change.shipment_id}</strong><StatusPill status={change.old_status} /><span className="diff-arrow">→</span><StatusPill status={change.new_status} /><span>{change.old_bounds.join("–")} cases → {change.new_bounds.join("–")} cases</span><small>{change.evidence_id}</small></div>)}</section>}
      </main>
      <footer><span>RecallNext · synthetic produce-distribution prototype</span><span>Snapshot {incident.snapshot_version} · {incident.model_version}</span></footer>
    </div>
  );
}
