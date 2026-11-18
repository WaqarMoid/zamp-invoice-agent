import React from "react";
import { CheckCircle2, Clock, Eye, Loader2, ShieldAlert, XCircle } from "lucide-react";
import type { Decision, RunStatus } from "../lib/types";

export interface DecisionBadgeProps {
  decision?: Decision | null;
  status?: RunStatus | null;
  currentStageLabel?: string | null;
  size?: "sm" | "md";
  className?: string;
}

export const DecisionBadge: React.FC<DecisionBadgeProps> = ({
  decision,
  status,
  currentStageLabel,
  size = "md",
  className = "",
}) => {
  const isRunning = status === "RUNNING";
  const isQueued = status === "QUEUED";

  const sizeStyles =
    size === "sm"
      ? "h-[20px] px-1.5 text-[11px] gap-1 rounded-[4px]"
      : "h-[24px] px-2 text-[13px] gap-1.5 rounded-[6px]";

  if (isRunning) {
    const label = currentStageLabel ? `Running · ${currentStageLabel}` : "Running";
    return (
      <span
        className={`inline-flex items-center font-sans font-semibold border border-[var(--ink)] bg-[var(--surface)] text-[var(--ink)] ${sizeStyles} ${className}`}
      >
        <Loader2 className="w-3.5 h-3.5 animate-spin text-[var(--ink)]" strokeWidth={1.5} />
        <span>{label}</span>
      </span>
    );
  }

  if (isQueued) {
    return (
      <span
        className={`inline-flex items-center font-sans font-semibold border border-[var(--line-strong)] bg-[var(--surface-sunken)] text-[var(--ink-2)] ${sizeStyles} ${className}`}
      >
        <Clock className="w-3.5 h-3.5 text-[var(--ink-2)]" strokeWidth={1.5} />
        <span>Queued</span>
      </span>
    );
  }

  if (!decision) {
    return (
      <span
        className={`inline-flex items-center font-sans font-semibold border border-[var(--line)] bg-[var(--surface-sunken)] text-[var(--ink-3)] ${sizeStyles} ${className}`}
      >
        <span>Pending</span>
      </span>
    );
  }

  const config = {
    APPROVE: {
      label: "Approved",
      icon: CheckCircle2,
      style: "bg-[var(--approve-tint)] text-[var(--approve)] border-[var(--approve-line)]",
    },
    REVIEW: {
      label: "Needs review",
      icon: Eye,
      style: "bg-[var(--review-tint)] text-[var(--review)] border-[var(--review-line)]",
    },
    HOLD: {
      label: "On hold",
      icon: ShieldAlert,
      style: "bg-[var(--hold-tint)] text-[var(--hold)] border-[var(--hold-line)]",
    },
    REJECT: {
      label: "Rejected",
      icon: XCircle,
      style: "bg-[var(--reject-tint)] text-[var(--reject)] border-[var(--reject-line)]",
    },
  }[decision];

  const Icon = config.icon;

  return (
    <span
      className={`inline-flex items-center font-sans font-semibold border ${config.style} ${sizeStyles} ${className}`}
    >
      <Icon className="w-3.5 h-3.5 shrink-0" strokeWidth={1.5} />
      <span>{config.label}</span>
    </span>
  );
};
