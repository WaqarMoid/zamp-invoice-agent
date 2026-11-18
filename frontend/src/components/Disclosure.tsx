import React, { useState } from "react";
import { ChevronRight } from "lucide-react";

export interface DisclosureProps {
  label?: string;
  data: Record<string, unknown> | null | undefined;
  className?: string;
}

function formatEvidenceValue(val: unknown, depth = 0): string {
  if (val === null || val === undefined) return "null";
  if (typeof val === "boolean") return val ? "true" : "false";
  if (typeof val === "number" || typeof val === "string") return String(val);

  const indent = "  ".repeat(depth + 1);
  if (Array.isArray(val)) {
    if (val.length === 0) return "[]";
    return (
      "[\n" +
      val.map((item) => `${indent}- ${formatEvidenceValue(item, depth + 1)}`).join("\n") +
      "\n" +
      "  ".repeat(depth) +
      "]"
    );
  }

  if (typeof val === "object") {
    const entries = Object.entries(val as Record<string, unknown>);
    if (entries.length === 0) return "{}";
    return (
      "\n" +
      entries
        .map(([k, v]) => `${indent}${k}: ${formatEvidenceValue(v, depth + 1)}`)
        .join("\n")
    );
  }

  return String(val);
}

export const Disclosure: React.FC<DisclosureProps> = ({
  label = "Show evidence",
  data,
  className = "",
}) => {
  const [open, setOpen] = useState(false);

  if (!data || Object.keys(data).length === 0) {
    return null;
  }

  return (
    <div className={`text-[13px] ${className}`}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="inline-flex items-center gap-1 text-[var(--ink-3)] hover:text-[var(--ink)] cursor-pointer select-none font-sans font-medium transition-colors focus-visible:outline-2 focus-visible:outline-[var(--focus)]"
      >
        <ChevronRight
          className={`w-3.5 h-3.5 transition-transform duration-150 ${open ? "rotate-90" : ""}`}
          strokeWidth={1.5}
        />
        <span>{open ? "Hide evidence" : label}</span>
      </button>

      {open && (
        <div className="mt-2 p-3 bg-[var(--surface-sunken)] border border-[var(--line)] rounded-[8px] max-h-[280px] overflow-y-auto">
          <pre className="font-mono text-[12px] leading-[18px] text-[var(--ink-2)] whitespace-pre-wrap break-all m-0">
            {Object.entries(data).map(([k, v]) => (
              <div key={k} className="py-0.5">
                <span className="font-semibold text-[var(--ink)]">{k}:</span>{" "}
                <span>{formatEvidenceValue(v)}</span>
              </div>
            ))}
          </pre>
        </div>
      )}
    </div>
  );
};
