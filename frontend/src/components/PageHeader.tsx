import React from "react";

export interface PageHeaderProps {
  title: React.ReactNode;
  description?: string;
  actions?: React.ReactNode;
  breadcrumb?: React.ReactNode;
  className?: string;
}

export const PageHeader: React.FC<PageHeaderProps> = ({
  title,
  description,
  actions,
  breadcrumb,
  className = "",
}) => {
  return (
    <div className={`mb-6 ${className}`}>
      {breadcrumb && <div className="mb-2 text-[13px] text-[var(--ink-3)]">{breadcrumb}</div>}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="font-heading font-bold text-[26px] leading-[32px] tracking-[-0.01em] text-[var(--ink)]">
            {title}
          </h1>
          {description && (
            <p className="font-sans text-[13px] leading-[20px] text-[var(--ink-2)] mt-1">
              {description}
            </p>
          )}
        </div>
        {actions && <div className="flex items-center gap-3 shrink-0">{actions}</div>}
      </div>
    </div>
  );
};
