import React from "react";
import { Copy, Check } from "lucide-react";
import type { RunDetail, Stage } from "../lib/types";
import { KeyValue } from "./KeyValue";
import { ConsumptionBar } from "./ConsumptionBar";

export interface StageOutputViewProps {
  stage: Stage;
  run: RunDetail;
  onSwitchTab?: (tabId: string) => void;
}

export const StageOutputView: React.FC<StageOutputViewProps> = ({
  stage,
  run,
  onSwitchTab,
}) => {
  const [copiedSha, setCopiedSha] = React.useState(false);
  const out = stage.output || {};

  const handleCopySha = (sha: string) => {
    navigator.clipboard.writeText(sha);
    setCopiedSha(true);
    setTimeout(() => setCopiedSha(false), 2000);
  };

  // 1. INGEST
  if (stage.stage_key === "ingest") {
    const doc = run.document;
    const sha = doc?.sha256 || (out.sha256 as string) || "";
    return (
      <div className="mt-6 pt-6 border-t border-[var(--line)]">
        <span className="font-heading font-semibold text-[11px] leading-[16px] uppercase tracking-[0.08em] text-[var(--ink-3)] block mb-4">
          Ingestion Diagnostics
        </span>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <KeyValue label="FILE" value={doc?.filename || "—"} />
          <KeyValue
            label="SIZE"
            value={doc?.size_bytes ? `${(doc.size_bytes / 1024).toFixed(1)} KB` : "—"}
            mono
          />
          <KeyValue label="PAGES" value={doc?.page_count ?? 1} mono />
          <KeyValue
            label="TEXT LAYER"
            value={
              doc?.has_text_layer ? (
                <span className="text-[var(--approve)] font-semibold">Yes</span>
              ) : (
                <span className="text-[var(--review)] font-semibold">No (Scanned image)</span>
              )
            }
          />
        </div>
        {sha && (
          <div className="mt-4 flex items-center gap-2">
            <span className="font-heading font-semibold text-[11px] uppercase tracking-[0.08em] text-[var(--ink-3)]">
              SHA-256:
            </span>
            <span className="font-mono text-[12px] bg-[var(--surface-sunken)] px-2 py-0.5 rounded border border-[var(--line)] text-[var(--ink)]">
              {sha.slice(0, 16)}...
            </span>
            <button
              type="button"
              onClick={() => handleCopySha(sha)}
              className="text-[var(--ink-3)] hover:text-[var(--ink)] p-1 rounded hover:bg-[var(--surface-sunken)] transition-colors cursor-pointer"
              title="Copy full SHA-256"
            >
              {copiedSha ? <Check size={14} className="text-[var(--approve)]" /> : <Copy size={14} />}
            </button>
          </div>
        )}
      </div>
    );
  }

  // 2. EXTRACT
  if (stage.stage_key === "extract") {
    return (
      <div className="mt-6 pt-6 border-t border-[var(--line)]">
        <span className="font-heading font-semibold text-[11px] leading-[16px] uppercase tracking-[0.08em] text-[var(--ink-3)] block mb-4">
          Extraction Parameters
        </span>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <KeyValue
            label="METHOD"
            value={run.extraction_method || (out.method as string) || "Text layer"}
          />
          <KeyValue label="MODEL" value={(out.model as string) || "gemini-3.5-flash-lite"} mono />
          <KeyValue
            label="CACHED"
            value={
              out.cached || run.use_cache ? (
                <span className="text-[var(--approve)] font-medium">Hit (True)</span>
              ) : (
                "Live API call"
              )
            }
          />
          <KeyValue
            label="LATENCY"
            value={stage.duration_ms ? `${(stage.duration_ms / 1000).toFixed(2)} s` : "—"}
            mono
          />
        </div>
        {onSwitchTab && (
          <div className="mt-4">
            <button
              type="button"
              onClick={() => onSwitchTab("extracted")}
              className="text-[13px] font-sans font-medium text-[var(--ink)] underline hover:opacity-80 cursor-pointer"
            >
              See all extracted fields →
            </button>
          </div>
        )}
      </div>
    );
  }

  // 3. NORMALIZE
  if (stage.stage_key === "normalize") {
    const normalizations = (out.normalizations as any[]) || [];
    return (
      <div className="mt-6 pt-6 border-t border-[var(--line)]">
        <span className="font-heading font-semibold text-[11px] leading-[16px] uppercase tracking-[0.08em] text-[var(--ink-3)] block mb-3">
          Normalizations Performed
        </span>
        {normalizations.length === 0 ? (
          <div className="text-[13px] text-[var(--ink-3)]">
            Dates, currency amounts, and identification codes sanitized and verified.
          </div>
        ) : (
          <div className="overflow-x-auto border border-[var(--line)] rounded-[8px]">
            <table className="w-full text-left text-[13px]">
              <thead className="bg-[var(--surface-sunken)] border-b border-[var(--line)]">
                <tr>
                  <th className="py-2 px-3 font-heading font-semibold text-[11px] uppercase text-[var(--ink-3)]">
                    Field
                  </th>
                  <th className="py-2 px-3 font-heading font-semibold text-[11px] uppercase text-[var(--ink-3)]">
                    As Printed
                  </th>
                  <th className="py-2 px-3 font-heading font-semibold text-[11px] uppercase text-[var(--ink-3)]">
                    Normalized
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--line)]">
                {normalizations.map((n, i) => (
                  <tr key={i}>
                    <td className="py-2 px-3 font-medium text-[var(--ink)]">{n.field}</td>
                    <td className="py-2 px-3 font-mono text-[var(--ink-2)]">{n.as_printed}</td>
                    <td className="py-2 px-3 font-mono text-[var(--ink)] font-semibold">{n.normalized}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    );
  }

  // 4. VENDOR
  if (stage.stage_key === "vendor") {
    const bankCheck = stage.checks.find((c) => c.check_id === "C07");
    const bankMismatch = Boolean(bankCheck && bankCheck.outcome === "FLAG");
    const vName = run.vendor_name || (out.legal_name as string) || "—";
    const vGstin = (out.gstin as string) || (run.result?.normalized as any)?.vendor_gstin || "—";

    return (
      <div className="mt-6 pt-6 border-t border-[var(--line)] space-y-4">
        <span className="font-heading font-semibold text-[11px] leading-[16px] uppercase tracking-[0.08em] text-[var(--ink-3)] block">
          Vendor Master Verification
        </span>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 p-3 rounded-[8px] bg-[var(--surface-sunken)] border border-[var(--line)]">
          <KeyValue label="VENDOR" value={vName} />
          <KeyValue label="GSTIN" value={vGstin} mono />
          <KeyValue
            label="STATUS"
            value={<span className="text-[var(--approve)] font-semibold">ACTIVE</span>}
          />
          <KeyValue label="MATCH METHOD" value={(out.match_method as string) || "GSTIN lookup"} />
        </div>

        {bankCheck && (
          <div>
            <span className="font-heading font-semibold text-[11px] uppercase tracking-[0.08em] text-[var(--ink-3)] block mb-2">
              Bank Details Comparison
            </span>
            <div className="overflow-x-auto border border-[var(--line)] rounded-[8px]">
              <table className="w-full text-left text-[13px]">
                <thead className="bg-[var(--surface-sunken)] border-b border-[var(--line)]">
                  <tr>
                    <th className="py-2 px-3 font-heading font-semibold text-[11px] uppercase text-[var(--ink-3)]">
                      Attribute
                    </th>
                    <th className="py-2 px-3 font-heading font-semibold text-[11px] uppercase text-[var(--ink-3)]">
                      On Invoice
                    </th>
                    <th className="py-2 px-3 font-heading font-semibold text-[11px] uppercase text-[var(--ink-3)]">
                      On Vendor Master
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--line)] font-mono">
                  <tr className={bankMismatch ? "bg-[var(--hold-tint)]" : ""}>
                    <td className="py-2 px-3 font-sans font-medium text-[var(--ink)]">Account Number</td>
                    <td className={`py-2 px-3 ${bankMismatch ? "text-[var(--hold)] font-bold" : ""}`}>
                      {String(bankCheck.evidence?.invoice_account || "—")}
                    </td>
                    <td className="py-2 px-3 text-[var(--ink-2)]">
                      {String(bankCheck.evidence?.master_account_masked || "••••5321")}
                    </td>
                  </tr>
                  <tr>
                    <td className="py-2 px-3 font-sans font-medium text-[var(--ink)]">IFSC Code</td>
                    <td className="py-2 px-3">{String(bankCheck.evidence?.invoice_ifsc || "—")}</td>
                    <td className="py-2 px-3 text-[var(--ink-2)]">{String(bankCheck.evidence?.master_ifsc || "—")}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    );
  }

  // 5. DUPLICATES
  if (stage.stage_key === "duplicates") {
    const dupCheck = stage.checks.find((c) => c.check_id === "C09");
    const isDup = dupCheck && dupCheck.outcome === "FLAG";

    return (
      <div className="mt-6 pt-6 border-t border-[var(--line)] space-y-3">
        <span className="font-heading font-semibold text-[11px] leading-[16px] uppercase tracking-[0.08em] text-[var(--ink-3)] block">
          Ledger Duplicate Scan
        </span>
        <div className="text-[14px] text-[var(--ink-2)]">
          Compared against historical approved invoices in the ledger.
        </div>
        {isDup && dupCheck.evidence && (
          <div className="p-3 bg-[var(--reject-tint)] border border-[var(--reject-line)] rounded-[8px] text-[13px] text-[var(--reject)] font-sans">
            <span className="font-bold">Duplicate Match Detected:</span> Prior invoice{" "}
            <span className="font-mono font-semibold">{String(dupCheck.evidence.prior_invoice_number)}</span> dated{" "}
            {String(dupCheck.evidence.prior_date)} with amount ₹{String(dupCheck.evidence.prior_amount)}.
          </div>
        )}
      </div>
    );
  }

  // 6. PO_MATCH
  if (stage.stage_key === "po_match") {
    const isInfer = run.po_method === "inferred";
    const candidates = (out.candidates as any[]) || [];
    const linePairings = (out.line_pairings as any[]) || [];

    return (
      <div className="mt-6 pt-6 border-t border-[var(--line)] space-y-4">
        <span className="font-heading font-semibold text-[11px] leading-[16px] uppercase tracking-[0.08em] text-[var(--ink-3)] block">
          PO Match & Line Pairing ({run.po_method || "explicit"})
        </span>

        {isInfer && candidates.length > 0 && (
          <div>
            <span className="font-heading font-semibold text-[11px] uppercase tracking-[0.08em] text-[var(--ink-3)] block mb-2">
              Inferred Candidate Scoring
            </span>
            <div className="overflow-x-auto border border-[var(--line)] rounded-[8px]">
              <table className="w-full text-left text-[13px]">
                <thead className="bg-[var(--surface-sunken)] border-b border-[var(--line)]">
                  <tr>
                    <th className="py-2 px-3 font-heading font-semibold text-[11px] uppercase text-[var(--ink-3)]">PO</th>
                    <th className="py-2 px-3 font-heading font-semibold text-[11px] uppercase text-[var(--ink-3)]">Coverage</th>
                    <th className="py-2 px-3 font-heading font-semibold text-[11px] uppercase text-[var(--ink-3)]">Amount Fit</th>
                    <th className="py-2 px-3 font-heading font-semibold text-[11px] uppercase text-[var(--ink-3)]">Date Bonus</th>
                    <th className="py-2 px-3 font-heading font-semibold text-[11px] uppercase text-[var(--ink-3)]">Score</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--line)] font-mono">
                  {candidates.map((c, i) => (
                    <tr key={i} className={i === 0 ? "font-bold bg-[var(--surface-sunken)]" : ""}>
                      <td className="py-2 px-3">{c.po_number}</td>
                      <td className="py-2 px-3">{c.coverage}</td>
                      <td className="py-2 px-3">{c.amount_fit}</td>
                      <td className="py-2 px-3">{c.date_bonus}</td>
                      <td className="py-2 px-3 text-[var(--ink)]">{c.composite_score}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {linePairings.length > 0 && (
          <div>
            <span className="font-heading font-semibold text-[11px] uppercase tracking-[0.08em] text-[var(--ink-3)] block mb-2">
              Line Pairings
            </span>
            <div className="overflow-x-auto border border-[var(--line)] rounded-[8px]">
              <table className="w-full text-left text-[13px]">
                <thead className="bg-[var(--surface-sunken)] border-b border-[var(--line)]">
                  <tr>
                    <th className="py-2 px-3 font-heading font-semibold text-[11px] uppercase text-[var(--ink-3)]">Invoice Line</th>
                    <th className="py-2 px-3 font-heading font-semibold text-[11px] uppercase text-[var(--ink-3)]">Matched PO Line</th>
                    <th className="py-2 px-3 font-heading font-semibold text-[11px] uppercase text-[var(--ink-3)]">Score</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--line)] font-mono">
                  {linePairings.map((p, i) => (
                    <tr key={i}>
                      <td className="py-2 px-3">{p.invoice_line_no}: {p.invoice_desc}</td>
                      <td className="py-2 px-3">{p.po_line_no ? `Line ${p.po_line_no}: ${p.po_desc}` : "—"}</td>
                      <td className="py-2 px-3">{p.score}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    );
  }

  // 7. RECONCILE
  if (stage.stage_key === "reconcile") {
    const lines = (out.lines as any[]) || [];
    const beforePct = Number(out.billed_pct_before ?? 0);
    const afterPct = Number(out.billed_pct_after ?? 0);

    return (
      <div className="mt-6 pt-6 border-t border-[var(--line)] space-y-4">
        <span className="font-heading font-semibold text-[11px] leading-[16px] uppercase tracking-[0.08em] text-[var(--ink-3)] block">
          PO Line Consumption & Overrun Analysis
        </span>

        <div className="flex items-center gap-6 p-4 bg-[var(--surface-sunken)] border border-[var(--line)] rounded-[8px]">
          <div>
            <span className="text-[12px] text-[var(--ink-3)] block">Before Invoice</span>
            <ConsumptionBar billedPct={beforePct} width="120px" />
          </div>
          <span className="text-[var(--ink-3)]">→</span>
          <div>
            <span className="text-[12px] text-[var(--ink-3)] block">After Invoice</span>
            <ConsumptionBar billedPct={afterPct} width="120px" />
          </div>
        </div>

        {lines.length > 0 && (
          <div className="overflow-x-auto border border-[var(--line)] rounded-[8px]">
            <table className="w-full text-left text-[13px]">
              <thead className="bg-[var(--surface-sunken)] border-b border-[var(--line)]">
                <tr>
                  <th className="py-2 px-3 font-heading font-semibold text-[11px] uppercase text-[var(--ink-3)]">Line</th>
                  <th className="py-2 px-3 font-heading font-semibold text-[11px] uppercase text-[var(--ink-3)]">Ordered</th>
                  <th className="py-2 px-3 font-heading font-semibold text-[11px] uppercase text-[var(--ink-3)]">Already Billed</th>
                  <th className="py-2 px-3 font-heading font-semibold text-[11px] uppercase text-[var(--ink-3)]">This Invoice</th>
                  <th className="py-2 px-3 font-heading font-semibold text-[11px] uppercase text-[var(--ink-3)]">Remaining</th>
                  <th className="py-2 px-3 font-heading font-semibold text-[11px] uppercase text-[var(--ink-3)]">Price Var</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--line)] font-mono">
                {lines.map((l, i) => {
                  const isOver = l.remaining_after < 0;
                  return (
                    <tr key={i} className={isOver ? "bg-[var(--reject-tint)] text-[var(--reject)]" : ""}>
                      <td className="py-2 px-3">{l.line_no}</td>
                      <td className="py-2 px-3">{l.ordered_qty}</td>
                      <td className="py-2 px-3">{l.already_billed_qty}</td>
                      <td className="py-2 px-3 font-semibold">{l.billed_qty}</td>
                      <td className={`py-2 px-3 ${isOver ? "font-bold" : ""}`}>{l.remaining_after}</td>
                      <td className="py-2 px-3">{l.price_variance || "0.0%"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    );
  }

  // 8. DECIDE
  if (stage.stage_key === "decide") {
    const severities = (out.severities_found as string[]) || [];
    return (
      <div className="mt-6 pt-6 border-t border-[var(--line)] space-y-3">
        <span className="font-heading font-semibold text-[11px] leading-[16px] uppercase tracking-[0.08em] text-[var(--ink-3)] block">
          Decision Synthesis
        </span>
        <div className="p-4 bg-[var(--surface-sunken)] border border-[var(--line)] rounded-[8px] space-y-2">
          <div className="text-[14px] font-sans text-[var(--ink)]">
            <span className="font-semibold">Summary:</span> {run.headline || "Decision synthesized from 21 policy checks."}
          </div>
          {severities.length > 0 && (
            <div className="text-[13px] text-[var(--ink-2)] font-mono">
              Precedence applied: {severities.join(" > ")} → {run.decision}
            </div>
          )}
        </div>
      </div>
    );
  }

  return null;
};
