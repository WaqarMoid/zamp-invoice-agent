import React, { useEffect, useRef } from "react";
import { X } from "lucide-react";

export interface DialogProps {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  children: React.ReactNode;
  width?: string;
  className?: string;
}

export const Dialog: React.FC<DialogProps> = ({
  open,
  onClose,
  title,
  description,
  children,
  width = "480px",
  className = "",
}) => {
  const dialogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape" && open) {
        onClose();
      }
    }
    if (open) {
      document.addEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "hidden";
    }
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "";
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="dialog-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[rgba(17,17,17,0.32)] backdrop-blur-[1px] animate-in fade-in duration-150"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        ref={dialogRef}
        style={{ width }}
        className={`bg-[var(--surface)] border border-[var(--line)] rounded-[12px] p-6 shadow-[var(--shadow-2)] max-w-full max-h-[90vh] flex flex-col relative z-10 ${className}`}
      >
        <div className="flex items-start justify-between gap-4 mb-4">
          <div>
            <h2
              id="dialog-title"
              className="font-heading font-semibold text-[18px] leading-[26px] text-[var(--ink)]"
            >
              {title}
            </h2>
            {description && (
              <p className="font-sans text-[13px] leading-[20px] text-[var(--ink-2)] mt-1">
                {description}
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close dialog"
            className="text-[var(--ink-3)] hover:text-[var(--ink)] cursor-pointer p-1 rounded-[6px] hover:bg-[var(--surface-sunken)] transition-colors focus-visible:outline-2 focus-visible:outline-[var(--focus)]"
          >
            <X size={18} strokeWidth={1.5} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto">{children}</div>
      </div>
    </div>
  );
};
