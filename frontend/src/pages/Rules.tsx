import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { api } from "../lib/api";
import { PageHeader } from "../components/PageHeader";
import { DecisionBadge } from "../components/DecisionBadge";
import { KeyValue } from "../components/KeyValue";
import { Button } from "../components/Button";
import { Dialog } from "../components/Dialog";
import { Skeleton } from "../components/Skeleton";
import { useToast } from "../components/Toast";

interface CheckCatalogueItem {
  id: string;
  name: string;
  stage: string;
  severities: ("REVIEW" | "HOLD" | "REJECT")[];
  description: string;
}

const CHECKS_CATALOGUE: CheckCatalogueItem[] = [
  { id: "C01", name: "Mandatory fields present", stage: "Normalize", severities: ["REJECT"], description: "Verifies invoice number, date, vendor name, and line items exist." },
  { id: "C02", name: "Field extraction confidence", stage: "Normalize", severities: ["REVIEW"], description: "Flags when any critical field confidence falls below 0.80." },
  { id: "C03", name: "Billed to Kestrel Foods", stage: "Normalize", severities: ["REJECT"], description: "Validates buyer legal name or GSTIN matches Kestrel Foods Pvt. Ltd." },
  { id: "C04", name: "Document arithmetic check", stage: "Normalize", severities: ["REJECT"], description: "Validates sum of lines equals subtotal, and subtotal + tax = total." },
  { id: "C05", name: "Vendor status active", stage: "Vendor", severities: ["REJECT"], description: "Confirms vendor exists in master and is not deactivated." },
  { id: "C06", name: "Vendor GSTIN verification", stage: "Vendor", severities: ["HOLD", "REJECT"], description: "Validates checksum, state code, and matches against vendor master." },
  { id: "C07", name: "Bank account verification", stage: "Vendor", severities: ["HOLD"], description: "Anti-fraud guard: flags any remittance account differing from master." },
  { id: "C08", name: "Invoice date sanity", stage: "Normalize", severities: ["REVIEW"], description: "Flags dates > 30 days in future or > 180 days in past." },
  { id: "C09", name: "Duplicate invoice check", stage: "Duplicates", severities: ["REJECT", "REVIEW"], description: "Flags exact duplicate (vendor+number) or same amount & date." },
  { id: "C10", name: "PO inferred match", stage: "PO Match", severities: ["REVIEW"], description: "Flags when PO number was not printed and had to be inferred." },
  { id: "C11", name: "Valid PO exists", stage: "PO Match", severities: ["REVIEW"], description: "Confirms referenced PO number exists in procurement database." },
  { id: "C12", name: "PO open status", stage: "PO Match", severities: ["REJECT"], description: "Rejects billing against closed or cancelled purchase orders." },
  { id: "C13", name: "Line items matched", stage: "PO Match", severities: ["REVIEW"], description: "Flags invoice lines that could not be paired to any PO line." },
  { id: "C14", name: "Unit price tolerance", stage: "Reconcile", severities: ["REVIEW"], description: "Checks unit price variance ≤ 1.0% or ₹1,000 (whichever is lower)." },
  { id: "C15", name: "Quantity & PO balance", stage: "Reconcile", severities: ["REVIEW"], description: "Flags billing that exceeds remaining unbilled quantity on the PO." },
  { id: "C16", name: "Tax calculation & regime", stage: "Reconcile", severities: ["REJECT"], description: "Validates CGST+SGST for intra-state vs IGST for inter-state transactions." },
  { id: "C17", name: "Currency verification", stage: "Normalize", severities: ["REJECT"], description: "Restricts processing to INR; foreign currency invoices rejected." },
  { id: "C18", name: "Line description similarity", stage: "PO Match", severities: ["REVIEW"], description: "Checks semantic similarity between invoice line and PO line." },
  { id: "C19", name: "Total amount tolerance", stage: "Reconcile", severities: ["REVIEW"], description: "Validates grand total matches PO within ₹10 rounding tolerance." },
  { id: "C20", name: "PO validity window", stage: "PO Match", severities: ["REVIEW"], description: "Flags invoices dated after PO validity expiration date." },
  { id: "C21", name: "HSN code validation", stage: "Normalize", severities: ["REVIEW"], description: "Validates format of 4, 6, or 8-digit HSN/SAC codes." },
];

export const RulesPage: React.FC = () => {
  const { showToast } = useToast();
  const [resetDialogOpen, setResetDialogOpen] = useState(false);
  const [confirmText, setConfirmText] = useState("");
  const [resetting, setResetting] = useState(false);

  // Fetch config
  const { data: config, isLoading: configLoading, refetch: refetchConfig } = useQuery({
    queryKey: ["config"],
    queryFn: () => api.getConfig(),
  });

  const handleReset = async () => {
    if (confirmText.trim() !== "RESET") {
      showToast("You must type RESET to confirm.");
      return;
    }
    setResetting(true);
    try {
      await api.resetAdmin();
      showToast("Demo data successfully reset to initial seed state.");
      setResetDialogOpen(false);
      setConfirmText("");
      await refetchConfig();
    } catch (err: any) {
      showToast(`Reset failed: ${err.message}`);
    } finally {
      setResetting(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* 1. Header */}
      <PageHeader
        title="Rules & Policy"
        description="Decision hierarchy, automated inspection catalogue, and tolerance thresholds."
      />

      {/* 2. Card 1: How decisions are made */}
      <div className="bg-[var(--surface)] border border-[var(--line)] rounded-[10px] p-6 shadow-[var(--shadow-1)] space-y-6">
        <div>
          <h2 className="font-heading font-semibold text-[18px] text-[var(--ink)]">
            How decisions are made
          </h2>
          <p className="font-sans text-[13px] text-[var(--ink-2)] mt-0.5">
            Strict deterministic precedence applied across all 21 checks:{" "}
            <span className="font-semibold text-[var(--ink)]">
              Reject outranks Hold, Hold outranks Review.
            </span>
          </p>
        </div>

        {/* 4 Decisions Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-4 rounded-[8px] bg-[var(--approve-tint)] border border-[var(--approve-line)] space-y-2">
            <DecisionBadge decision="APPROVE" />
            <p className="font-sans text-[13px] leading-[20px] text-[var(--approve)] m-0">
              Matches PO within tolerance, verified vendor, arithmetic and GST correct.
              Auto-approved for payment.
            </p>
          </div>

          <div className="p-4 rounded-[8px] bg-[var(--review-tint)] border border-[var(--review-line)] space-y-2">
            <DecisionBadge decision="REVIEW" />
            <p className="font-sans text-[13px] leading-[20px] text-[var(--review)] m-0">
              Discrepancy within commercial tolerance or ambiguous match. Requires human AP review.
            </p>
          </div>

          <div className="p-4 rounded-[8px] bg-[var(--hold-tint)] border border-[var(--hold-line)] space-y-2">
            <DecisionBadge decision="HOLD" />
            <p className="font-sans text-[13px] leading-[20px] text-[var(--hold)] m-0">
              High fraud risk or bank account change. Payment on hold pending verbal verification.
            </p>
          </div>

          <div className="p-4 rounded-[8px] bg-[var(--reject-tint)] border border-[var(--reject-line)] space-y-2">
            <DecisionBadge decision="REJECT" />
            <p className="font-sans text-[13px] leading-[20px] text-[var(--reject)] m-0">
              Arithmetic error, closed PO, wrong entity, or duplicate invoice. Returned to vendor.
            </p>
          </div>
        </div>

        {/* Checks Catalogue Table */}
        <div className="space-y-3 pt-4 border-t border-[var(--line)]">
          <span className="font-heading font-semibold text-[11px] uppercase tracking-[0.08em] text-[var(--ink-3)] block select-none">
            Complete Inspection Catalogue (C01 – C21)
          </span>
          <div className="overflow-x-auto border border-[var(--line)] rounded-[8px]">
            <table className="w-full text-left text-[13px]">
              <thead className="bg-[var(--surface-sunken)] border-b border-[var(--line)]">
                <tr>
                  <th className="py-2.5 px-3 font-heading font-semibold text-[11px] uppercase text-[var(--ink-3)] w-[64px]">
                    ID
                  </th>
                  <th className="py-2.5 px-3 font-heading font-semibold text-[11px] uppercase text-[var(--ink-3)]">
                    Check Name
                  </th>
                  <th className="py-2.5 px-3 font-heading font-semibold text-[11px] uppercase text-[var(--ink-3)]">
                    Stage
                  </th>
                  <th className="py-2.5 px-3 font-heading font-semibold text-[11px] uppercase text-[var(--ink-3)]">
                    Can Route To
                  </th>
                  <th className="py-2.5 px-3 font-heading font-semibold text-[11px] uppercase text-[var(--ink-3)]">
                    Policy Description
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--line)]">
                {CHECKS_CATALOGUE.map((item) => (
                  <tr key={item.id} className="hover:bg-[var(--surface-sunken)] transition-colors">
                    <td className="py-2.5 px-3 font-mono font-medium text-[var(--ink)]">
                      {item.id}
                    </td>
                    <td className="py-2.5 px-3 font-sans font-medium text-[var(--ink)]">
                      {item.name}
                    </td>
                    <td className="py-2.5 px-3 font-sans text-[var(--ink-2)]">
                      {item.stage}
                    </td>
                    <td className="py-2.5 px-3">
                      <div className="flex items-center gap-1.5 flex-wrap">
                        {item.severities.map((sev) => (
                          <DecisionBadge key={sev} decision={sev} size="sm" />
                        ))}
                      </div>
                    </td>
                    <td className="py-2.5 px-3 font-sans text-[13px] text-[var(--ink-2)] max-w-md">
                      {item.description}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* 3. Card 2: Thresholds & Configuration */}
      <div className="bg-[var(--surface)] border border-[var(--line)] rounded-[10px] p-6 shadow-[var(--shadow-1)] space-y-6">
        <div>
          <h2 className="font-heading font-semibold text-[18px] text-[var(--ink)]">
            System Thresholds & Constants
          </h2>
          <p className="font-sans text-[13px] text-[var(--ink-2)] mt-0.5">
            Operational boundaries defined for Kestrel Foods automated AP desk.
          </p>
        </div>

        {configLoading ? (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-6">
            {[1, 2, 3, 4].map((i) => (
              <Skeleton key={i} width="100%" height="48px" />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            <KeyValue
              label="BUYER ENTITY"
              value={config?.buyer.legal_name || "Kestrel Foods Pvt. Ltd."}
            />
            <KeyValue
              label="BUYER GSTIN"
              value={config?.buyer.gstin || "29AAACK4521M1ZD"}
              mono
            />
            <KeyValue
              label="PRICE TOLERANCE"
              value="1.0% or ₹1,000 per line"
            />
            <KeyValue
              label="ROUNDING LEATHWAY"
              value="₹10.00 total amount"
            />
            <KeyValue
              label="DATE FUTURE LIMIT"
              value="30 days max advance"
            />
            <KeyValue
              label="DATE STALE LIMIT"
              value="180 days past"
            />
            <KeyValue
              label="PO CANDIDATE CUTOFF"
              value="Score ≥ 0.60"
              mono
            />
            <KeyValue
              label="LLM EXTRACTOR"
              value={config?.model || "gemini-3.5-flash-lite"}
              mono
            />
          </div>
        )}
      </div>

      {/* 4. Card 3: Demo Data Reset */}
      {config?.demo_mode && (
        <div className="bg-[var(--surface)] border border-[var(--line)] rounded-[10px] p-6 shadow-[var(--shadow-1)] flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h3 className="font-heading font-semibold text-[16px] text-[var(--ink)] flex items-center gap-2">
              <RefreshCw size={16} strokeWidth={1.5} className="text-[var(--ink-2)]" />
              <span>Demo data management</span>
            </h3>
            <p className="font-sans text-[13px] text-[var(--ink-2)] mt-1 max-w-xl">
              Resets vendors, POs and the invoice ledger to their starting state. Cached extractions
              are kept.
            </p>
          </div>

          <Button
            variant="danger"
            size="sm"
            onClick={() => setResetDialogOpen(true)}
          >
            Reset demo data
          </Button>
        </div>
      )}

      {/* Reset Confirmation Dialog */}
      {resetDialogOpen && (
        <Dialog
          open={resetDialogOpen}
          onClose={() => setResetDialogOpen(false)}
          title="Reset Demo Data"
          description="This will restore the database to its pristine seed state. All newly processed invoice runs and human review decisions will be wiped."
        >
          <div className="space-y-4 pt-2">
            <div className="p-3 bg-[var(--reject-tint)] border border-[var(--reject-line)] rounded-[8px] text-[13px] text-[var(--reject)] flex items-start gap-2">
              <AlertTriangle size={16} className="shrink-0 mt-0.5" strokeWidth={1.5} />
              <span>
                To prevent accidental data loss, please type <span className="font-bold">RESET</span> in
                capital letters below.
              </span>
            </div>

            <input
              type="text"
              value={confirmText}
              onChange={(e) => setConfirmText(e.target.value)}
              placeholder="Type RESET"
              className="w-full p-2.5 rounded-[8px] border border-[var(--line-strong)] bg-[var(--surface-sunken)] text-[14px] font-mono focus:outline-none focus:border-[var(--ink)]"
            />

            <div className="flex justify-end gap-3 pt-3 border-t border-[var(--line)]">
              <Button variant="ghost" onClick={() => setResetDialogOpen(false)}>
                Cancel
              </Button>
              <Button
                variant="danger"
                loading={resetting}
                disabled={confirmText.trim() !== "RESET"}
                onClick={handleReset}
              >
                Confirm Reset
              </Button>
            </div>
          </div>
        </Dialog>
      )}
    </div>
  );
};
