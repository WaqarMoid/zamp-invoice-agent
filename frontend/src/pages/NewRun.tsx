import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Info, Play, Loader2 } from "lucide-react";
import { api } from "../lib/api";
import type { Sample } from "../lib/types";
import { PageHeader } from "../components/PageHeader";
import { Dropzone } from "../components/Dropzone";
import { Button } from "../components/Button";
import { DecisionBadge } from "../components/DecisionBadge";
import { Dialog } from "../components/Dialog";
import { Skeleton } from "../components/Skeleton";
import { useToast } from "../components/Toast";

export const NewRunPage: React.FC = () => {
  const navigate = useNavigate();
  const { showToast } = useToast();
  const [useCache, setUseCache] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [previewSample, setPreviewSample] = useState<Sample | null>(null);
  const [runningSampleId, setRunningSampleId] = useState<string | null>(null);

  // Fetch samples
  const { data: samples, isLoading: samplesLoading } = useQuery({
    queryKey: ["samples"],
    queryFn: () => api.getSamples(),
  });

  const handleFileUpload = async (file: File) => {
    setUploading(true);
    try {
      const res = await api.createRunFromFile(file, useCache);
      showToast(`Run initiated for ${file.name}`);
      navigate(`/runs/${res.run_id}`);
    } catch (err: any) {
      showToast(`Upload failed: ${err.message}`);
      setUploading(false);
    }
  };

  const handleRunSample = async (sample: Sample) => {
    setRunningSampleId(sample.id);
    try {
      const res = await api.createRunFromSample(sample.id, useCache);
      showToast(`Run initiated for ${sample.id}`);
      navigate(`/runs/${res.run_id}`);
    } catch (err: any) {
      showToast(`Failed to start sample run: ${err.message}`);
      setRunningSampleId(null);
    }
  };

  // Group samples
  const groupedSamples = React.useMemo(() => {
    if (!samples) return {};
    const groups: Record<string, Sample[]> = {
      "Happy path": [],
      "Edge cases": [],
      "More scenarios": [],
    };
    for (const s of samples) {
      if (groups[s.group]) {
        groups[s.group].push(s);
      } else {
        groups[s.group] = [s];
      }
    }
    return groups;
  }, [samples]);

  return (
    <div className="space-y-6">
      {/* 1. Page Header */}
      <PageHeader
        title="Process invoice"
        description="Upload an invoice or select a verified test scenario to run through the AP pipeline."
      />

      {/* 2. Info Line */}
      <div className="flex items-center gap-2 p-3 bg-[var(--surface)] border border-[var(--line)] rounded-[8px] text-[13px] leading-[20px] text-[var(--ink-2)]">
        <Info size={16} strokeWidth={1.5} className="text-[var(--ink-3)] shrink-0" />
        <span>
          Runs execute one at a time. Each run reads the invoice, checks it against the vendor
          master, the PO ledger and prior invoices, then decides.
        </span>
      </div>

      {/* 3. Two-Column Layout (7 / 5) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left Column (7 cols): Upload */}
        <div className="lg:col-span-7 bg-[var(--surface)] border border-[var(--line)] rounded-[10px] p-6 shadow-[var(--shadow-1)] space-y-5">
          <div className="flex items-center justify-between">
            <h2 className="font-heading font-semibold text-[18px] leading-[26px] text-[var(--ink)]">
              Upload an invoice
            </h2>
            {uploading && (
              <div className="flex items-center gap-2 text-[13px] text-[var(--ink-2)] font-mono">
                <Loader2 size={14} className="animate-spin text-[var(--ink)]" />
                <span>Uploading...</span>
              </div>
            )}
          </div>

          <Dropzone onFileSelect={handleFileUpload} />

          <div className="pt-2 border-t border-[var(--line)]">
            <label className="flex items-start gap-2.5 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={useCache}
                onChange={(e) => setUseCache(e.target.checked)}
                className="mt-1 w-4 h-4 rounded border-[var(--line-strong)] text-[var(--ink)] accent-[var(--ink)] focus:ring-0"
              />
              <div className="flex flex-col">
                <span className="font-sans text-[14px] text-[var(--ink)] font-medium">
                  Use cached extraction when the same file was read before
                </span>
                <span className="font-sans text-[12px] text-[var(--ink-3)]">
                  Turn off to watch the model read the document live.
                </span>
              </div>
            </label>
          </div>
        </div>

        {/* Right Column (5 cols): Sample Invoices */}
        <div className="lg:col-span-5 bg-[var(--surface)] border border-[var(--line)] rounded-[10px] p-6 shadow-[var(--shadow-1)] space-y-6">
          <h2 className="font-heading font-semibold text-[18px] leading-[26px] text-[var(--ink)]">
            Sample invoices
          </h2>

          {samplesLoading ? (
            <div className="space-y-4">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="space-y-2 py-2 border-b border-[var(--line)] last:border-b-0">
                  <Skeleton width="60%" height="16px" />
                  <Skeleton width="40%" height="12px" />
                  <Skeleton width="90%" height="14px" />
                </div>
              ))}
            </div>
          ) : (
            <div className="space-y-6 divide-y divide-[var(--line)]">
              {Object.entries(groupedSamples).map(([groupName, groupItems], groupIdx) => (
                <div key={groupName} className={groupIdx > 0 ? "pt-5" : ""}>
                  <span className="font-heading font-semibold text-[11px] leading-[16px] uppercase tracking-[0.08em] text-[var(--ink-3)] block mb-3 select-none">
                    {groupName}
                  </span>

                  <div className="space-y-4">
                    {groupItems.map((sample) => {
                      const isRunning = runningSampleId === sample.id;

                      return (
                        <div
                          key={sample.id}
                          className="flex flex-col gap-1.5 p-3 rounded-[8px] bg-[var(--surface-sunken)] border border-[var(--line)] hover:border-[var(--line-strong)] transition-colors"
                        >
                          <div className="flex items-start justify-between gap-2">
                            <div>
                              <div className="font-sans font-semibold text-[14px] leading-[20px] text-[var(--ink)]">
                                {sample.title}
                              </div>
                              <div className="font-mono text-[11px] text-[var(--ink-3)] mt-0.5">
                                {sample.filename}
                              </div>
                            </div>
                            <div className="flex items-center gap-1.5 shrink-0">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => setPreviewSample(sample)}
                              >
                                Preview
                              </Button>
                              <Button
                                variant="secondary"
                                size="sm"
                                icon={!isRunning && <Play size={12} strokeWidth={1.5} />}
                                loading={isRunning}
                                onClick={() => handleRunSample(sample)}
                              >
                                Run
                              </Button>
                            </div>
                          </div>

                          <p className="font-sans text-[12px] leading-[18px] text-[var(--ink-2)] line-clamp-2 m-0">
                            {sample.description}
                          </p>

                          <div className="flex items-center gap-2 pt-1">
                            <span className="font-sans text-[11px] text-[var(--ink-3)]">Expected:</span>
                            <DecisionBadge decision={sample.expected_decision} size="sm" />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* PDF Preview Dialog */}
      {previewSample && (
        <Dialog
          open={Boolean(previewSample)}
          onClose={() => setPreviewSample(null)}
          title={`Preview: ${previewSample.title}`}
          description={`${previewSample.filename} · Expected: ${previewSample.expected_decision}`}
          width="720px"
        >
          <div className="space-y-4">
            <div className="w-full h-[540px] bg-[var(--surface-sunken)] border border-[var(--line)] rounded-[8px] overflow-hidden">
              <iframe
                src={api.getSampleFileUrl(previewSample.id)}
                title={previewSample.title}
                className="w-full h-full border-0"
              />
            </div>
            <div className="flex items-center justify-between pt-2">
              <span className="font-sans text-[13px] text-[var(--ink-2)]">
                {previewSample.description}
              </span>
              <Button
                variant="primary"
                size="sm"
                icon={<Play size={14} strokeWidth={1.5} />}
                onClick={() => {
                  const s = previewSample;
                  setPreviewSample(null);
                  handleRunSample(s);
                }}
              >
                Run this scenario
              </Button>
            </div>
          </div>
        </Dialog>
      )}
    </div>
  );
};
