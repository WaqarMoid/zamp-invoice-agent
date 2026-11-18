import React, { useState } from "react";
import { Plus, Download, Trash2, ArrowRight } from "lucide-react";
import { Button } from "../components/Button";
import { DecisionBadge } from "../components/DecisionBadge";
import { OutcomeIcon } from "../components/OutcomeIcon";
import { StageMarker } from "../components/StageMarker";
import { KeyValue } from "../components/KeyValue";
import { Money } from "../components/Money";
import { ConsumptionBar } from "../components/ConsumptionBar";
import { Tabs } from "../components/Tabs";
import { Disclosure } from "../components/Disclosure";
import { Dialog } from "../components/Dialog";
import { Skeleton } from "../components/Skeleton";
import { EmptyState } from "../components/EmptyState";
import { Dropzone } from "../components/Dropzone";
import { DataTable, Column } from "../components/DataTable";
import { useToast } from "../components/Toast";
import { PageHeader } from "../components/PageHeader";

export const Gallery: React.FC = () => {
  const [activeTab, setActiveTab] = useState("stage");
  const [dialogOpen, setDialogOpen] = useState(false);
  const { showToast } = useToast();

  const sampleEvidence = {
    tolerance_pct: 1.0,
    tolerance_inr: 1000.0,
    line_variance_inr: 1250.0,
    candidate_pos: ["PO-2026-0412", "PO-2026-0418"],
    matched_lines: [
      { invoice_line: 1, po_line: 1, score: 0.94 },
      { invoice_line: 2, po_line: 2, score: 0.88 },
    ],
  };

  interface SampleTableRow {
    id: string;
    vendor: string;
    po: string;
    amount: number;
    decision: "APPROVE" | "REVIEW" | "HOLD" | "REJECT";
  }

  const tableData: SampleTableRow[] = [
    { id: "SPS/26-27/0512", vendor: "Sharma Packaging Solutions", po: "PO-2026-0412", amount: 129682.0, decision: "APPROVE" },
    { id: "DCC-INV-1092", vendor: "Deccan Cold Chain Logistics", po: "PO-2026-0418", amount: 48970.0, decision: "REVIEW" },
    { id: "BIS-INV-26-89", vendor: "Bluepeak IT Services", po: "PO-2026-0398", amount: 247800.0, decision: "HOLD" },
    { id: "MOP-2026-0814", vendor: "Metro Office Products", po: "PO-2026-0377", amount: 82600.0, decision: "REJECT" },
  ];

  const tableColumns: Column<SampleTableRow>[] = [
    { key: "id", header: "Invoice", render: (r) => <span className="font-mono">{r.id}</span> },
    { key: "vendor", header: "Vendor", render: (r) => r.vendor },
    { key: "po", header: "PO", render: (r) => <span className="font-mono">{r.po}</span> },
    { key: "amount", header: "Amount", align: "right", render: (r) => <Money amount={r.amount} /> },
    { key: "decision", header: "Decision", render: (r) => <DecisionBadge decision={r.decision} size="sm" /> },
  ];

  return (
    <div className="space-y-12">
      <PageHeader
        title="Component Gallery"
        description="Design system tokens, typography specimens, and atomic UI components (dev reference)."
        actions={
          <Button variant="secondary" onClick={() => showToast("Test notification toast fired!")}>
            Trigger Toast
          </Button>
        }
      />

      {/* 1. Typography & Numerals */}
      <section className="bg-[var(--surface)] border border-[var(--line)] rounded-[10px] p-6 shadow-[var(--shadow-1)]">
        <h2 className="font-heading font-semibold text-[18px] leading-[26px] text-[var(--ink)] mb-4">
          Typography Specimen & Lining Numerals
        </h2>
        <div className="space-y-4">
          <div>
            <span className="font-heading font-semibold text-[11px] uppercase tracking-[0.08em] text-[var(--ink-3)] block mb-1">
              Display (Raleway 700 32px)
            </span>
            <div className="font-heading font-bold text-[32px] leading-[40px] text-[var(--ink)]">
              Needs review · ₹1,29,682.00 (0123456789)
            </div>
          </div>
          <div>
            <span className="font-heading font-semibold text-[11px] uppercase tracking-[0.08em] text-[var(--ink-3)] block mb-1">
              Heading 1 (Raleway 700 26px)
            </span>
            <h1 className="font-heading font-bold text-[26px] leading-[32px] text-[var(--ink)]">
              Invoice Desk: 8 Stages Processed in 3.4s
            </h1>
          </div>
          <div>
            <span className="font-heading font-semibold text-[11px] uppercase tracking-[0.08em] text-[var(--ink-3)] block mb-1">
              Heading 2 & 3 (Raleway 600 18px & 15px)
            </span>
            <h2 className="font-heading font-semibold text-[18px] leading-[26px] text-[var(--ink)]">
              Stage 6 · Reconcile against PO-2026-0412
            </h2>
            <h3 className="font-heading font-semibold text-[15px] leading-[22px] text-[var(--ink)]">
              Subsection: Line item arithmetic check
            </h3>
          </div>
          <div>
            <span className="font-heading font-semibold text-[11px] uppercase tracking-[0.08em] text-[var(--ink-3)] block mb-1">
              Body & Mono (Source Sans 3 15px & IBM Plex Mono 13px)
            </span>
            <p className="font-sans text-[15px] leading-[24px] text-[var(--ink)] max-w-[68ch]">
              The invoice billed 40 units against an unbilled balance of 30 units on PO-2026-0418.
              GSTIN <span className="font-mono text-[13px] bg-[var(--surface-sunken)] px-1.5 py-0.5 rounded border border-[var(--line)]">29AAACK4521M1ZD</span> matches
              Kestrel Foods Pvt. Ltd. with tax regime CGST+SGST.
            </p>
          </div>
        </div>
      </section>

      {/* 2. Color Tokens */}
      <section className="bg-[var(--surface)] border border-[var(--line)] rounded-[10px] p-6 shadow-[var(--shadow-1)]">
        <h2 className="font-heading font-semibold text-[18px] leading-[26px] text-[var(--ink)] mb-4">
          Colour Tokens (Semantic & Neutral)
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="p-3 rounded border border-[var(--approve-line)] bg-[var(--approve-tint)] text-[var(--approve)]">
            <div className="font-semibold text-[13px]">APPROVE</div>
            <div className="font-mono text-[11px]">#1B6B43</div>
          </div>
          <div className="p-3 rounded border border-[var(--review-line)] bg-[var(--review-tint)] text-[var(--review)]">
            <div className="font-semibold text-[13px]">REVIEW</div>
            <div className="font-mono text-[11px]">#8A5A00</div>
          </div>
          <div className="p-3 rounded border border-[var(--hold-line)] bg-[var(--hold-tint)] text-[var(--hold)]">
            <div className="font-semibold text-[13px]">HOLD</div>
            <div className="font-mono text-[11px]">#A13D0F</div>
          </div>
          <div className="p-3 rounded border border-[var(--reject-line)] bg-[var(--reject-tint)] text-[var(--reject)]">
            <div className="font-semibold text-[13px]">REJECT</div>
            <div className="font-mono text-[11px]">#A3182A</div>
          </div>
        </div>
      </section>

      {/* 3. Buttons */}
      <section className="bg-[var(--surface)] border border-[var(--line)] rounded-[10px] p-6 shadow-[var(--shadow-1)]">
        <h2 className="font-heading font-semibold text-[18px] leading-[26px] text-[var(--ink)] mb-4">
          Buttons & States
        </h2>
        <div className="flex flex-wrap items-center gap-4">
          <Button variant="primary" icon={<Plus size={16} strokeWidth={1.5} />}>
            Primary Action
          </Button>
          <Button variant="secondary" icon={<Download size={16} strokeWidth={1.5} />}>
            Secondary
          </Button>
          <Button variant="ghost" icon={<ArrowRight size={16} strokeWidth={1.5} />}>
            Ghost Link
          </Button>
          <Button variant="danger" icon={<Trash2 size={16} strokeWidth={1.5} />}>
            Reject / Danger
          </Button>
          <Button variant="primary" loading>
            Loading State
          </Button>
          <Button variant="secondary" disabled>
            Disabled
          </Button>
          <Button variant="secondary" size="sm">
            Small Size
          </Button>
        </div>
      </section>

      {/* 4. Decision Badges & Outcome Icons */}
      <section className="bg-[var(--surface)] border border-[var(--line)] rounded-[10px] p-6 shadow-[var(--shadow-1)]">
        <h2 className="font-heading font-semibold text-[18px] leading-[26px] text-[var(--ink)] mb-4">
          Decision Badges & Outcome Markers
        </h2>
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <DecisionBadge decision="APPROVE" />
            <DecisionBadge decision="REVIEW" />
            <DecisionBadge decision="HOLD" />
            <DecisionBadge decision="REJECT" />
            <DecisionBadge status="RUNNING" currentStageLabel="Extract" />
            <DecisionBadge status="QUEUED" />
          </div>

          <div className="flex items-center gap-6 pt-2">
            <div className="flex items-center gap-2 text-[13px]">
              <OutcomeIcon outcome="PASS" /> PASS
            </div>
            <div className="flex items-center gap-2 text-[13px]">
              <OutcomeIcon outcome="INFO" /> INFO
            </div>
            <div className="flex items-center gap-2 text-[13px]">
              <OutcomeIcon outcome="FLAG" severity="REVIEW" /> REVIEW flag
            </div>
            <div className="flex items-center gap-2 text-[13px]">
              <OutcomeIcon outcome="FLAG" severity="HOLD" /> HOLD flag
            </div>
            <div className="flex items-center gap-2 text-[13px]">
              <OutcomeIcon outcome="FLAG" severity="REJECT" /> REJECT flag
            </div>
            <div className="flex items-center gap-2 text-[13px]">
              <OutcomeIcon outcome="SKIP" /> SKIP
            </div>
          </div>

          <div className="flex items-center gap-4 pt-2">
            <StageMarker position={1} status="PASSED" />
            <StageMarker position={2} status="RUNNING" />
            <StageMarker position={3} status="FLAGGED" highestSeverity="REVIEW" />
            <StageMarker position={4} status="FLAGGED" highestSeverity="HOLD" />
            <StageMarker position={5} status="FLAGGED" highestSeverity="REJECT" />
            <StageMarker position={6} status="FAILED" />
            <StageMarker position={7} status="SKIPPED" />
            <StageMarker position={8} status="PENDING" />
          </div>
        </div>
      </section>

      {/* 5. KeyValue, Money, ConsumptionBar */}
      <section className="bg-[var(--surface)] border border-[var(--line)] rounded-[10px] p-6 shadow-[var(--shadow-1)]">
        <h2 className="font-heading font-semibold text-[18px] leading-[26px] text-[var(--ink)] mb-4">
          Financial & Key-Value Elements
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-6">
          <KeyValue label="VENDOR" value="Sharma Packaging Solutions" />
          <KeyValue label="PO NUMBER" value="PO-2026-0412" mono />
          <KeyValue label="INVOICE AMOUNT" value={<Money amount={129682.0} />} mono size="lg" />
          <KeyValue label="COMPACT VALUE" value={<Money amount={1240000} compact />} mono size="lg" />
        </div>

        <div className="mt-6 pt-6 border-t border-[var(--line)] space-y-3">
          <div className="flex items-center justify-between max-w-md">
            <span className="text-[13px] text-[var(--ink-2)]">75% partially billed:</span>
            <ConsumptionBar billedPct={75.0} />
          </div>
          <div className="flex items-center justify-between max-w-md">
            <span className="text-[13px] text-[var(--ink-2)]">100% fully billed:</span>
            <ConsumptionBar billedPct={100.0} />
          </div>
          <div className="flex items-center justify-between max-w-md">
            <span className="text-[13px] text-[var(--ink-2)]">118% overbilled:</span>
            <ConsumptionBar billedPct={118.5} />
          </div>
        </div>
      </section>

      {/* 6. Tabs, Disclosure, Dialog Trigger */}
      <section className="bg-[var(--surface)] border border-[var(--line)] rounded-[10px] p-6 shadow-[var(--shadow-1)]">
        <h2 className="font-heading font-semibold text-[18px] leading-[26px] text-[var(--ink)] mb-4">
          Interactive Controls & Disclosure
        </h2>
        <Tabs
          tabs={[
            { id: "stage", label: "Stage", count: 8 },
            { id: "extracted", label: "Extracted data" },
            { id: "events", label: "Event log", count: 36 },
          ]}
          activeTab={activeTab}
          onChange={setActiveTab}
        />

        <div className="py-4">
          <Disclosure label="Show tolerance check evidence" data={sampleEvidence} />
        </div>

        <div className="pt-2">
          <Button variant="secondary" onClick={() => setDialogOpen(true)}>
            Open Sample Dialog
          </Button>
          <Dialog
            open={dialogOpen}
            onClose={() => setDialogOpen(false)}
            title="Confirm AP Approval"
            description="You are manually approving this invoice despite flag C15 (quantity overrun)."
          >
            <div className="space-y-4 pt-2">
              <p className="text-[14px] text-[var(--ink-2)]">
                Please provide an audit note describing why this billing was authorized.
              </p>
              <textarea
                rows={3}
                placeholder="Approved per procurement team confirmation..."
                className="w-full p-2.5 rounded-[8px] border border-[var(--line-strong)] bg-[var(--surface-sunken)] text-[14px] font-sans focus:outline-none focus:border-[var(--ink)]"
              />
              <div className="flex justify-end gap-3 pt-2">
                <Button variant="ghost" onClick={() => setDialogOpen(false)}>
                  Cancel
                </Button>
                <Button
                  variant="primary"
                  onClick={() => {
                    setDialogOpen(false);
                    showToast("Audit note recorded and invoice approved.");
                  }}
                >
                  Confirm Approval
                </Button>
              </div>
            </div>
          </Dialog>
        </div>
      </section>

      {/* 7. Dropzone */}
      <section className="bg-[var(--surface)] border border-[var(--line)] rounded-[10px] p-6 shadow-[var(--shadow-1)]">
        <h2 className="font-heading font-semibold text-[18px] leading-[26px] text-[var(--ink)] mb-4">
          Dropzone File Ingestion
        </h2>
        <Dropzone onFileSelect={(file) => showToast(`Selected file: ${file.name} (${file.size} bytes)`)} />
      </section>

      {/* 8. DataTable */}
      <section>
        <h2 className="font-heading font-semibold text-[18px] leading-[26px] text-[var(--ink)] mb-4">
          Data Table Specimen
        </h2>
        <DataTable
          columns={tableColumns}
          data={tableData}
          keyExtractor={(r) => r.id}
          onRowClick={(r) => showToast(`Clicked row: ${r.id}`)}
        />
      </section>

      {/* 9. Skeletons & EmptyState */}
      <section className="bg-[var(--surface)] border border-[var(--line)] rounded-[10px] p-6 shadow-[var(--shadow-1)]">
        <h2 className="font-heading font-semibold text-[18px] leading-[26px] text-[var(--ink)] mb-4">
          Loading Skeletons & Empty State
        </h2>
        <div className="space-y-2 mb-6">
          <Skeleton height={28} width="35%" />
          <Skeleton height={18} width="65%" />
          <Skeleton height={18} width="50%" />
        </div>
        <EmptyState
          title="No purchase orders found"
          description="Try adjusting your search terms or filter settings to view open POs."
          action={<Button variant="secondary" size="sm">Clear filters</Button>}
        />
      </section>
    </div>
  );
};
