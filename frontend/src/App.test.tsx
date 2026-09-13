// @vitest-environment jsdom
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: Error) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}
const response = (body: object) => new Response(JSON.stringify(body));
const action = (id: string) => ({
  action_id: id, action_type: "MANIFEST", target_id: id, question: `Inspect ${id}`,
  estimated_minutes: 2, availability: "AVAILABLE", ranking_reason: "Resolves cases",
  possible_outcomes: [], affected_shipments: [], conditional_best_case_resolved_cases: 10,
});
const incident = {
  incident_id: "INC-DEMO-001", recalled_lots: ["LOT-1"], current_version: 1,
  product_id: "PRODUCT-1", title: "Test recall", public_recall: null,
  snapshot_version: 1, model_version: "test", data_source: "SYNTHETIC_FIXTURE",
  data_source_detail: "Synthetic test data", summary: { feasible_scenarios: 2, solver_status: "SUCCESS" },
  latest_diff: [],
};
let examples: Map<string, ReturnType<typeof deferred<Response>>>;
let signals: Map<string, AbortSignal>;
let fetchMock: ReturnType<typeof vi.fn>;
let post: ReturnType<typeof deferred<Response>>;
const storedFact = { fact_type: "allocation", quantity: 7 };
const proposal = { evidence_id: "EV-STORED", status: "PENDING_REVIEW", duplicate: false,
  source_reference: "stored/source", proposed_fact: storedFact };

beforeEach(() => {
  examples = new Map([['A', deferred<Response>()], ['B', deferred<Response>()]]);
  signals = new Map();
  post = deferred<Response>();
  fetchMock = vi.fn((path: string, init?: RequestInit) => {
    if (path === '/api/incidents') return Promise.resolve(response({ incidents: [{ incident_id: incident.incident_id }] }));
    if (path.endsWith('/example-fact')) {
      const id = path.split('/').at(-2)!;
      signals.set(id, init!.signal!);
      // Deliberately ignore abort: simulate a response already queued for delivery.
      return examples.get(id)!.promise;
    }
    if (path.endsWith('/accept') || path.endsWith('/reject')) return Promise.resolve(response({ current_version: 2, solver_status: "SUCCESS" }));
    if (init?.method === 'POST') return post.promise;
    if (path.endsWith('/evidence-actions')) return Promise.resolve(response({ actions: [action('A'), action('B')] }));
    if (path.endsWith('/decisions')) return Promise.resolve(response({ decisions: [] }));
    if (path.endsWith('/evidence')) return Promise.resolve(response({ evidence: [] }));
    return Promise.resolve(response(incident));
  });
  vi.stubGlobal('fetch', fetchMock);
});
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

async function open() {
  render(<App />);
  await screen.findByLabelText('Proposed structured fact');
  await waitFor(() => expect(signals.has('A')).toBe(true));
}
const factField = () => screen.getByLabelText('Proposed structured fact') as HTMLTextAreaElement;
async function deliver(id: string, fact: object) {
  await act(async () => { examples.get(id)!.resolve(response({ proposed_fact: fact, source_reference: `source/${id}` })); });
}
async function save() {
  fireEvent.click(screen.getByText('Save proposal'));
  await waitFor(() => expect(fetchMock.mock.calls.some(([path, init]) => path.endsWith('/evidence') && init?.method === 'POST')).toBe(true));
}

describe('example request lifecycle', () => {
  it.each(['accept', 'reject'])('keeps server-confirmed evidence visible through a late response and %s', async (decision) => {
    await open();
    fireEvent.change(factField(), { target: { value: JSON.stringify({ quantity: 3 }) } });
    await save();
    await act(async () => { post.resolve(response(proposal)); });
    await screen.findByText('Awaiting acceptance');
    await deliver('A', { quantity: 999 });
    expect(signals.get('A')!.aborted).toBe(true);
    expect(JSON.parse(factField().value)).toEqual(storedFact);
    expect(factField().disabled).toBe(true);
    expect((screen.getByLabelText('Source reference') as HTMLInputElement).value).toBe('stored/source');
    expect((screen.getByRole('button', { name: /Inspect B/ }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.change(screen.getByLabelText('Verified by'), { target: { value: 'Tester' } });
    if (decision === 'reject') fireEvent.change(screen.getByLabelText('Rejection reason'), { target: { value: 'Unreadable' } });
    fireEvent.click(screen.getByText(decision === 'accept' ? 'Accept and reassess' : 'Reject'));
    await waitFor(() => expect(fetchMock.mock.calls.some(([path]) => path.endsWith(`/EV-STORED/${decision}`))).toBe(true));
  });

  it('invalidates the request on save even without a manual edit', async () => {
    await open();
    await save();
    expect(signals.get('A')!.aborted).toBe(true);
    await deliver('A', { quantity: 999 });
    expect(factField().value).toBe('{}');
    await act(async () => { post.resolve(response(proposal)); });
    expect(JSON.parse(factField().value)).toEqual(storedFact);
  });

  it.each(['Proposed structured fact', 'Source reference'])('preserves manual edits to %s before saving', async (label) => {
    await open();
    fireEvent.change(screen.getByLabelText(label), { target: { value: label === 'Source reference' ? 'manual/source' : '{"quantity":3}' } });
    const draft = factField().value;
    await deliver('A', { quantity: 999 });
    expect(factField().value).toBe(draft);
    expect(signals.get('A')!.aborted).toBe(true);
  });

  it('ignores old selection responses while loading the new selection', async () => {
    await open();
    fireEvent.click(screen.getByRole('button', { name: /Inspect B/ }));
    await deliver('B', { quantity: 2 });
    await deliver('A', { quantity: 999 });
    expect(JSON.parse(factField().value)).toEqual({ quantity: 2 });
    expect(signals.get('A')!.aborted).toBe(true);
  });

  it('ignores errors from invalidated requests', async () => {
    await open();
    await save();
    await act(async () => { post.resolve(response(proposal)); });
    await act(async () => { examples.get('A')!.reject(new Error('stale failure')); });
    expect(screen.queryByText('stale failure')).toBeNull();
    expect(JSON.parse(factField().value)).toEqual(storedFact);
  });

  it('retains an editable draft after a failed save without reviving the example', async () => {
    await open();
    await save();
    await act(async () => { post.reject(new Error('Save failed')); });
    await screen.findByText('Save failed');
    await deliver('A', { quantity: 999 });
    expect(factField().value).toBe('{}');
    expect(factField().disabled).toBe(false);
    expect((screen.getByText('Accept and reassess') as HTMLButtonElement).disabled).toBe(true);
  });
});
