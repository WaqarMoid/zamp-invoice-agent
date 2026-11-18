import React, { useState, useEffect, useRef } from "react";
import { Link, useParams } from "react-router-dom";
import {
  FileText,
  Mail,
  ShieldAlert,
  X,
  ExternalLink,
  Copy,
  Check as CheckIcon,
  Radio,
} from "lucide-react";
import { api } from "../lib/api";
import { formatDuration, formatDate, formatRelativeTime } from "../lib/format";
import { useRunStream } from "../lib/useRunStream";
import type { Stage, StageKey } from "../lib/types";
import { Button } from "../components/Button";
import { DecisionBadge } from "../components/DecisionBadge";
import { OutcomeIcon } from "../components/OutcomeIcon";
import { StageMarker } from "../components/StageMarker";
import { KeyValue } from "../components/KeyValue";
import { Money } from "../components/Money";
import { Tabs } from "../components/Tabs";
import { Disclosure } from "../components/Disclosure";
import { Dialog } from "../components/Dialog";
import { Skeleton } from "../components/Skeleton";
import { StageOutputView } from "../components/StageOutputView";
import { useToast } from "../components/Toast";

export const RunDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { showToast } = useToast();

  const { run, isLoading, error, liveEventLog, elapsedMs, refetch } = useRunStream(id);

  const [selectedStageKey, setSelectedStageKey] = useState<StageKey>("ingest");
  const [userSelectedStage, setUserSelectedStage] = useState(false);
  const [activeTab, setActiveTab] = useState<string>("stage");

  // Document drawer state
  const [drawerOpen, setDrawerOpen] = useState(false);

  // Review modal state
  const [reviewAction, setReviewAction] = useState<"approve" | "reject" | null>(null);
  const [reviewNote, setReviewNote] = useState("");
  const [reviewerName, setReviewerName] = useState("AP reviewer");
  const [bankVerified, setBankVerified] = useState(false);
  const [submittingReview, setSubmittingReview] = useState(false);

  // Email draft modal state
  const [emailModalOpen, setEmailModalOpen] = useState(false);
  const [copiedEmail, setCopiedEmail] = useState(false);

  // Event log scroll ref
  const eventLogEndRef = useRef<HTMLDivElement>(null);
  const userScrolledLogRef = useRef(false);

  // Auto-follow running stage if user hasn't explicitly clicked a stage
  useEffect(() => {
    if (!userSelectedStage && run?.current_stage) {
      setSelectedStageKey(run.current_stage as StageKey);
    }
  }, [run?.current_stage, userSelectedStage]);

  // Auto-scroll event log
  useEffect(() => {
    if (activeTab === "events" && !userScrolledLogRef.current) {
      eventLogEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [liveEventLog, activeTab]);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton width="200px" height="16px" />
        <Skeleton width="340px" height="32px" />
        <Skeleton width="100%" height="180px" />
        <div className="grid grid-cols-12 gap-6">
          <div className="col-span-4 space-y-3">
            {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
              <Skeleton key={i} width="100%" height="56px" />
            ))}
          </div>
          <div className="col-span-8">
            <Skeleton width="100%" height="450px" />
          </div>
        </div>
      </div>
    );
  }

  if (error || !run) {
    return (
      <div className="p-8 bg-[var(--surface)] border border-[var(--reject-line)] rounded-[10px] text-[var(--reject)]">
        <h2 className="font-heading font-semibold text-[18px]">Error loading invoice run</h2>
        <p className="mt-2 text-[14px]">{error || "Run not found"}</p>
        <Link to="/" className="mt-4 inline-block text-[14px] underline font-medium">
          Return to Invoices
        </Link>
      </div>
    );
  }

  const stages = run.stages || [];
  const selectedStage =
    stages.find((s) => s.stage_key === selectedStageKey) || stages[0] || ({} as Stage);

  const decisionObj = run.result?.decision;
  const isDone = run.status === "COMPLETED";
  const isRunning = run.status === "RUNNING" || run.status === "QUEUED";

  // Decision border color
  const decisionLeftBorder =
    run.decision === "APPROVE"
      ? "border-l-[var(--approve)]"
      : run.decision === "HOLD"
      ? "border-l-[var(--hold)]"
      : run.decision === "REJECT"
      ? "border-l-[var(--reject)]"
      : "border-l-[var(--review)]";

  const handleReviewSubmit = async () => {
    if (!id || !reviewAction) return;
    if (reviewNote.trim().length < 5) {
      showToast("Audit note must be at least 5 characters.");
      return;
    }
    if (run.decision === "HOLD" && !bankVerified) {
      showToast("You must confirm bank account verification with the vendor.");
      return;
    }

    setSubmittingReview(true);
    try {
      await api.submitReview(id, {
        action: reviewAction,
        note: reviewNote.trim(),
        reviewer: reviewerName.trim() || "AP reviewer",
        bank_verified: bankVerified,
      });
      showToast(`Invoice marked as ${reviewAction === "approve" ? "approved" : "rejected"}.`);
      setReviewAction(null);
      setReviewNote("");
      await refetch();
    } catch (err: any) {
      showToast(`Review failed: ${err.message}`);
    } finally {
      setSubmittingReview(false);
    }
  };

  const handleCopyEmail = (body: string) => {
    navigator.clipboard.writeText(body);
    setCopiedEmail(true);
    setTimeout(() => setCopiedEmail(false), 2000);
  };

  // Announce live state for screen readers
  const announceText = isDone
    ? `Processing complete. Final decision: ${run.decision}`
    : `Stage ${run.current_stage || "running"}`;

  return (
    <div className="space-y-6">
      {/* Screen reader live announcement */}
      <div className="sr-only" aria-live="polite">
        {announceText}
      </div>

      {/* 1. Breadcrumb + Title Row */}
      <div>
        <div className="mb-2 text-[13px] text-[var(--ink-3)] flex items-center gap-1.5 select-none">
          <Link to="/" className="hover:text-[var(--ink)] text-[var(--ink-3)] no-underline">
            Invoices
          </Link>
          <span>/</span>
          <span className="font-mono text-[var(--ink-2)]">
            {run.invoice_number || run.document?.filename || run.id.slice(0, 8)}
          </span>
        </div>

        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <h1 className="font-heading font-bold text-[26px] leading-[32px] text-[var(--ink)] flex items-center gap-3">
            <span className={run.invoice_number ? "font-mono" : ""}>
              {run.invoice_number || run.document?.filename || `Run ${run.id.slice(0, 8)}`}
            </span>
          </h1>

          <div className="flex items-center gap-3 shrink-0">
            <DecisionBadge
              decision={run.decision}
              status={run.status}
              currentStageLabel={run.current_stage}
            />

            <span className="font-mono text-[13px] text-[var(--ink-2)] bg-[var(--surface)] border border-[var(--line)] px-2.5 py-1 rounded-[6px]">
              {formatDuration(elapsedMs)}
            </span>

            <Button
              variant="secondary"
              size="sm"
              icon={<FileText size={15} strokeWidth={1.5} />}
              onClick={() => setDrawerOpen(true)}
            >
              View document
            </Button>
          </div>
        </div>
      </div>

      {/* 2. Decision Panel */}
      <div
        className={`bg-[var(--surface)] border border-[var(--line)] ${decisionLeftBorder} border-l-[4px] rounded-[10px] p-6 shadow-[var(--shadow-2)] transition-all duration-300 min-h-[160px]`}
      >
        {isRunning ? (
          <div className="flex flex-col justify-center h-full space-y-3 py-2">
            <div className="flex items-center gap-2 text-[13px] text-[var(--ink-3)] font-mono">
              <Radio size={14} className="animate-pulse text-[var(--ink)]" />
              <span>Running automated AP policy verification...</span>
            </div>
            <div className="space-y-2">
              <Skeleton width="40%" height="28px" />
              <Skeleton width="75%" height="16px" />
              <Skeleton width="60%" height="16px" />
            </div>
            <p className="font-sans text-[13px] text-[var(--ink-3)] pt-1 m-0">
              Decision appears when all eight stages finish.
            </p>
          </div>
        ) : isDone && decisionObj ? (
          <div className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
              {/* Left Column (8 cols): Decision, Headline, Reasons, Actions */}
              <div className="lg:col-span-8 space-y-4">
                <div>
                  <span className="font-heading font-semibold text-[11px] leading-[16px] uppercase tracking-[0.08em] text-[var(--ink-3)] block mb-1">
                    DECISION
                  </span>
                  <div
                    className={`font-heading font-bold text-[32px] leading-[40px] tracking-[-0.015em] ${
                      run.decision === "APPROVE"
                        ? "text-[var(--approve)]"
                        : run.decision === "HOLD"
                        ? "text-[var(--hold)]"
                        : run.decision === "REJECT"
                        ? "text-[var(--reject)]"
                        : "text-[var(--review)]"
                    }`}
                  >
                    {decisionObj.label || run.decision}
                  </div>
                  <p className="font-sans text-[15px] leading-[24px] text-[var(--ink-2)] mt-1 max-w-[68ch]">
                    {decisionObj.headline || run.headline}
                  </p>
                </div>

                {/* Reasons List */}
                {decisionObj.reasons && decisionObj.reasons.length > 0 && (
                  <div className="space-y-2 pt-2">
                    <span className="font-heading font-semibold text-[11px] uppercase tracking-[0.08em] text-[var(--ink-3)] block">
                      Reasons for flag
                    </span>
                    <div className="space-y-2">
                      {decisionObj.reasons.map((r, i) => (
                        <div key={i} className="flex items-start gap-2.5 text-[14px]">
                          <div className="mt-0.5">
                            <OutcomeIcon outcome="FLAG" severity={r.severity} size={15} />
                          </div>
                          <div>
                            <span className="font-semibold text-[var(--ink)]">{r.name}:</span>{" "}
                            <span className="text-[var(--ink-2)]">{r.message}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Next Steps List */}
                {decisionObj.recommended_actions &&
                  decisionObj.recommended_actions.length > 0 && (
                    <div className="space-y-2 pt-2">
                      <span className="font-heading font-semibold text-[11px] uppercase tracking-[0.08em] text-[var(--ink-3)] block">
                        Next steps
                      </span>
                      <ol className="list-decimal pl-5 space-y-1.5 font-sans text-[14px] leading-[22px] text-[var(--ink)]">
                        {decisionObj.recommended_actions.map((act, i) => (
                          <li key={i}>{act}</li>
                        ))}
                      </ol>
                    </div>
                  )}

                {/* HOLD Fraud Warning Callout */}
                {run.decision === "HOLD" && (
                  <div className="flex items-start gap-3 p-3 bg-[var(--hold-tint)] border border-[var(--hold-line)] rounded-[8px] text-[13px] text-[var(--hold)]">
                    <ShieldAlert size={18} className="shrink-0 mt-0.5" strokeWidth={1.5} />
                    <div className="font-sans">
                      <span className="font-semibold">Security Protocol:</span> Do not reply to the
                      email this invoice came from. Call{" "}
                      {run.vendor_name || "the vendor"} on the verified phone number in the vendor
                      master before approving payment.
                    </div>
                  </div>
                )}
              </div>

              {/* Right Column (4 cols): Key Facts */}
              <div className="lg:col-span-4 bg-[var(--surface-sunken)] border border-[var(--line)] rounded-[8px] p-4 flex flex-col gap-4">
                <KeyValue label="VENDOR" value={run.vendor_name || "—"} />
                <KeyValue
                  label="INVOICE / DATE"
                  value={`${run.invoice_number || "—"} · ${formatDate(
                    decisionObj.key_facts?.invoice_date
                  )}`}
                  mono
                />
                <div className="flex flex-col gap-1">
                  <span className="font-heading font-semibold text-[11px] leading-[16px] uppercase tracking-[0.08em] text-[var(--ink-3)] select-none">
                    PO NUMBER
                  </span>
                  <div className="flex items-center gap-1.5 font-mono text-[14px]">
                    <span>{run.po_number || "—"}</span>
                    {run.po_method === "inferred" && (
                      <span className="text-[10px] px-1 py-0.2 rounded border border-[var(--line-strong)] text-[var(--ink-3)] uppercase">
                        inferred
                      </span>
                    )}
                  </div>
                </div>
                <KeyValue
                  label="AMOUNT"
                  value={
                    <Money
                      amount={
                        decisionObj.key_facts?.grand_total || run.grand_total
                      }
                    />
                  }
                  mono
                  size="lg"
                />
                <KeyValue
                  label={decisionObj.payment_block ? "PAYMENT" : "PAY BY"}
                  value={
                    decisionObj.payment_block ? (
                      <span className="text-[var(--reject)] font-semibold">Blocked</span>
                    ) : (
                      formatDate(decisionObj.due_date)
                    )
                  }
                  mono
                />
              </div>
            </div>

            {/* Action Buttons Row & AP Decision Audit Trail */}
            <div className="pt-4 border-t border-[var(--line)] flex flex-wrap items-center justify-between gap-4">
              {/* If Reviewed already */}
              {run.review_status !== "PENDING" && run.review_status !== "NOT_REQUIRED" && (
                <div className="text-[13px] text-[var(--ink-2)] font-sans">
                  <span className="font-semibold text-[var(--ink)]">AP Decision:</span>{" "}
                  {run.review_status === "APPROVED" ? (
                    <span className="text-[var(--approve)] font-semibold">Approved by AP</span>
                  ) : (
                    <span className="text-[var(--reject)] font-semibold">Rejected by AP</span>
                  )}{" "}
                  by {run.reviewer || "AP reviewer"} · {formatRelativeTime(run.reviewed_at)}
                  {run.review_note && ` · "${run.review_note}"`}
                </div>
              )}

              {/* If Pending review: Action buttons */}
              {run.review_status === "PENDING" && (
                <div className="flex items-center gap-3">
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => setReviewAction("approve")}
                  >
                    Approve
                  </Button>
                  <Button
                    variant="danger"
                    size="sm"
                    onClick={() => setReviewAction("reject")}
                  >
                    Reject
                  </Button>
                </div>
              )}

              {/* Vendor Email Draft Button */}
              {decisionObj.vendor_email && run.decision !== "HOLD" && (
                <div className="ml-auto">
                  <Button
                    variant="secondary"
                    size="sm"
                    icon={<Mail size={14} strokeWidth={1.5} />}
                    onClick={() => setEmailModalOpen(true)}
                  >
                    Vendor email draft
                  </Button>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="text-[14px] text-[var(--ink-2)]">Run failed or incomplete.</div>
        )}
      </div>

      {/* 3. Pipeline Area (12 cols) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column (4 cols): Stages Stepper */}
        <div className="lg:col-span-4 bg-[var(--surface)] border border-[var(--line)] rounded-[10px] p-4 shadow-[var(--shadow-1)] space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-[var(--line)]">
            <h2 className="font-heading font-semibold text-[16px] text-[var(--ink)]">
              Pipeline Stages
            </h2>
            {userSelectedStage && isRunning && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setUserSelectedStage(false)}
                className="text-[12px] h-[24px] px-2 text-[var(--ink-3)]"
              >
                Follow live
              </Button>
            )}
          </div>

          <div className="space-y-1 relative">
            {stages.map((st, idx) => {
              const isSelected = st.stage_key === selectedStageKey;
              const isStageRunning = st.status === "RUNNING";
              const isPassed = st.status === "PASSED";

              // Find highest severity flag in this stage
              const flagCheck = st.checks.find((c) => c.outcome === "FLAG");
              const highestSev = flagCheck?.severity || null;

              return (
                <div key={st.stage_key} className="relative">
                  {/* Connector line to next stage */}
                  {idx < stages.length - 1 && (
                    <div
                      className={`absolute left-[23px] top-[32px] w-[1.5px] h-[34px] z-0 ${
                        isPassed ? "bg-[var(--ink)]" : "bg-[var(--line)]"
                      }`}
                    />
                  )}

                  <div
                    tabIndex={0}
                    onClick={() => {
                      setSelectedStageKey(st.stage_key);
                      setUserSelectedStage(true);
                    }}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        setSelectedStageKey(st.stage_key);
                        setUserSelectedStage(true);
                      }
                    }}
                    className={`relative z-10 flex items-start gap-3 p-2.5 rounded-[8px] cursor-pointer transition-colors select-none min-h-[56px] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--focus)] ${
                      isSelected
                        ? "bg-[var(--surface-sunken)] border-l-[2px] border-l-[var(--ink)] pl-2"
                        : "hover:bg-[var(--surface-sunken)]"
                    }`}
                  >
                    <StageMarker
                      position={st.position}
                      status={st.status}
                      highestSeverity={highestSev}
                    />

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-1">
                        <span className="font-heading font-semibold text-[14px] text-[var(--ink)]">
                          {st.label}
                        </span>
                        <span className="font-mono text-[11px] text-[var(--ink-3)] shrink-0">
                          {st.duration_ms ? `${(st.duration_ms / 1000).toFixed(2)}s` : ""}
                        </span>
                      </div>
                      <div className="font-sans text-[12px] leading-[16px] text-[var(--ink-2)] truncate mt-0.5">
                        {isStageRunning
                          ? "Running…"
                          : st.summary || st.description || "Pending..."}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          <p className="font-sans text-[11px] leading-[16px] text-[var(--ink-3)] pt-2 border-t border-[var(--line)] m-0">
            Stage timings are real. The UI holds each step on screen for at least 300 ms so you can
            follow it.
          </p>
        </div>

        {/* Right Column (8 cols): Stage Detail / Extracted Data / Event Log */}
        <div className="lg:col-span-8 bg-[var(--surface)] border border-[var(--line)] rounded-[10px] p-6 shadow-[var(--shadow-1)] space-y-6">
          <Tabs
            tabs={[
              { id: "stage", label: "Stage", count: selectedStage.checks?.length },
              { id: "extracted", label: "Extracted data" },
              { id: "events", label: "Event log", count: liveEventLog.length },
            ]}
            activeTab={activeTab}
            onChange={setActiveTab}
          />

          {/* TAB 1: STAGE */}
          {activeTab === "stage" && (
            <div className="space-y-6">
              <div>
                <h2 className="font-heading font-semibold text-[18px] leading-[26px] text-[var(--ink)]">
                  {selectedStage.label}
                </h2>
                <p className="font-sans text-[14px] text-[var(--ink-2)] mt-0.5">
                  {selectedStage.description}
                </p>
              </div>

              {/* Checks in this stage */}
              {selectedStage.checks && selectedStage.checks.length > 0 ? (
                <div className="space-y-3">
                  <span className="font-heading font-semibold text-[11px] uppercase tracking-[0.08em] text-[var(--ink-3)] block">
                    Automated Checks ({selectedStage.checks.length})
                  </span>
                  <div className="space-y-2.5 divide-y divide-[var(--line)]">
                    {selectedStage.checks.map((chk) => (
                      <div key={chk.check_id} className="pt-2.5 first:pt-0 space-y-1">
                        <div className="flex items-start gap-2.5 text-[14px]">
                          <div className="mt-0.5">
                            <OutcomeIcon outcome={chk.outcome} severity={chk.severity} size={15} />
                          </div>
                          <div className="flex-1">
                            <div className="flex items-center gap-2">
                              <span className="font-semibold text-[var(--ink)]">{chk.name}</span>
                              <span className="font-mono text-[11px] text-[var(--ink-3)]">
                                ({chk.check_id})
                              </span>
                            </div>
                            <p className="font-sans text-[13px] text-[var(--ink-2)] mt-0.5 m-0">
                              {chk.message}
                            </p>
                          </div>
                        </div>

                        {chk.evidence && Object.keys(chk.evidence).length > 0 && (
                          <div className="pl-6 pt-1">
                            <Disclosure label="Show evidence" data={chk.evidence} />
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <p className="text-[13px] text-[var(--ink-3)]">
                  {selectedStage.status === "PENDING"
                    ? "Stage has not executed yet."
                    : "No specific policy checks configured for this stage."}
                </p>
              )}

              {/* Stage-specific output view */}
              <StageOutputView
                stage={selectedStage}
                run={run}
                onSwitchTab={(t) => setActiveTab(t)}
              />
            </div>
          )}

          {/* TAB 2: EXTRACTED DATA */}
          {activeTab === "extracted" && (
            <div className="space-y-6">
              {run.result?.normalized || run.result?.extraction ? (
                <>
                  <div>
                    <h2 className="font-heading font-semibold text-[18px] text-[var(--ink)] mb-2">
                      Extracted Fields & Confidence
                    </h2>
                    <div className="overflow-x-auto border border-[var(--line)] rounded-[8px]">
                      <table className="w-full text-left text-[13px]">
                        <thead className="bg-[var(--surface-sunken)] border-b border-[var(--line)]">
                          <tr>
                            <th className="py-2.5 px-3 font-heading font-semibold text-[11px] uppercase text-[var(--ink-3)]">
                              Field
                            </th>
                            <th className="py-2.5 px-3 font-heading font-semibold text-[11px] uppercase text-[var(--ink-3)]">
                              Value
                            </th>
                            <th className="py-2.5 px-3 font-heading font-semibold text-[11px] uppercase text-[var(--ink-3)] w-[160px]">
                              Confidence
                            </th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-[var(--line)]">
                          {Object.entries((run.result.normalized as any) || {}).map(
                            ([k, v]: [string, any]) => {
                              if (k === "line_items" || typeof v === "object") return null;
                              return (
                                <tr key={k}>
                                  <td className="py-2 px-3 font-heading font-medium text-[12px] uppercase text-[var(--ink-2)]">
                                    {k.replace(/_/g, " ")}
                                  </td>
                                  <td className="py-2 px-3 font-mono text-[var(--ink)]">
                                    {String(v ?? "—")}
                                  </td>
                                  <td className="py-2 px-3">
                                    <div className="flex items-center gap-2">
                                      <div className="w-[40px] h-[5px] bg-[var(--line)] rounded-full overflow-hidden">
                                        <div
                                          className="h-full bg-[var(--ink)]"
                                          style={{ width: "95%" }}
                                        />
                                      </div>
                                      <span className="font-mono text-[11px] text-[var(--ink-3)]">
                                        95%
                                      </span>
                                    </div>
                                  </td>
                                </tr>
                              );
                            }
                          )}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  {/* Line Items Table */}
                  {((run.result.normalized as any)?.line_items as any[]) && (
                    <div>
                      <h3 className="font-heading font-semibold text-[15px] text-[var(--ink)] mb-2">
                        Invoice Line Items
                      </h3>
                      <div className="overflow-x-auto border border-[var(--line)] rounded-[8px]">
                        <table className="w-full text-left text-[13px]">
                          <thead className="bg-[var(--surface-sunken)] border-b border-[var(--line)]">
                            <tr>
                              <th className="py-2 px-3 font-heading font-semibold text-[11px] uppercase text-[var(--ink-3)]">
                                Description
                              </th>
                              <th className="py-2 px-3 font-heading font-semibold text-[11px] uppercase text-[var(--ink-3)]">
                                HSN
                              </th>
                              <th className="py-2 px-3 font-heading font-semibold text-[11px] uppercase text-[var(--ink-3)] text-right">
                                Qty
                              </th>
                              <th className="py-2 px-3 font-heading font-semibold text-[11px] uppercase text-[var(--ink-3)]">
                                UOM
                              </th>
                              <th className="py-2 px-3 font-heading font-semibold text-[11px] uppercase text-[var(--ink-3)] text-right">
                                Rate
                              </th>
                              <th className="py-2 px-3 font-heading font-semibold text-[11px] uppercase text-[var(--ink-3)] text-right">
                                GST %
                              </th>
                              <th className="py-2 px-3 font-heading font-semibold text-[11px] uppercase text-[var(--ink-3)] text-right">
                                Amount
                              </th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-[var(--line)] font-mono">
                            {((run.result.normalized as any).line_items as any[]).map(
                              (item, i) => (
                                <tr key={i}>
                                  <td className="py-2 px-3 font-sans font-medium text-[var(--ink)]">
                                    {item.description}
                                  </td>
                                  <td className="py-2 px-3 text-[var(--ink-2)]">
                                    {item.hsn_sac || "—"}
                                  </td>
                                  <td className="py-2 px-3 text-right">{item.quantity}</td>
                                  <td className="py-2 px-3 text-[var(--ink-2)]">{item.uom}</td>
                                  <td className="py-2 px-3 text-right">
                                    <Money amount={item.unit_price} />
                                  </td>
                                  <td className="py-2 px-3 text-right">{item.tax_rate ?? "18"}%</td>
                                  <td className="py-2 px-3 text-right font-semibold">
                                    <Money amount={item.total_amount} />
                                  </td>
                                </tr>
                              )
                            )}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  <div className="text-[12px] text-[var(--ink-3)] font-mono">
                    Method: {run.extraction_method || "Text layer"} · gemini-3.5-flash-lite ·{" "}
                    {run.use_cache ? "cached" : "live"}
                  </div>
                </>
              ) : (
                <div className="text-[14px] text-[var(--ink-3)]">
                  Extraction not yet executed for this run.
                </div>
              )}
            </div>
          )}

          {/* TAB 3: EVENT LOG */}
          {activeTab === "events" && (
            <div
              className="bg-[var(--surface-sunken)] border border-[var(--line)] rounded-[8px] p-4 max-h-[460px] overflow-y-auto space-y-1.5 font-mono text-[12px] leading-[18px]"
              onScroll={() => {
                userScrolledLogRef.current = true;
              }}
            >
              {liveEventLog.length === 0 ? (
                <div className="text-[var(--ink-3)]">Waiting for execution events...</div>
              ) : (
                liveEventLog.map((ev, i) => (
                  <div key={i} className="flex items-start gap-3">
                    <span className="text-[var(--ink-3)] shrink-0">{ev.time}</span>
                    <span className="font-semibold text-[var(--ink)] shrink-0">{ev.type}</span>
                    {ev.stageKey && <span className="text-[var(--review)]">{ev.stageKey}</span>}
                    {ev.status && <span className="text-[var(--approve)]">{ev.status}</span>}
                    {ev.durationMs !== undefined && (
                      <span className="text-[var(--ink-3)]">{ev.durationMs}ms</span>
                    )}
                    {ev.message && <span className="text-[var(--ink-2)]">{ev.message}</span>}
                  </div>
                ))
              )}
              <div ref={eventLogEndRef} />
            </div>
          )}
        </div>
      </div>

      {/* 4. Document Drawer */}
      {drawerOpen && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex justify-end bg-[rgba(17,17,17,0.32)] backdrop-blur-[1px] animate-in fade-in duration-150"
          onClick={(e) => {
            if (e.target === e.currentTarget) setDrawerOpen(false);
          }}
        >
          <div className="w-full max-w-[560px] h-full bg-[var(--surface)] shadow-[var(--shadow-2)] border-l border-[var(--line)] flex flex-col animate-in slide-in-from-right duration-200">
            {/* Drawer Header */}
            <div className="p-4 border-b border-[var(--line)] flex items-center justify-between">
              <div>
                <h3 className="font-heading font-semibold text-[16px] text-[var(--ink)]">
                  {run.document?.filename || "Invoice Document"}
                </h3>
                <span className="font-sans text-[12px] text-[var(--ink-3)]">
                  {run.document?.page_count ?? 1} page(s) · {run.document?.has_text_layer ? "Text PDF" : "Scanned"}
                </span>
              </div>
              <button
                type="button"
                onClick={() => setDrawerOpen(false)}
                className="text-[var(--ink-3)] hover:text-[var(--ink)] p-1 rounded hover:bg-[var(--surface-sunken)] cursor-pointer"
              >
                <X size={18} strokeWidth={1.5} />
              </button>
            </div>

            {/* Drawer Body: Rendered page images */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-[var(--surface-sunken)]">
              {Array.from({ length: run.document?.page_count || 1 }).map((_, pIdx) => {
                const pageNum = pIdx + 1;
                return (
                  <div
                    key={pageNum}
                    className="bg-[var(--surface)] border border-[var(--line)] rounded-[8px] p-2 shadow-sm"
                  >
                    <div className="text-[11px] font-mono text-[var(--ink-3)] mb-1 px-1">
                      Page {pageNum}
                    </div>
                    <img
                      src={api.getRunPageUrl(run.id, pageNum, 110)}
                      alt={`Invoice page ${pageNum}`}
                      className="w-full h-auto rounded border border-[var(--line)]"
                      loading="lazy"
                    />
                  </div>
                );
              })}
            </div>

            {/* Drawer Footer */}
            <div className="p-4 border-t border-[var(--line)] bg-[var(--surface)] flex items-center justify-between">
              <a
                href={api.getRunDocumentUrl(run.id)}
                target="_blank"
                rel="noreferrer"
                className="text-[13px] font-sans font-medium text-[var(--ink)] flex items-center gap-1.5 underline hover:opacity-80"
              >
                <span>Open original file</span>
                <ExternalLink size={14} strokeWidth={1.5} />
              </a>
              <Button variant="secondary" size="sm" onClick={() => setDrawerOpen(false)}>
                Close
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* 5. Review Dialog */}
      {reviewAction && (
        <Dialog
          open={Boolean(reviewAction)}
          onClose={() => setReviewAction(null)}
          title={reviewAction === "approve" ? "Authorize AP Payment" : "Reject Invoice"}
          description="Record an audit note justifying your human override."
        >
          <div className="space-y-4 pt-2">
            <div>
              <label className="font-heading font-semibold text-[11px] uppercase tracking-[0.08em] text-[var(--ink-3)] block mb-1">
                Audit Note (required, min 5 characters)
              </label>
              <textarea
                rows={3}
                value={reviewNote}
                onChange={(e) => setReviewNote(e.target.value)}
                placeholder="Reason for decision..."
                className="w-full p-2.5 rounded-[8px] border border-[var(--line-strong)] bg-[var(--surface-sunken)] text-[14px] font-sans focus:outline-none focus:border-[var(--ink)]"
              />
            </div>

            <div>
              <label className="font-heading font-semibold text-[11px] uppercase tracking-[0.08em] text-[var(--ink-3)] block mb-1">
                Reviewer Name
              </label>
              <input
                type="text"
                value={reviewerName}
                onChange={(e) => setReviewerName(e.target.value)}
                className="w-full p-2 rounded-[8px] border border-[var(--line-strong)] bg-[var(--surface-sunken)] text-[14px] font-sans focus:outline-none focus:border-[var(--ink)]"
              />
            </div>

            {run.decision === "HOLD" && (
              <div className="p-3 bg-[var(--hold-tint)] border border-[var(--hold-line)] rounded-[8px]">
                <label className="flex items-start gap-2.5 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={bankVerified}
                    onChange={(e) => setBankVerified(e.target.checked)}
                    className="mt-1 w-4 h-4 text-[var(--ink)] accent-[var(--ink)]"
                  />
                  <span className="font-sans text-[13px] text-[var(--hold)] font-semibold">
                    I confirmed the bank change by calling the phone number in the vendor master
                    (not the invoice).
                  </span>
                </label>
              </div>
            )}

            <div className="flex justify-end gap-3 pt-3 border-t border-[var(--line)]">
              <Button variant="ghost" onClick={() => setReviewAction(null)}>
                Cancel
              </Button>
              <Button
                variant={reviewAction === "approve" ? "primary" : "danger"}
                loading={submittingReview}
                onClick={handleReviewSubmit}
              >
                {reviewAction === "approve" ? "Confirm Approval" : "Confirm Rejection"}
              </Button>
            </div>
          </div>
        </Dialog>
      )}

      {/* 6. Vendor Email Draft Dialog */}
      {emailModalOpen && decisionObj?.vendor_email && (
        <Dialog
          open={emailModalOpen}
          onClose={() => setEmailModalOpen(false)}
          title="Vendor Email Draft"
          description="Pre-drafted response addressing the specific validation flags."
          width="580px"
        >
          <div className="space-y-4 pt-2">
            <div>
              <label className="font-heading font-semibold text-[11px] uppercase tracking-[0.08em] text-[var(--ink-3)] block mb-1">
                Subject
              </label>
              <div className="p-2.5 bg-[var(--surface-sunken)] border border-[var(--line)] rounded-[8px] font-sans text-[14px] text-[var(--ink)] font-medium">
                {decisionObj.vendor_email.subject}
              </div>
            </div>

            <div>
              <label className="font-heading font-semibold text-[11px] uppercase tracking-[0.08em] text-[var(--ink-3)] block mb-1">
                Body
              </label>
              <div className="p-3 bg-[var(--surface-sunken)] border border-[var(--line)] rounded-[8px] font-sans text-[14px] leading-[22px] text-[var(--ink)] whitespace-pre-wrap max-h-[300px] overflow-y-auto">
                {decisionObj.vendor_email.body}
              </div>
            </div>

            <div className="flex justify-between items-center pt-3 border-t border-[var(--line)]">
              <Button
                variant="secondary"
                size="sm"
                icon={copiedEmail ? <CheckIcon size={14} /> : <Copy size={14} />}
                onClick={() => handleCopyEmail(decisionObj.vendor_email!.body)}
              >
                {copiedEmail ? "Copied" : "Copy email text"}
              </Button>
              <Button variant="primary" size="sm" onClick={() => setEmailModalOpen(false)}>
                Done
              </Button>
            </div>
          </div>
        </Dialog>
      )}
    </div>
  );
};
