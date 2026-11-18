import React from "react";
import { Loader2 } from "lucide-react";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "md" | "sm";
  icon?: React.ReactNode;
  loading?: boolean;
}

export const Button: React.FC<ButtonProps> = ({
  variant = "primary",
  size = "md",
  icon,
  loading = false,
  disabled,
  children,
  className = "",
  ...props
}) => {
  const baseStyles =
    "inline-flex items-center justify-center font-sans font-medium transition-colors select-none cursor-pointer disabled:cursor-not-allowed disabled:opacity-40 active:translate-y-[0.5px] focus-visible:outline-2 focus-visible:outline-[var(--focus)] focus-visible:outline-offset-2";

  const sizeStyles =
    size === "sm"
      ? "h-[32px] px-3 text-[13px] rounded-[6px] gap-2"
      : "h-[36px] px-[14px] text-[15px] rounded-[8px] gap-2";

  const variantStyles = {
    primary: "bg-[var(--ink)] text-white hover:bg-[#2A2A2A] border-0",
    secondary:
      "bg-[var(--surface)] text-[var(--ink)] border border-[var(--line-strong)] hover:bg-[var(--surface-sunken)]",
    ghost: "bg-transparent text-[var(--ink)] hover:bg-[var(--surface-sunken)] border-0",
    danger:
      "bg-transparent text-[var(--reject)] border border-[var(--reject-line)] hover:bg-[var(--reject-tint)]",
  }[variant];

  return (
    <button
      disabled={disabled || loading}
      className={`${baseStyles} ${sizeStyles} ${variantStyles} ${className}`}
      {...props}
    >
      {loading ? (
        <Loader2 className="w-4 h-4 animate-spin text-current" strokeWidth={1.5} />
      ) : (
        icon && <span className="inline-flex shrink-0">{icon}</span>
      )}
      <span>{children}</span>
    </button>
  );
};
