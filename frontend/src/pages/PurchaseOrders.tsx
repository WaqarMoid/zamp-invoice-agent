import React, { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ChevronDown, ChevronRight, ExternalLink } from "lucide-react";
import { api } from "../lib/api";
import { formatDate } from "../lib/format";
import type { PurchaseOrder } from "../lib/types";
import { PageHeader } from "../components/PageHeader";
import { Money } from "../components/Money";
import { ConsumptionBar } from "../components/ConsumptionBar";
import { Skeleton } from "../components/Skeleton";

export const PurchaseOrdersPage: React.FC = () => {
  const [expandedPo, setExpandedPo] = useState<string | null>(null);

  // 1. Fetch Purchase Orders
  const { data: pos, isLoading: posLoading } = useQuery({
    queryKey: ["purchase-orders"],
    queryFn: () => api.getPurchaseOrders(),
  });

  // 2. Fetch Single PO Detail (for expanded invoices history)
  const { data: expandedDetail, isLoading: expandedLoading } = useQuery({
    queryKey: ["purchase-order-detail", expandedPo],
    queryFn: () => (expandedPo ? api.getPurchaseOrder(expandedPo) : null),
    enabled: Boolean(expandedPo),
  });

  // 3. Fetch Vendors
  const { data: vendors, isLoading: vendorsLoading } = useQuery({
    queryKey: ["vendors"],
    queryFn: () => api.getVendors(),
  });

  const toggleExpand = (poNumber: string) => {
    setExpandedPo((curr) => (curr === poNumber ? null : poNumber));
  };

  return (
    <div className="space-y-8">
      {/* 1. Header */}
      <PageHeader
        title="Purchase orders"
        description="Open commitments and how much of each has been invoiced."
      />

      {/* 2. Purchase Orders Table */}
      <div className="bg-[var(--surface)] border border-[var(--line)] rounded-[10px] shadow-[var(--shadow-1)] overflow-hidden">
        {posLoading ? (
          <div className="p-6 space-y-4">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="flex items-center justify-between gap-4 py-2 border-b border-[var(--line)] last:border-b-0">
                <Skeleton width="120px" height="18px" />
                <Skeleton width="180px" height="18px" />
                <Skeleton width="90px" height="18px" />
                <Skeleton width="70px" height="18px" />
                <Skeleton width="160px" height="18px" />
              </div>
            ))}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-left text-[14px]">
              <thead className="sticky top-0 bg-[var(--surface-sunken)] border-b border-[var(--line)]">
                <tr>
                  <th className="py-3 px-4 font-heading font-semibold text-[11px] uppercase tracking-[0.08em] text-[var(--ink-3)] w-[36px]"></th>
                  <th className="py-3 px-4 font-heading font-semibold text-[11px] uppercase tracking-[0.08em] text-[var(--ink-3)]">
                    PO
                  </th>
                  <th className="py-3 px-4 font-heading font-semibold text-[11px] uppercase tracking-[0.08em] text-[var(--ink-3)]">
                    Vendor
                  </th>
                  <th className="py-3 px-4 font-heading font-semibold text-[11px] uppercase tracking-[0.08em] text-[var(--ink-3)]">
                    Date
                  </th>
                  <th className="py-3 px-4 font-heading font-semibold text-[11px] uppercase tracking-[0.08em] text-[var(--ink-3)]">
                    Status
                  </th>
                  <th className="py-3 px-4 font-heading font-semibold text-[11px] uppercase tracking-[0.08em] text-[var(--ink-3)] text-right">
                    Value
                  </th>
                  <th className="py-3 px-4 font-heading font-semibold text-[11px] uppercase tracking-[0.08em] text-[var(--ink-3)] w-[260px]">
                    Billed
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--line)]">
                {pos?.map((po: PurchaseOrder) => {
                  const isExpanded = expandedPo === po.po_number;
                  const netRupees = po.net_value ? parseFloat(po.net_value.replace(/[^\d.]/g, "")) : 0;

                  return (
                    <React.Fragment key={po.po_number}>
                      <tr
                        tabIndex={0}
                        onClick={() => toggleExpand(po.po_number)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter" || e.key === " ") {
                            e.preventDefault();
                            toggleExpand(po.po_number);
                          }
                        }}
                        className={`transition-colors duration-100 cursor-pointer hover:bg-[var(--surface-sunken)] ${
                          isExpanded ? "bg-[var(--surface-sunken)] font-medium" : ""
                        }`}
                      >
                        <td className="py-3 px-3 text-[var(--ink-3)]">
                          {isExpanded ? (
                            <ChevronDown size={16} strokeWidth={1.5} />
                          ) : (
                            <ChevronRight size={16} strokeWidth={1.5} />
                          )}
                        </td>
                        <td className="py-3 px-4 font-mono font-medium text-[var(--ink)]">
                          {po.po_number}
                        </td>
                        <td className="py-3 px-4 font-sans text-[var(--ink)] font-medium">
                          {po.vendor_name}
                        </td>
                        <td className="py-3 px-4 font-sans text-[13px] text-[var(--ink-2)]">
                          {formatDate(po.po_date)}
                        </td>
                        <td className="py-3 px-4">
                          <span className="inline-flex items-center gap-1.5 text-[13px] font-sans">
                            <span
                              className={`w-2 h-2 rounded-full ${
                                po.status === "OPEN" ? "bg-[var(--approve)]" : "bg-[var(--ink-3)]"
                              }`}
                            />
                            <span className={po.status === "OPEN" ? "text-[var(--ink)]" : "text-[var(--ink-3)]"}>
                              {po.status === "OPEN" ? "Open" : "Closed"}
                            </span>
                          </span>
                        </td>
                        <td className="py-3 px-4 text-right">
                          <Money amount={netRupees} />
                        </td>
                        <td className="py-3 px-4">
                          <ConsumptionBar billedPct={po.billed_pct} width="160px" />
                        </td>
                      </tr>

                      {/* Expanded Section */}
                      {isExpanded && (
                        <tr>
                          <td colSpan={7} className="p-0 bg-[var(--surface-sunken)] border-b border-[var(--line)]">
                            <div className="p-6 space-y-6">
                              {/* 1. Line Items Breakdown */}
                              <div>
                                <span className="font-heading font-semibold text-[11px] leading-[16px] uppercase tracking-[0.08em] text-[var(--ink-3)] block mb-2 select-none">
                                  Ordered Lines Breakdown
                                </span>
                                <div className="overflow-x-auto border border-[var(--line)] rounded-[8px] bg-[var(--surface)]">
                                  <table className="w-full text-left text-[13px]">
                                    <thead className="bg-[var(--surface-sunken)] border-b border-[var(--line)]">
                                      <tr>
                                        <th className="py-2 px-3 font-heading font-semibold text-[11px] uppercase text-[var(--ink-3)]">
                                          Line
                                        </th>
                                        <th className="py-2 px-3 font-heading font-semibold text-[11px] uppercase text-[var(--ink-3)]">
                                          Description
                                        </th>
                                        <th className="py-2 px-3 font-heading font-semibold text-[11px] uppercase text-[var(--ink-3)] text-right">
                                          Ordered
                                        </th>
                                        <th className="py-2 px-3 font-heading font-semibold text-[11px] uppercase text-[var(--ink-3)] text-right">
                                          Billed
                                        </th>
                                        <th className="py-2 px-3 font-heading font-semibold text-[11px] uppercase text-[var(--ink-3)] text-right">
                                          Remaining
                                        </th>
                                        <th className="py-2 px-3 font-heading font-semibold text-[11px] uppercase text-[var(--ink-3)] text-right">
                                          Unit Price
                                        </th>
                                        <th className="py-2 px-3 font-heading font-semibold text-[11px] uppercase text-[var(--ink-3)] text-right">
                                          GST
                                        </th>
                                      </tr>
                                    </thead>
                                    <tbody className="divide-y divide-[var(--line)] font-mono">
                                      {po.lines.map((line) => {
                                        const remNum = parseFloat(line.remaining_quantity);
                                        const isOver = remNum < 0;

                                        return (
                                          <tr key={line.line_no}>
                                            <td className="py-2 px-3">{line.line_no}</td>
                                            <td className="py-2 px-3 font-sans font-medium text-[var(--ink)]">
                                              {line.description}
                                            </td>
                                            <td className="py-2 px-3 text-right">
                                              {line.quantity} {line.uom}
                                            </td>
                                            <td className="py-2 px-3 text-right">
                                              {line.billed_quantity} {line.uom}
                                            </td>
                                            <td
                                              className={`py-2 px-3 text-right font-semibold ${
                                                isOver ? "text-[var(--reject)]" : "text-[var(--ink)]"
                                              }`}
                                            >
                                              {line.remaining_quantity} {line.uom}
                                            </td>
                                            <td className="py-2 px-3 text-right">
                                              <Money amount={line.unit_price} />
                                            </td>
                                            <td className="py-2 px-3 text-right">
                                              {line.tax_rate_percent || "18"}%
                                            </td>
                                          </tr>
                                        );
                                      })}
                                    </tbody>
                                  </table>
                                </div>
                              </div>

                              {/* 2. Invoices History against PO */}
                              <div>
                                <span className="font-heading font-semibold text-[11px] leading-[16px] uppercase tracking-[0.08em] text-[var(--ink-3)] block mb-2 select-none">
                                  Invoices against this PO
                                </span>
                                {expandedLoading ? (
                                  <Skeleton width="100%" height="80px" />
                                ) : expandedDetail?.invoices && expandedDetail.invoices.length > 0 ? (
                                  <div className="overflow-x-auto border border-[var(--line)] rounded-[8px] bg-[var(--surface)]">
                                    <table className="w-full text-left text-[13px]">
                                      <thead className="bg-[var(--surface-sunken)] border-b border-[var(--line)]">
                                        <tr>
                                          <th className="py-2 px-3 font-heading font-semibold text-[11px] uppercase text-[var(--ink-3)]">
                                            Invoice Number
                                          </th>
                                          <th className="py-2 px-3 font-heading font-semibold text-[11px] uppercase text-[var(--ink-3)]">
                                            Date
                                          </th>
                                          <th className="py-2 px-3 font-heading font-semibold text-[11px] uppercase text-[var(--ink-3)] text-right">
                                            Amount
                                          </th>
                                          <th className="py-2 px-3 font-heading font-semibold text-[11px] uppercase text-[var(--ink-3)]">
                                            Status
                                          </th>
                                          <th className="py-2 px-3 font-heading font-semibold text-[11px] uppercase text-[var(--ink-3)]">
                                            Source
                                          </th>
                                        </tr>
                                      </thead>
                                      <tbody className="divide-y divide-[var(--line)]">
                                        {expandedDetail.invoices.map((inv) => (
                                          <tr key={inv.id}>
                                            <td className="py-2 px-3 font-mono font-medium text-[var(--ink)]">
                                              {inv.invoice_number || "—"}
                                            </td>
                                            <td className="py-2 px-3 font-sans text-[var(--ink-2)]">
                                              {formatDate(inv.invoice_date)}
                                            </td>
                                            <td className="py-2 px-3 text-right">
                                              <Money amount={inv.grand_total ? inv.grand_total.replace(/[^\d.]/g, "") : null} />
                                            </td>
                                            <td className="py-2 px-3">
                                              <span
                                                className={`text-[12px] font-sans font-semibold px-2 py-0.5 rounded-[4px] border ${
                                                  inv.status === "APPROVED"
                                                    ? "bg-[var(--approve-tint)] border-[var(--approve-line)] text-[var(--approve)]"
                                                    : inv.status === "ON_HOLD"
                                                    ? "bg-[var(--hold-tint)] border-[var(--hold-line)] text-[var(--hold)]"
                                                    : inv.status === "REJECTED"
                                                    ? "bg-[var(--reject-tint)] border-[var(--reject-line)] text-[var(--reject)]"
                                                    : "bg-[var(--review-tint)] border-[var(--review-line)] text-[var(--review)]"
                                                }`}
                                              >
                                                {inv.status}
                                              </span>
                                            </td>
                                            <td className="py-2 px-3 font-sans text-[12px] text-[var(--ink-3)]">
                                              {inv.source === "seed" ? (
                                                <span>seeded history</span>
                                              ) : inv.run_id ? (
                                                <Link
                                                  to={`/runs/${inv.run_id}`}
                                                  className="inline-flex items-center gap-1 font-mono text-[var(--ink)] hover:underline"
                                                >
                                                  <span>run {inv.run_id.slice(0, 8)}</span>
                                                  <ExternalLink size={12} strokeWidth={1.5} />
                                                </Link>
                                              ) : (
                                                <span>run</span>
                                              )}
                                            </td>
                                          </tr>
                                        ))}
                                      </tbody>
                                    </table>
                                  </div>
                                ) : (
                                  <div className="text-[13px] text-[var(--ink-3)] p-4 bg-[var(--surface)] border border-[var(--line)] rounded-[8px]">
                                    No prior invoices recorded for this purchase order.
                                  </div>
                                )}
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* 3. Vendors Master Card */}
      <div className="bg-[var(--surface)] border border-[var(--line)] rounded-[10px] p-6 shadow-[var(--shadow-1)] space-y-4">
        <div>
          <h2 className="font-heading font-semibold text-[18px] text-[var(--ink)]">
            Vendor Master Registry
          </h2>
          <p className="font-sans text-[13px] text-[var(--ink-2)] mt-0.5">
            Active and archived suppliers configured for Kestrel Foods Pvt. Ltd.
          </p>
        </div>

        {vendorsLoading ? (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} width="100%" height="40px" />
            ))}
          </div>
        ) : (
          <div className="overflow-x-auto border border-[var(--line)] rounded-[8px]">
            <table className="w-full text-left text-[13px]">
              <thead className="bg-[var(--surface-sunken)] border-b border-[var(--line)]">
                <tr>
                  <th className="py-2.5 px-3 font-heading font-semibold text-[11px] uppercase text-[var(--ink-3)]">
                    Vendor
                  </th>
                  <th className="py-2.5 px-3 font-heading font-semibold text-[11px] uppercase text-[var(--ink-3)]">
                    GSTIN
                  </th>
                  <th className="py-2.5 px-3 font-heading font-semibold text-[11px] uppercase text-[var(--ink-3)]">
                    Status
                  </th>
                  <th className="py-2.5 px-3 font-heading font-semibold text-[11px] uppercase text-[var(--ink-3)]">
                    Bank
                  </th>
                  <th className="py-2.5 px-3 font-heading font-semibold text-[11px] uppercase text-[var(--ink-3)] text-right">
                    Terms
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--line)]">
                {vendors?.map((v) => (
                  <tr key={v.vendor_id}>
                    <td className="py-2.5 px-3 font-sans font-medium text-[var(--ink)]">
                      <div>{v.legal_name}</div>
                      <div className="font-mono text-[11px] text-[var(--ink-3)]">{v.vendor_id}</div>
                    </td>
                    <td className="py-2.5 px-3 font-mono text-[var(--ink-2)]">{v.gstin}</td>
                    <td className="py-2.5 px-3">
                      <span className="inline-flex items-center gap-1.5 text-[12px] font-sans">
                        <span
                          className={`w-2 h-2 rounded-full ${
                            v.status === "ACTIVE" ? "bg-[var(--approve)]" : "bg-[var(--ink-3)]"
                          }`}
                        />
                        <span className={v.status === "ACTIVE" ? "text-[var(--ink)]" : "text-[var(--ink-3)]"}>
                          {v.status === "ACTIVE" ? "Active" : "Inactive"}
                        </span>
                      </span>
                    </td>
                    <td className="py-2.5 px-3 font-mono text-[12px] text-[var(--ink-2)]">
                      {v.bank_name} {v.bank_account_masked}
                    </td>
                    <td className="py-2.5 px-3 font-mono text-[13px] text-right text-[var(--ink)]">
                      {v.payment_terms_days} days
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
