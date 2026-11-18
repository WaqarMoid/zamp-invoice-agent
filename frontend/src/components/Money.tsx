import React from "react";
import { formatCompactMoney, formatMoney } from "../lib/format";

export interface MoneyProps {
  amount: number | string | null | undefined;
  compact?: boolean;
  className?: string;
}

export const Money: React.FC<MoneyProps> = ({ amount, compact = false, className = "" }) => {
  const formatted = compact ? formatCompactMoney(amount) : formatMoney(amount);

  return (
    <span className={`font-mono tabular whitespace-nowrap ${className}`}>
      {formatted}
    </span>
  );
};
