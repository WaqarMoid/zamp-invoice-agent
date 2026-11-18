import React from "react";

export interface EmptyStateProps {
  title: string;
  description: string;
  action?: React.ReactNode;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  description,
  action,
  className = "",
}) => {
  return (
    <div className={`p-8 text-left ${className}`}>
      <h3 className="font-heading font-semibold text-[16px] leading-[22px] text-[var(--ink)] mb-1">
        {title}
      </h3>
      <p className="font-sans text-[14px] leading-[22px] text-[var(--ink-2)] max-w-md mb-4">
        {description}
      </p>
      {action && <div>{action}</div>}
    </div>
  );
};
