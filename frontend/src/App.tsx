import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Action, Decision, EvidenceRecord, Incident, IncidentListItem, Status } from "./types";

const labels: Record<Status, string> = {
  CONFIRMED_INCLUSION: "Confirmed inclusion",
  POSSIBLE_INCLUSION: "Possible inclusion",
  EXCLUDED_UNDER_ASSUMPTIONS: "Excluded under assumptions",
  UNRESOLVED: "Unresolved",
};

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
  const [incidentOptions, setIncidentOptions] = useState<IncidentListItem[]>([]);
  const [incidentId, setIncidentId] = useState("");
  const [incident, setIncident] = useState<Incident | null>(null);
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [actions, setActions] = useState<Action[]>([]);
  const [evidenceLog, setEvidenceLog] = useState<EvidenceRecord[]>([]);
  const [selected, setSelected] = useState<Action | null>(null);
  const [fact, setFact] = useState("{}");
  const [source, setSource] = useState("");
  const [reviewer, setReviewer] = useState("");
  const [rejectionReason, setRejectionReason] = useState("");
  const [retractionReason, setRetractionReason] = useState("");
  const [accessKey, setAccessKey] = useState("");
  const [sourceDocument, setSourceDocument] = useState<File | null>(null);
  const [documentHash, setDocumentHash] = useState<string | null>(null);
  const [extractionConfigured, setExtractionConfigured] = useState(false);
  const [writeAuthRequired, setWriteAuthRequired] = useState(false);
  const [evidenceId, setEvidenceId] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const exampleRequest = useRef<AbortController | null>(null);

  function cancelExample() {
    exampleRequest.current?.abort();
    exampleRequest.current = null;
  }

  function writeHeaders(jsonBody = true): Record<string, string> {
    const headers: Record<string, string> = {};
    if (jsonBody) headers["Content-Type"] = "application/json";
    if (accessKey.trim()) headers.Authorization = `Bearer ${accessKey.trim()}`;
    return headers;
  }

  useEffect(() => {
    json<{ document_extraction_configured: boolean; write_auth_required: boolean }>("/api/health")
      .then((health) => {
        setExtractionConfigured(Boolean(health.document_extraction_configured));
        setWriteAuthRequired(Boolean(health.write_auth_required));
      })
      .catch((reason) => setError(reason.message));
    json<{ incidents: IncidentListItem[] }>("/api/incidents")
      .then(({ incidents }) => {
        if (!incidents.length) throw new Error("No incidents are available");
        setIncidentOptions(incidents);
        setIncidentId(incidents[0].incident_id);
      })
      .catch((reason) => setError(reason.message));
  }, []);

  const load = useCallback(async () => {
    if (!incidentId) return;
    const [incidentData, decisionData, actionData, evidenceData] = await Promise.all([
      json<Incident>(`/api/incidents/${incidentId}`),
      json<{ decisions: Decision[] }>(`/api/incidents/${incidentId}/decisions`),
      json<{ actions: Action[] }>(`/api/incidents/${incidentId}/evidence-actions`),
      json<{ evidence: EvidenceRecord[] }>(`/api/incidents/${incidentId}/evidence`),
    ]);
    setIncident(incidentData);
    setDecisions(decisionData.decisions);
    setActions(actionData.actions);
    setEvidenceLog(evidenceData.evidence);
    setSelected((current) => current
      ? actionData.actions.find((item) => item.action_id === current.action_id) || actionData.actions[0]
      : actionData.actions[0]);
  }, [incidentId]);

  useEffect(() => { load().catch((reason) => setError(reason.message)); }, [load]);
  useEffect(() => {
    if (!selected || !incidentId) return;
    const controller = new AbortController();
    exampleRequest.current = controller;
    setFact("{}");
    setSource("");
    setSourceDocument(null);
    setDocumentHash(null);
    json<{ proposed_fact: object; source_reference: string }>(
      `/api/incidents/${incidentId}/evidence-actions/${selected.action_id}/example-fact`,
      { signal: controller.signal },
    )
      .then((data) => {
        if (!controller.signal.aborted) {
          setFact(JSON.stringify(data.proposed_fact, null, 2));
          setSource(data.source_reference);
        }
      })
      .catch((reason) => {
        if (!controller.signal.aborted) setError(reason.message);
      });
    setEvidenceId(null);
    setMessage(null);
    return () => controller.abort();
  }, [incidentId, selected?.action_id]);

  const openCases = useMemo(
    () => decisions
      .filter((item) => item.status === "POSSIBLE_INCLUSION" || item.status === "UNRESOLVED")
      .reduce((sum, item) => sum + item.held_cases, 0),
    [decisions],
  );
  const retractable = evidenceLog.find((item) => item.status === "ACCEPTED" || item.status === "CONFLICTING");
  const writeAccessMissing = writeAuthRequired && !accessKey.trim();

  async function extractDocument() {
    if (!selected || !incident || !sourceDocument || busy || evidenceId) return;
    cancelExample();
    setBusy(true); setError(null); setMessage(null);
    try {
      const body = new FormData();
      body.append("document", sourceDocument);
      const extracted = await json<{
        proposed_fact: object;
        source_reference: string;
        content_hash: string;
        model: string;
        requires_human_review: boolean;
      }>(`/api/incidents/${incidentId}/evidence-actions/${selected.action_id}/extract-document`, {
        method: "POST",
        headers: writeHeaders(false),
        body,
      });
      setFact(JSON.stringify(extracted.proposed_fact, null, 2));
      setSource(extracted.source_reference);
      setDocumentHash(extracted.content_hash);
      setMessage(`OpenAI extracted a proposal with ${extracted.model}. Review every field before saving.`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not extract the document");
    } finally { setBusy(false); }
  }

  async function propose() {
    if (!selected || !incident || busy || evidenceId) return;
    cancelExample();
    setBusy(true); setError(null); setMessage(null);
    try {
      const parsed = JSON.parse(fact);
      const contentHash = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(`${source}:${fact}`));
      const hash = documentHash || [...new Uint8Array(contentHash)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
      const evidence = await json<EvidenceRecord & { duplicate: boolean }>(`/api/incidents/${incidentId}/evidence`, {
        method: "POST",
        headers: writeHeaders(),
        body: JSON.stringify({ action_id: selected.action_id, source_reference: source, proposed_fact: parsed, content_hash: hash, review_status: "PENDING_REVIEW" }),
      });
      const reviewable = evidence.status === "PENDING_REVIEW";
      setSource(evidence.source_reference);
      setFact(JSON.stringify(evidence.proposed_fact, null, 2));
      setEvidenceId(reviewable ? evidence.evidence_id : null);
      setMessage(evidence.duplicate
        ? `This document is already ${evidence.status.toLowerCase().replaceAll("_", " ")}.`
        : "Proposal saved. Decisions have not changed.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not save proposal");
    } finally { setBusy(false); }
  }

  async function accept() {
    if (!evidenceId || !incident || !reviewer.trim()) return;
    setBusy(true); setError(null);
    try {
      const result = await json<{ current_version: number; solver_status: string }>(`/api/incidents/${incidentId}/evidence/${evidenceId}/accept`, {
        method: "POST", headers: writeHeaders(),
        body: JSON.stringify({ verified_by: reviewer.trim(), expected_version: incident.current_version }),
      });
      setMessage(result.solver_status === "SUCCESS" ? `Accepted into incident version ${result.current_version}.` : `Version ${result.current_version} is unresolved because the evidence conflicts.`);
      setEvidenceId(null);
      await load();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not accept evidence"); }
    finally { setBusy(false); }
  }

  async function reject() {
    if (!evidenceId || !incident || !reviewer.trim() || !rejectionReason.trim()) return;
    setBusy(true); setError(null);
    try {
      await json(`/api/incidents/${incidentId}/evidence/${evidenceId}/reject`, {
        method: "POST", headers: writeHeaders(),
        body: JSON.stringify({ verified_by: reviewer.trim(), expected_version: incident.current_version, reason: rejectionReason.trim() }),
      });
      setMessage("Proposal rejected. Shipment decisions and the incident version are unchanged.");
      setEvidenceId(null);
      await load();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not reject evidence"); }
    finally { setBusy(false); }
  }

  async function retract() {
    if (!retractable || !incident || !reviewer.trim() || !retractionReason.trim()) return;
    setBusy(true); setError(null);
    try {
      const result = await json<{ current_version: number }>(`/api/incidents/${incidentId}/evidence/${retractable.evidence_id}/retract`, {
        method: "POST", headers: writeHeaders(),
        body: JSON.stringify({ verified_by: reviewer.trim(), expected_version: incident.current_version, reason: retractionReason.trim() }),
      });
      setRetractionReason("");
      setMessage(`Evidence retracted into incident version ${result.current_version}.`);
      await load();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not retract evidence"); }
    finally { setBusy(false); }
  }

  if (!incident) return <main className="loading"><span>RN</span><p>{error || "Loading investigation..."}</p></main>;

  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand"><span>RN</span><strong>RecallNext</strong></div>
        <nav><a href="#investigation">Investigation</a><a href="#review">Evidence review</a><a href="#audit">Audit</a></nav>
        <div className="source-badge"><i />{incident.data_source.replaceAll("_", " ")}</div>
      </header>

      <main id="investigation">
        <section className="incident-head">
          <div><p className="eyebrow">Active investigation - version {incident.current_version}</p><h1>{incident.title}</h1><p className="lede">Bound the recalled quantity in every shipment, then rank the next obtainable record by how much uncertainty it can remove.</p></div>
          <div className="identity"><label>Incident<select value={incidentId} onChange={(event) => setIncidentId(event.target.value)}>{incidentOptions.map((item) => <option key={item.incident_id} value={item.incident_id}>{item.incident_id}</option>)}</select></label><span>Recalled lot</span><strong>{incident.recalled_lots.join(", ")}</strong></div>
        </section>

        <aside className="notice"><strong>Decision support only.</strong> Excluded under recorded assumptions does not mean safe. A qualified person controls holds and releases. <span>{incident.data_source_detail}</span></aside>

        {incident.public_recall && <section className="public-source panel"><div><p className="eyebrow">Official public recall context</p><h2>{incident.public_recall.recall_number}</h2></div><dl><div><dt>Classification</dt><dd>{incident.public_recall.classification}</dd></div><div><dt>Firm</dt><dd>{incident.public_recall.recalling_firm}</dd></div><div><dt>Code information</dt><dd>{incident.public_recall.code_info}</dd></div><div><dt>Distribution</dt><dd>{incident.public_recall.distribution_pattern}</dd></div><div className="wide"><dt>Reason</dt><dd>{incident.public_recall.reason_for_recall}</dd></div></dl><a href={incident.public_recall.source_url} target="_blank" rel="noreferrer">Open machine-readable FDA record</a></section>}

        <section className="metrics"><article><span>Cases still uncertain</span><strong>{openCases}</strong><small>across current shipment scope</small></article><article><span>Feasible histories</span><strong>{incident.summary.feasible_scenarios}</strong><small>deterministically enumerated</small></article><article><span>Next evidence</span><strong>{actions[0]?.estimated_minutes ?? "-"}<em> min</em></strong><small>estimated retrieval effort</small></article><article><span>Computation</span><strong className="word">{incident.summary.solver_status}</strong><small>{incident.model_version}</small></article></section>

        <section className="workspace">
          <div className="shipments panel"><div className="panel-title"><div><p className="eyebrow">Current decisions</p><h2>Shipment exposure</h2></div><span>{decisions.length} shipments</span></div><div className="table-wrap"><table><thead><tr><th>Shipment</th><th>Decision</th><th>Recalled-case bound</th><th>Held</th></tr></thead><tbody>{decisions.map((decision) => <tr key={decision.shipment_id}><td><strong>{decision.shipment_id}</strong></td><td><StatusPill status={decision.status} /></td><td><div className="bounds"><span>{decision.min_recalled_cases}</span><i /><span>{decision.max_recalled_cases}</span></div></td><td>{decision.status === "EXCLUDED_UNDER_ASSUMPTIONS" ? "0" : decision.held_cases} cases</td></tr>)}</tbody></table></div></div>
          <aside className="actions panel"><div className="panel-title"><div><p className="eyebrow">Ranked investigation queue</p><h2>Next evidence</h2></div></div><div className="action-list">{actions.map((action, index) => <button key={action.action_id} className={selected?.action_id === action.action_id ? "action selected" : "action"} disabled={busy || Boolean(evidenceId)} onClick={() => setSelected(action)}><span className="rank">{String(index + 1).padStart(2, "0")}</span><span className="action-copy"><strong>{action.question}</strong><small>{action.action_type.replaceAll("_", " ")} - {action.target_id}</small><span className="impact">Up to {action.conditional_best_case_resolved_cases} cases conditionally - {action.estimated_minutes} min</span></span><span className="arrow">&gt;</span></button>)}</div><p className="method"><strong>Why this rank</strong>{selected?.ranking_reason} <span>Possible outcomes: {selected?.possible_outcomes.join(", ").toLowerCase().replaceAll("_", " ")}.</span></p></aside>
        </section>

        <section className="review panel" id="review">
          <div className="panel-title">
            <div><p className="eyebrow">Human review boundary</p><h2>Review proposed evidence</h2></div>
            <span className="pending">{evidenceId ? "Awaiting acceptance" : "No decision change yet"}</span>
          </div>
          <div className="review-grid">
            <div className="source-preview">
              <span className="doc-label">{extractionConfigured ? "Live AI document extraction" : "Computed candidate preview"}</span>
              <div className="extractor">
                <label>Reviewer access key<input type="password" value={accessKey} autoComplete="off" placeholder={writeAuthRequired ? "Required for protected actions" : "Optional in local mode"} onChange={(event) => setAccessKey(event.target.value)} /></label>
                <label>Source document<input type="file" accept=".pdf,.png,.jpg,.jpeg,.webp,.txt,.csv,.json" disabled={busy || Boolean(evidenceId) || !extractionConfigured} onChange={(event) => { setSourceDocument(event.target.files?.[0] || null); setDocumentHash(null); }} /></label>
                <button className="secondary" disabled={busy || Boolean(evidenceId) || !sourceDocument || !extractionConfigured || writeAccessMissing} onClick={extractDocument}>Extract with OpenAI</button>
                <small>{extractionConfigured ? "The model proposes structured fields only. It cannot accept evidence or change a shipment decision." : "Live extraction is unavailable until the server has an OpenAI runtime key and model."}</small>
              </div>
              <div className="document"><p>{selected?.action_type.replaceAll("_", " ")}</p><strong>{selected?.target_id}</strong><dl><dt>Scope</dt><dd>{selected?.affected_shipments.join(", ")}</dd><dt>Retrieval</dt><dd>{selected?.estimated_minutes} min</dd><dt>Availability</dt><dd>{selected?.availability}</dd></dl></div>
              <small>The computed candidate comes from current feasible histories. A qualified reviewer must verify the named source before accepting any proposal.</small>
            </div>
            <div className="form">
              <label>Source reference<input value={source} disabled={busy || Boolean(evidenceId)} onChange={(event) => { cancelExample(); setSource(event.target.value); }} /></label>
              <label>Proposed structured fact<textarea rows={9} value={fact} disabled={busy || Boolean(evidenceId)} onChange={(event) => { cancelExample(); setFact(event.target.value); }} spellCheck={false} /></label>
              <label>Verified by<input value={reviewer} placeholder="Reviewer name" onChange={(event) => setReviewer(event.target.value)} /></label>
              {evidenceId && <label>Rejection reason<input value={rejectionReason} placeholder="Required only for rejection" onChange={(event) => setRejectionReason(event.target.value)} /></label>}
              {writeAccessMissing && <p className="feedback warning">Enter the reviewer access key to use protected actions.</p>}
              {error && <p className="feedback error">{error}</p>}
              {message && <p className="feedback success">{message}</p>}
              <div className="controls">
                <button className="secondary" disabled={busy || Boolean(evidenceId) || writeAccessMissing} onClick={propose}>Save proposal</button>
                <button className="danger" disabled={busy || !evidenceId || !reviewer.trim() || !rejectionReason.trim() || writeAccessMissing} onClick={reject}>Reject</button>
                <button className="primary" disabled={busy || !evidenceId || !reviewer.trim() || writeAccessMissing} onClick={accept}>Accept and reassess</button>
              </div>
              <p className="boundary">Saving a proposal never changes a shipment decision. Acceptance checks the displayed incident version and runs deterministic reassessment.</p>
            </div>
          </div>
        </section>

        <section className="audit panel" id="audit"><div className="panel-title"><div><p className="eyebrow">Evidence audit</p><h2>Reviewed evidence</h2></div><span>{evidenceLog.length} records</span></div>{retractable ? <div className="retract-row"><div><strong>{retractable.evidence_id}</strong><span>{retractable.status.replaceAll("_", " ")} by {retractable.verified_by}</span></div><label>Retraction reason<input value={retractionReason} placeholder="Why is this source no longer valid?" onChange={(event) => setRetractionReason(event.target.value)} /></label><button className="danger" disabled={busy || !reviewer.trim() || !retractionReason.trim() || writeAccessMissing} onClick={retract}>Retract latest reviewed evidence</button></div> : <p className="empty">No accepted or conflicting evidence can be retracted.</p>}</section>

        {incident.latest_diff.length > 0 && <section className="diff panel"><div className="panel-title"><div><p className="eyebrow">Version {incident.current_version - 1} to {incident.current_version}</p><h2>Decision changes</h2></div></div>{incident.latest_diff.map((change) => <div className="diff-row" key={change.shipment_id}><strong>{change.shipment_id}</strong><StatusPill status={change.old_status} /><span className="diff-arrow">-&gt;</span><StatusPill status={change.new_status} /><span>{change.old_bounds.join("-")} cases to {change.new_bounds.join("-")} cases</span><small>{change.evidence_id}</small></div>)}</section>}
      </main>
      <footer><span>RecallNext - synthetic private warehouse fixture with optional public openFDA context</span><span>Snapshot {incident.snapshot_version} - {incident.model_version}</span></footer>
    </div>
  );
}
