import type {
  ConfigResponse,
  Decision,
  PurchaseOrder,
  PurchaseOrderDetail,
  ReviewRequest,
  RunDetail,
  RunStatus,
  RunSummary,
  Sample,
  Stats,
  Vendor,
} from "./types";

const API_BASE = import.meta.env.VITE_API_URL || "";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`;
  const response = await fetch(url, options);

  if (!response.ok) {
    let errorDetail = `HTTP ${response.status}: ${response.statusText}`;
    try {
      const data = await response.json();
      if (data && data.detail) {
        errorDetail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
      }
    } catch {
      // Keep default errorDetail
    }
    throw new Error(errorDetail);
  }

  return response.json();
}

export const api = {
  getHealth: () => request<{ status: string; version: string }>("/api/health"),
  getConfig: () => request<ConfigResponse>("/api/config"),
  getStats: () => request<Stats>("/api/stats"),
  getSamples: () => request<Sample[]>("/api/samples"),
  getSampleFileUrl: (id: string) => `${API_BASE}/api/samples/${id}/file`,

  getRuns: (params?: {
    decision?: Decision;
    status?: RunStatus;
    q?: string;
    limit?: number;
    offset?: number;
  }) => {
    const search = new URLSearchParams();
    if (params?.decision) search.set("decision", params.decision);
    if (params?.status) search.set("status", params.status);
    if (params?.q) search.set("q", params.q);
    if (params?.limit !== undefined) search.set("limit", String(params.limit));
    if (params?.offset !== undefined) search.set("offset", String(params.offset));

    const qs = search.toString();
    return request<{ items: RunSummary[]; total: number }>(`/api/runs${qs ? `?${qs}` : ""}`);
  },

  getRun: (id: string) => request<RunDetail>(`/api/runs/${id}`),

  createRunFromSample: (sampleId: string, useCache = true) =>
    request<{ run_id: string; status: string }>("/api/runs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sample_id: sampleId, use_cache: useCache }),
    }),

  createRunFromFile: (file: File, useCache = true) => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("use_cache", String(useCache));

    return request<{ run_id: string; status: string }>("/api/runs", {
      method: "POST",
      body: formData,
    });
  },

  submitReview: (runId: string, payload: ReviewRequest) =>
    request<RunDetail>(`/api/runs/${runId}/review`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),

  getRunDocumentUrl: (id: string) => `${API_BASE}/api/runs/${id}/document`,
  getRunPageUrl: (id: string, page: number, dpi = 110) =>
    `${API_BASE}/api/runs/${id}/pages/${page}.png?dpi=${dpi}`,

  getVendors: () => request<Vendor[]>("/api/vendors"),
  getPurchaseOrders: () => request<PurchaseOrder[]>("/api/purchase-orders"),
  getPurchaseOrder: (poNumber: string) =>
    request<PurchaseOrderDetail>(`/api/purchase-orders/${encodeURIComponent(poNumber)}`),

  resetAdmin: () =>
    request<{ ok: boolean }>("/api/admin/reset", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ confirm: "RESET" }),
    }),
};
