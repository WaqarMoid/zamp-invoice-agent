import React from "react";

export interface ConsumptionBarProps {
  billedPct: number;
  showLabel?: boolean;
  className?: string;
  width?: string;
}

export const ConsumptionBar: React.FC<ConsumptionBarProps> = ({
  billedPct,
  showLabel = true,
  className = "",
  width = "160px",
}) => {
  const safePct = Math.max(0, billedPct);
  const maxScale = Math.max(100, safePct);

  // Normal billed up to 100%
  const normalWidthPct = (Math.min(100, safePct) / maxScale) * 100;

  // Overflow above 100%
  const overflowWidthPct = safePct > 100 ? ((safePct - 100) / maxScale) * 100 : 0;

  return (
    <div className={`inline-flex items-center gap-3 ${className}`}>
      <div
        style={{ width }}
        className="h-[6px] rounded-full bg-[var(--line)] overflow-hidden flex relative shrink-0"
      >
        <div
          style={{ width: `${normalWidthPct}%` }}
          className="h-full bg-[var(--ink)] transition-all duration-300"
        />
        {overflowWidthPct > 0 && (
          <div
            style={{ width: `${overflowWidthPct}%` }}
            className="h-full bg-[var(--reject)] transition-all duration-300"
          />
        )}
      </div>
      {showLabel && (
        <span
          className={`font-mono tabular text-[13px] leading-[20px] whitespace-nowrap ${
            safePct > 100 ? "text-[var(--reject)] font-semibold" : "text-[var(--ink-2)]"
          }`}
        >
          {safePct.toFixed(1)}% billed
        </span>
      )}
    </div>
  );
};
