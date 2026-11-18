import React from "react";
import { Link } from "react-router-dom";
import { Button } from "../components/Button";

export const NotFoundPage: React.FC = () => {
  return (
    <div className="py-20 text-center max-w-md mx-auto space-y-4">
      <span className="font-heading font-semibold text-[11px] uppercase tracking-[0.08em] text-[var(--ink-3)] select-none">
        404 ERROR
      </span>
      <h1 className="font-heading font-bold text-[32px] leading-[40px] text-[var(--ink)]">
        Page not found
      </h1>
      <p className="font-sans text-[15px] leading-[24px] text-[var(--ink-2)]">
        The page you are looking for does not exist or has been moved.
      </p>
      <div className="pt-2">
        <Link to="/">
          <Button variant="primary">Return to Invoices</Button>
        </Link>
      </div>
    </div>
  );
};
