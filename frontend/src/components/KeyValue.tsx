import React from "react";

export interface KeyValueProps {
  label: string;
  value: React.ReactNode;
  mono?: boolean;
  size?: "default" | "lg";
  className?: string;
}

export const KeyValue: React.FC<KeyValueProps> = ({
  label,
  value,
  mono = false,
  size = "default",
  className = "",
}) => {
  return (
    <div className={`flex flex-col gap-1 ${className}`}>
      <span className="font-heading font-semibold text-[11px] leading-[16px] uppercase tracking-[0.08em] text-[var(--ink-3)] select-none">
        {label}
      </span>
      <div
        className={`${
          mono ? "font-mono tabular" : "font-sans"
        } ${
          size === "lg"
            ? "text-[20px] leading-[28px] font-medium text-[var(--ink)]"
            : "text-[15px] leading-[24px] text-[var(--ink)]"
        }`}
      >
        {value ?? "—"}
      </div>
    </div>
  );
};
