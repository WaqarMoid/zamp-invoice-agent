import React from "react";
import { AlertTriangle, Check, Info, MinusCircle, ShieldAlert, XOctagon } from "lucide-react";
import type { Outcome, Severity } from "../lib/types";

export interface OutcomeIconProps {
  outcome: Outcome;
  severity?: Severity | null;
  size?: number;
  className?: string;
}

export const OutcomeIcon: React.FC<OutcomeIconProps> = ({
  outcome,
  severity,
  size = 16,
  className = "",
}) => {
  if (outcome === "PASS") {
    return (
      <Check
        size={size}
        strokeWidth={1.5}
        className={`text-[var(--approve)] shrink-0 ${className}`}
        aria-label="Passed"
      />
    );
  }

  if (outcome === "INFO") {
    return (
      <Info
        size={size}
        strokeWidth={1.5}
        className={`text-[var(--ink-3)] shrink-0 ${className}`}
        aria-label="Info"
      />
    );
  }

  if (outcome === "SKIP") {
    return (
      <MinusCircle
        size={size}
        strokeWidth={1.5}
        className={`text-[var(--ink-3)] shrink-0 ${className}`}
        aria-label="Skipped"
      />
    );
  }

  // Outcome is FLAG
  if (severity === "HOLD") {
    return (
      <ShieldAlert
        size={size}
        strokeWidth={1.5}
        className={`text-[var(--hold)] shrink-0 ${className}`}
        aria-label="Hold flag"
      />
    );
  }

  if (severity === "REJECT") {
    return (
      <XOctagon
        size={size}
        strokeWidth={1.5}
        className={`text-[var(--reject)] shrink-0 ${className}`}
        aria-label="Reject flag"
      />
    );
  }

  // Default FLAG severity is REVIEW
  return (
    <AlertTriangle
      size={size}
      strokeWidth={1.5}
      className={`text-[var(--review)] shrink-0 ${className}`}
      aria-label="Review flag"
    />
  );
};
