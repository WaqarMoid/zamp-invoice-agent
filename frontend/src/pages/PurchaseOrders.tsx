import React from "react";

export const PurchaseOrdersPage: React.FC = () => {
  return (
    <div className="space-y-4">
      <div className="border-b border-slate-200 pb-4">
        <h1 className="text-2xl font-bold font-display text-slate-900">Purchase orders</h1>
        <p className="text-sm text-slate-600 mt-1">PO ledger and billed balance tracking.</p>
      </div>
      <div className="rounded-lg border border-dashed border-slate-300 p-12 text-center text-slate-500">
        Purchase orders list placeholder (P6e)
      </div>
    </div>
  );
};
