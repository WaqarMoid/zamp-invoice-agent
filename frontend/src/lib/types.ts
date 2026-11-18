export type Decision = "APPROVE" | "REVIEW" | "HOLD" | "REJECT";
export type RunStatus = "QUEUED" | "RUNNING" | "COMPLETED" | "FAILED";
export type StageStatus = "PENDING" | "RUNNING" | "PASSED" | "FLAGGED" | "FAILED" | "SKIPPED";
export type Outcome = "PASS" | "INFO" | "FLAG" | "SKIP";
export type Severity = "REVIEW" | "HOLD" | "REJECT";
export type StageKey =
  | "ingest"
  | "extract"
  | "normalize"
  | "vendor"
  | "duplicates"
  | "po_match"
  | "reconcile"
  | "decide";

export interface Sample {
  id: string;
  filename: string;
  title: string;
  scenario: string;
  description: string;
  expected_decision: Decision;
  group: "Happy path" | "Edge cases" | "More scenarios";
}

export interface RunSummary {
  id: string;
  short_id: string;
  status: RunStatus;
  current_stage: StageKey | null;
  decision: Decision | null;
  label: string | null;
  headline: string | null;
  vendor_name: string | null;
  invoice_number: string | null;
  po_number: string | null;
  po_method: "explicit" | "inferred" | "none" | null;
  grand_total: string | null;
  flags_count: number;
  sample_id: string | null;
  filename: string;
  review_status: "NOT_REQUIRED" | "PENDING" | "APPROVED" | "REJECTED";
  created_at: string;
  completed_at: string | null;
  duration_ms: number | null;
}

export interface Check {
  stage_key: StageKey;
  check_id: string;
  name: string;
  outcome: Outcome;
  severity: Severity | null;
  message: string;
  evidence: Record<string, unknown>;
}

export interface Stage {
  stage_key: StageKey;
  position: number;
  label: string;
  description: string;
  status: StageStatus;
  summary: string | null;
  started_at: string | null;
  completed_at: string | null;
  duration_ms: number | null;
  output: Record<string, unknown> | null;
  checks: Check[];
}

export interface DecisionResult {
  decision: Decision;
  label: string;
  headline: string;
  reasons: { check_id: string; name: string; severity: Severity; message: string }[];
  recommended_actions: string[];
  payment_block: boolean;
  due_date: string | null;
  vendor_email: { subject: string; body: string } | null;
  key_facts: {
    vendor: string | null;
    po: string | null;
    po_method: string;
    invoice_number: string | null;
    invoice_date: string | null;
    grand_total: string | null;
  };
}

export interface RunDetail extends RunSummary {
  document: {
    filename: string;
    mime: string;
    size_bytes: number;
    page_count: number;
    has_text_layer: boolean;
    sha256: string;
  };
  use_cache: boolean;
  extraction_method: string | null;
  stages: Stage[];
  result: {
    extraction: Record<string, unknown> | null;
    normalized: Record<string, unknown> | null;
    decision: DecisionResult;
  } | null;
  reviewer: string | null;
  review_note: string | null;
  reviewed_at: string | null;
}

export interface Stats {
  total_runs: number;
  completed_runs: number;
  by_decision: Record<Decision, number>;
  auto_approval_rate: number; // APPROVE / completed, 0..1
  awaiting_action: number; // review_status == PENDING
  value_processed: string; // sum grand_total of completed runs, rupees
  median_duration_ms: number | null;
  runs_last_7_days: { date: string; count: number }[];
}

export interface Vendor {
  vendor_id: string;
  legal_name: string;
  gstin: string;
  state_code: string;
  status: "ACTIVE" | "INACTIVE";
  bank_name: string;
  bank_ifsc: string;
  bank_account_masked: string;
  payment_terms_days: number;
}

export interface POLine {
  line_no: number;
  description: string;
  hsn_sac: string;
  uom: string;
  quantity: string;
  unit_price: string;
  tax_rate_percent: string;
  billed_quantity: string;
  remaining_quantity: string;
}

export interface PurchaseOrder {
  po_number: string;
  vendor_id: string;
  vendor_name: string;
  po_date: string;
  valid_until: string;
  status: "OPEN" | "CLOSED" | "CANCELLED";
  net_value: string;
  billed_net_value: string;
  billed_pct: number; // 0..100+, can exceed 100 after an override
  billing_state: "UNBILLED" | "PARTIALLY_BILLED" | "FULLY_BILLED" | "OVERBILLED";
  lines: POLine[];
}

export interface LedgerEntry {
  id: number;
  source: "seed" | "run";
  run_id: string | null;
  invoice_number: string | null;
  invoice_date: string | null;
  grand_total: string;
  status: "APPROVED" | "IN_REVIEW" | "ON_HOLD" | "REJECTED";
  created_at: string;
}

export interface PurchaseOrderDetail extends PurchaseOrder {
  invoices: LedgerEntry[];
}

export interface ConfigResponse {
  app_name: string;
  version: string;
  buyer: {
    legal_name: string;
    trade_name: string;
    gstin: string;
    city: string;
    state: string;
    state_code: string;
  };
  thresholds: Record<string, unknown>;
  demo_mode: boolean;
  model: string;
}

export interface ReviewRequest {
  action: "approve" | "reject";
  note: string;
  reviewer?: string;
  bank_verified?: boolean;
}

export interface RunEventPayload {
  seq: number;
  type: string;
  payload: Record<string, any>;
  created_at: string;
}
