import React from "react";
import { AlertTriangle, Check, Loader2, ShieldAlert, X, XOctagon } from "lucide-react";
import type { Severity, StageStatus } from "../lib/types";

export interface StageMarkerProps {
  position: number;
  status: StageStatus;
  highestSeverity?: Severity | null;
  className?: string;
}

export const StageMarker: React.FC<StageMarkerProps> = ({
  position,
  status,
  highestSeverity,
  className = "",
}) => {
  const base =
    "w-6 h-6 rounded-full flex items-center justify-center shrink-0 transition-transform duration-200 select-none";

  if (status === "RUNNING") {
    return (
      <div className={`${base} bg-[var(--surface)] border border-[var(--ink)] ${className}`}>
        <Loader2 className="w-3.5 h-3.5 animate-spin text-[var(--ink)]" strokeWidth={1.5} />
      </div>
    );
  }

  if (status === "PASSED") {
    return (
      <div
        className={`${base} bg-[var(--approve-tint)] border border-[var(--approve-line)] text-[var(--approve)] ${className}`}
      >
        <Check className="w-3.5 h-3.5" strokeWidth={1.5} />
      </div>
    );
  }

  if (status === "FLAGGED") {
    if (highestSeverity === "HOLD") {
      return (
        <div
          className={`${base} bg-[var(--hold-tint)] border border-[var(--hold-line)] text-[var(--hold)] ${className}`}
        >
          <ShieldAlert className="w-3.5 h-3.5" strokeWidth={1.5} />
        </div>
      );
    }
    if (highestSeverity === "REJECT") {
      return (
        <div
          className={`${base} bg-[var(--reject-tint)] border border-[var(--reject-line)] text-[var(--reject)] ${className}`}
        >
          <XOctagon className="w-3.5 h-3.5" strokeWidth={1.5} />
        </div>
      );
    }
    return (
      <div
        className={`${base} bg-[var(--review-tint)] border border-[var(--review-line)] text-[var(--review)] ${className}`}
      >
        <AlertTriangle className="w-3.5 h-3.5" strokeWidth={1.5} />
      </div>
    );
  }

  if (status === "FAILED") {
    return (
      <div
        className={`${base} bg-[var(--reject-tint)] border border-[var(--reject-line)] text-[var(--reject)] ${className}`}
      >
        <X className="w-3.5 h-3.5" strokeWidth={1.5} />
      </div>
    );
  }

  if (status === "SKIPPED") {
    return (
      <div
        className={`${base} border border-dashed border-[var(--line-strong)] text-[var(--ink-3)] font-mono text-[11px] ${className}`}
      >
        –
      </div>
    );
  }

  // PENDING (default)
  return (
    <div
      className={`${base} border border-[var(--line-strong)] bg-[var(--surface)] text-[var(--ink-3)] font-mono text-[11px] ${className}`}
    >
      {position}
    </div>
  );
};
