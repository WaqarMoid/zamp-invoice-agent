import React from "react";
import { useParams } from "react-router-dom";

export const RunDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();

  return (
    <div className="space-y-4">
      <div className="border-b border-slate-200 pb-4">
        <h1 className="text-2xl font-bold font-display text-slate-900">Run detail: {id}</h1>
        <p className="text-sm text-slate-600 mt-1">Live execution view and verification stages.</p>
      </div>
      <div className="rounded-lg border border-dashed border-slate-300 p-12 text-center text-slate-500">
        Run detail live view placeholder (P6d)
      </div>
    </div>
  );
};
