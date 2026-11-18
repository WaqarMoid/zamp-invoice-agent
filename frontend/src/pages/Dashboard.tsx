import React, { useMemo } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Plus, Search } from "lucide-react";
import { api } from "../lib/api";
import { formatCompactMoney, formatDuration, formatRelativeTime } from "../lib/format";
import type { Decision, RunSummary } from "../lib/types";
import { Button } from "../components/Button";
import { PageHeader } from "../components/PageHeader";
import { DecisionBadge } from "../components/DecisionBadge";
import { Money } from "../components/Money";
import { DataTable, Column } from "../components/DataTable";
import { Skeleton } from "../components/Skeleton";
import { EmptyState } from "../components/EmptyState";

function cleanHeadlineReason(headline: string | null | undefined): string {
  if (!headline) return "—";
  // Strip label prefix like "Approved for payment. ", "Needs review: ", "Payment on hold: ", "Rejected: "
  const colonIdx = headline.indexOf(": ");
  if (colonIdx !== -1) {
    return headline.slice(colonIdx + 2);
  }
  return headline;
}

export const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const currentDecision = (searchParams.get("decision") as Decision) || undefined;
  const currentQuery = searchParams.get("q") || "";

  // 1. Fetch Stats
  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ["stats"],
    queryFn: () => api.getStats(),
    refetchInterval: (query) => {
      // If there are runs running, poll faster
      const data = query.state.data;
      if (data && data.total_runs > data.completed_runs) {
        return 2000;
      }
      return 15000;
    },
  });

  // 2. Fetch Runs
  const { data: runsData, isLoading: runsLoading } = useQuery({
    queryKey: ["runs", currentDecision, currentQuery],
    queryFn: () =>
      api.getRuns({
        decision: currentDecision,
        q: currentQuery.trim() || undefined,
        limit: 100,
      }),
    refetchInterval: (query) => {
      const items = query.state.data?.items;
      const hasActive = items?.some((r) => r.status === "RUNNING" || r.status === "QUEUED");
      return hasActive ? 2000 : 15000;
    },
  });

  const runs = runsData?.items || [];

  const handleDecisionFilter = (d: Decision | "ALL") => {
    const next = new URLSearchParams(searchParams);
    if (d === "ALL") {
      next.delete("decision");
    } else {
      next.set("decision", d);
    }
    setSearchParams(next);
  };

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    const next = new URLSearchParams(searchParams);
    if (!val.trim()) {
      next.delete("q");
    } else {
      next.set("q", val);
    }
    setSearchParams(next);
  };

  // Filter tab counts
  const counts = useMemo(() => {
    const byDec = stats?.by_decision || { APPROVE: 0, REVIEW: 0, HOLD: 0, REJECT: 0 };
    return {
      ALL: stats?.total_runs ?? 0,
      APPROVE: byDec.APPROVE ?? 0,
      REVIEW: byDec.REVIEW ?? 0,
      HOLD: byDec.HOLD ?? 0,
      REJECT: byDec.REJECT ?? 0,
    };
  }, [stats]);

  // Table Columns
  const columns: Column<RunSummary>[] = [
    {
      key: "received",
      header: "Received",
      width: "120px",
      render: (r) => (
        <span title={r.created_at} className="text-[13px] text-[var(--ink-2)]">
          {formatRelativeTime(r.created_at)}
        </span>
      ),
    },
    {
      key: "invoice",
      header: "Invoice",
      width: "160px",
      render: (r) => (
        <div className="flex flex-col">
          <span className="font-mono text-[13px] font-medium text-[var(--ink)]">
            {r.invoice_number || "—"}
          </span>
          <span className="font-sans text-[11px] text-[var(--ink-3)] truncate max-w-[140px]">
            {r.filename}
          </span>
        </div>
      ),
    },
    {
      key: "vendor",
      header: "Vendor",
      render: (r) => (
        <span className="font-sans text-[14px] text-[var(--ink)] font-medium">
          {r.vendor_name || "—"}
        </span>
      ),
    },
    {
      key: "po",
      header: "PO",
      width: "140px",
      render: (r) => (
        <div className="flex items-center gap-1.5">
          <span className="font-mono text-[13px] text-[var(--ink-2)]">
            {r.po_number || "—"}
          </span>
          {r.po_method === "inferred" && (
            <span className="text-[10px] font-mono px-1 py-0.2 rounded border border-[var(--line-strong)] text-[var(--ink-3)] uppercase tracking-wide">
              inferred
            </span>
          )}
        </div>
      ),
    },
    {
      key: "amount",
      header: "Amount",
      align: "right",
      width: "120px",
      render: (r) => (
        <Money
          amount={r.grand_total ? r.grand_total.replace(/[^\d.]/g, "") : null}
          className="text-[14px] text-[var(--ink)]"
        />
      ),
    },
    {
      key: "decision",
      header: "Decision",
      width: "130px",
      render: (r) => (
        <DecisionBadge
          decision={r.decision}
          status={r.status}
          currentStageLabel={r.current_stage}
          size="sm"
        />
      ),
    },
    {
      key: "reason",
      header: "Reason",
      render: (r) => (
        <div
          title={r.headline || ""}
          className="font-sans text-[13px] text-[var(--ink-2)] truncate max-w-[320px]"
        >
          {cleanHeadlineReason(r.headline)}
        </div>
      ),
    },
    {
      key: "time",
      header: "Time",
      align: "right",
      width: "80px",
      render: (r) => (
        <span className="font-mono text-[13px] text-[var(--ink-3)]">
          {formatDuration(r.duration_ms)}
        </span>
      ),
    },
    {
      key: "review",
      header: "Review",
      width: "120px",
      render: (r) => {
        if (r.review_status === "PENDING") {
          return (
            <span className="font-sans text-[13px] font-semibold text-[var(--review)]">
              Pending
            </span>
          );
        }
        if (r.review_status === "APPROVED") {
          return <span className="font-sans text-[12px] text-[var(--approve)]">Approved by AP</span>;
        }
        if (r.review_status === "REJECTED") {
          return <span className="font-sans text-[12px] text-[var(--reject)]">Rejected by AP</span>;
        }
        return <span className="text-[var(--ink-3)]">·</span>;
      },
    },
  ];

  return (
    <div className="space-y-8">
      {/* 1. Header */}
      <PageHeader
        title="Invoices"
        description="Every invoice processed, with the decision and the reason."
        actions={
          <Button
            variant="primary"
            icon={<Plus size={16} strokeWidth={1.5} />}
            onClick={() => navigate("/new")}
          >
            Process invoice
          </Button>
        }
      />

      {/* 2. KPI Strip */}
      {statsLoading ? (
        <div className="bg-[var(--surface)] border border-[var(--line)] rounded-[10px] p-6 grid grid-cols-2 sm:grid-cols-5 gap-6">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="space-y-2">
              <Skeleton width="60px" height="12px" />
              <Skeleton width="90px" height="28px" />
              <Skeleton width="110px" height="14px" />
            </div>
          ))}
        </div>
      ) : stats ? (
        <div className="bg-[var(--surface)] border border-[var(--line)] rounded-[10px] shadow-[var(--shadow-1)] grid grid-cols-1 sm:grid-cols-5 divide-y sm:divide-y-0 sm:divide-x divide-[var(--line)] overflow-hidden">
          {/* PROCESSED */}
          <div className="p-5 flex flex-col gap-1">
            <span className="font-heading font-semibold text-[11px] leading-[16px] uppercase tracking-[0.08em] text-[var(--ink-3)] select-none">
              PROCESSED
            </span>
            <div className="font-mono tabular text-[20px] leading-[28px] font-medium text-[var(--ink)]">
              {stats.completed_runs}
            </div>
            <span className="font-sans text-[13px] leading-[20px] text-[var(--ink-2)]">
              {stats.total_runs > stats.completed_runs
                ? `${stats.total_runs - stats.completed_runs} running`
                : "all complete"}
            </span>
          </div>

          {/* AUTO-APPROVED */}
          <div className="p-5 flex flex-col gap-1">
            <span className="font-heading font-semibold text-[11px] leading-[16px] uppercase tracking-[0.08em] text-[var(--ink-3)] select-none">
              AUTO-APPROVED
            </span>
            <div className="font-mono tabular text-[20px] leading-[28px] font-medium text-[var(--ink)]">
              {(stats.auto_approval_rate * 100).toFixed(0)}%
            </div>
            <span className="font-sans text-[13px] leading-[20px] text-[var(--ink-2)]">
              {stats.by_decision?.APPROVE || 0} of {stats.completed_runs}
            </span>
          </div>

          {/* AWAITING ACTION */}
          <div className="p-5 flex flex-col gap-1">
            <span className="font-heading font-semibold text-[11px] leading-[16px] uppercase tracking-[0.08em] text-[var(--ink-3)] select-none">
              AWAITING ACTION
            </span>
            <div
              className={`font-mono tabular text-[20px] leading-[28px] font-medium ${
                stats.awaiting_action > 0 ? "text-[var(--review)]" : "text-[var(--ink)]"
              }`}
            >
              {stats.awaiting_action}
            </div>
            <span className="font-sans text-[13px] leading-[20px] text-[var(--ink-2)]">
              needs review or on hold
            </span>
          </div>

          {/* VALUE PROCESSED */}
          <div className="p-5 flex flex-col gap-1">
            <span className="font-heading font-semibold text-[11px] leading-[16px] uppercase tracking-[0.08em] text-[var(--ink-3)] select-none">
              VALUE PROCESSED
            </span>
            <div className="font-mono tabular text-[20px] leading-[28px] font-medium text-[var(--ink)]">
              {formatCompactMoney(stats.value_processed ? parseFloat(stats.value_processed.replace(/[^\d.]/g, "")) : 0)}
            </div>
            <span className="font-sans text-[13px] leading-[20px] text-[var(--ink-2)]">
              across all invoices
            </span>
          </div>

          {/* MEDIAN TIME */}
          <div className="p-5 flex flex-col gap-1">
            <span className="font-heading font-semibold text-[11px] leading-[16px] uppercase tracking-[0.08em] text-[var(--ink-3)] select-none">
              MEDIAN TIME
            </span>
            <div className="font-mono tabular text-[20px] leading-[28px] font-medium text-[var(--ink)]">
              {stats.median_duration_ms ? `${(stats.median_duration_ms / 1000).toFixed(1)} s` : "—"}
            </div>
            <span className="font-sans text-[13px] leading-[20px] text-[var(--ink-2)]">
              upload to decision
            </span>
          </div>
        </div>
      ) : null}

      {/* 3. Filter Row */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        {/* Segmented Filter Control */}
        <div className="inline-flex items-center gap-1 p-1 bg-[var(--surface)] border border-[var(--line)] rounded-[8px] select-none text-[13px]">
          {[
            { id: "ALL", label: "All" },
            { id: "APPROVE", label: "Approved" },
            { id: "REVIEW", label: "Needs review" },
            { id: "HOLD", label: "On hold" },
            { id: "REJECT", label: "Rejected" },
          ].map((tab) => {
            const isSelected =
              tab.id === "ALL" ? !currentDecision : currentDecision === tab.id;
            const count = counts[tab.id as keyof typeof counts];

            return (
              <button
                key={tab.id}
                onClick={() => handleDecisionFilter(tab.id as any)}
                className={`px-3 py-1 rounded-[6px] font-medium transition-colors cursor-pointer flex items-center gap-1.5 ${
                  isSelected
                    ? "bg-[var(--ink)] text-white"
                    : "text-[var(--ink-2)] hover:text-[var(--ink)] hover:bg-[var(--surface-sunken)]"
                }`}
              >
                <span>{tab.label}</span>
                <span
                  className={`font-mono text-[11px] ${
                    isSelected ? "text-white opacity-80" : "text-[var(--ink-3)]"
                  }`}
                >
                  {count}
                </span>
              </button>
            );
          })}
        </div>

        {/* Search Input */}
        <div className="relative w-full sm:w-[240px]">
          <Search
            size={16}
            strokeWidth={1.5}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--ink-3)] pointer-events-none"
          />
          <input
            type="text"
            value={currentQuery}
            onChange={handleSearchChange}
            placeholder="Vendor, invoice or PO"
            className="w-full pl-9 pr-3 py-1.5 h-[36px] text-[13px] font-sans rounded-[8px] border border-[var(--line-strong)] bg-[var(--surface)] text-[var(--ink)] placeholder:text-[var(--ink-3)] focus:outline-none focus:border-[var(--ink)] transition-colors"
          />
        </div>
      </div>

      {/* 4. Runs Table / Empty / Loading */}
      {runsLoading ? (
        <div className="bg-[var(--surface)] border border-[var(--line)] rounded-[10px] p-6 space-y-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="flex items-center justify-between gap-4 py-2 border-b border-[var(--line)] last:border-b-0">
              <Skeleton width="100px" height="16px" />
              <Skeleton width="140px" height="16px" />
              <Skeleton width="180px" height="16px" />
              <Skeleton width="90px" height="16px" />
              <Skeleton width="110px" height="24px" />
            </div>
          ))}
        </div>
      ) : runs.length === 0 ? (
        stats && stats.total_runs === 0 ? (
          <div className="bg-[var(--surface)] border border-[var(--line)] rounded-[10px] shadow-[var(--shadow-1)]">
            <EmptyState
              title="No invoices processed yet"
              description="Run one of the sample invoices to see the pipeline work end to end."
              action={
                <Button variant="primary" onClick={() => navigate("/new")}>
                  Process invoice
                </Button>
              }
            />
          </div>
        ) : (
          <div className="bg-[var(--surface)] border border-[var(--line)] rounded-[10px] shadow-[var(--shadow-1)]">
            <EmptyState
              title="No matching invoices found"
              description="No invoice runs match your active search terms or decision filter."
              action={
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => setSearchParams(new URLSearchParams())}
                >
                  Clear filters
                </Button>
              }
            />
          </div>
        )
      ) : (
        <DataTable
          columns={columns}
          data={runs}
          keyExtractor={(r) => r.id}
          onRowClick={(r) => navigate(`/runs/${r.id}`)}
        />
      )}
    </div>
  );
};
