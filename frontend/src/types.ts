export type Status = "CONFIRMED_INCLUSION" | "POSSIBLE_INCLUSION" | "EXCLUDED_UNDER_ASSUMPTIONS" | "UNRESOLVED";

export interface Decision {
  shipment_id: string;
  min_recalled_cases: number;
  max_recalled_cases: number;
  held_cases: number;
  status: Status;
  solver_status: string;
}

export interface Incident {
  incident_id: string;
  product_id: string;
  title: string;
  recalled_lots: string[];
  snapshot_version: number;
  current_version: number;
  model_version: string;
  data_source: string;
  data_source_detail: string;
  public_recall: PublicRecall | null;
  summary: { shipment_count: number; held_cases: number; feasible_scenarios: number; solver_status: string; status_counts: Record<string, number>; data_quality_issues: string[] };
  latest_diff: Diff[];
}

export interface IncidentListItem {
  incident_id: string;
  current_version: number;
  title: string;
  status: string;
  data_source: string;
}

export interface PublicRecall {
  source_name: string;
  recall_number: string;
  event_id: string;
  classification: string;
  recall_status: string;
  report_date: string;
  recall_initiation_date: string;
  recalling_firm: string;
  product_description: string;
  code_info: string;
  distribution_pattern: string;
  reason_for_recall: string;
  source_url: string;
  dataset_last_updated: string;
  fetched_at: string;
}

export interface EvidenceRecord {
  evidence_id: string;
  action_id: string;
  incident_version: number;
  status: string;
  verified_by?: string | null;
  source_reference: string;
  proposed_fact: object;
  accepted_into_version?: number;
  retracted_into_version?: number;
}

export interface Action {
  action_id: string;
  action_type: string;
  target_id: string;
  question: string;
  estimated_minutes: number;
  availability: string;
  worst_case_resolved_cases: number;
  conditional_best_case_resolved_cases: number;
  conditional_worst_case_resolved_cases: number;
  ranking_reason: string;
  possible_outcomes: string[];
  affected_shipments: string[];
  dominated?: boolean;
}

export interface Diff {
  shipment_id: string;
  old_status: Status;
  new_status: Status;
  old_bounds: [number, number];
  new_bounds: [number, number];
  evidence_id: string;
  remaining_unresolved_cases: number;
}
