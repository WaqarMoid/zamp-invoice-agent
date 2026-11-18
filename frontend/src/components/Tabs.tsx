import React from "react";

export interface TabItem {
  id: string;
  label: string;
  count?: number;
}

export interface TabsProps {
  tabs: TabItem[];
  activeTab: string;
  onChange: (id: string) => void;
  className?: string;
}

export const Tabs: React.FC<TabsProps> = ({ tabs, activeTab, onChange, className = "" }) => {
  return (
    <div
      role="tablist"
      className={`flex items-center gap-6 border-b border-[var(--line)] ${className}`}
    >
      {tabs.map((tab) => {
        const isActive = tab.id === activeTab;
        return (
          <button
            key={tab.id}
            role="tab"
            aria-selected={isActive}
            onClick={() => onChange(tab.id)}
            className={`h-[40px] relative font-sans font-medium text-[15px] select-none transition-colors cursor-pointer flex items-center gap-2 focus-visible:outline-2 focus-visible:outline-[var(--focus)] focus-visible:outline-offset-2 ${
              isActive ? "text-[var(--ink)] font-semibold" : "text-[var(--ink-3)] hover:text-[var(--ink)]"
            }`}
          >
            <span>{tab.label}</span>
            {tab.count !== undefined && (
              <span
                className={`font-mono tabular text-[12px] px-1.5 py-0.2 rounded-full ${
                  isActive
                    ? "bg-[var(--surface-sunken)] text-[var(--ink)] border border-[var(--line)]"
                    : "text-[var(--ink-3)]"
                }`}
              >
                {tab.count}
              </span>
            )}
            {isActive && (
              <span className="absolute bottom-[-1px] left-0 right-0 h-[2px] bg-[var(--ink)]" />
            )}
          </button>
        );
      })}
    </div>
  );
};
