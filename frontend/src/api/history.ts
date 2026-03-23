import { apiFetch } from "./client";

export interface HistoryEntry {
  id: string;
  title: string;
  artist: string;
  platform: string;
  format: string;
  quality: string;
  filepath: string;
  thumbnail_url: string;
  duration: number;
  filesize: number;
  url: string;
  downloaded_at: string;
}

export interface HistoryPage {
  items: HistoryEntry[];
  total: number;
  pages: number;
}

export const historyApi = {
  get: (params: { search?: string; platform?: string; format?: string; page?: number; per_page?: number }) => {
    const q = new URLSearchParams();
    if (params.search) q.set("search", params.search);
    if (params.platform) q.set("platform", params.platform);
    if (params.format) q.set("format", params.format);
    if (params.page) q.set("page", String(params.page));
    if (params.per_page) q.set("per_page", String(params.per_page));
    return apiFetch<HistoryPage>(`/history?${q}`);
  },

  delete: (id: string) =>
    apiFetch<{ ok: boolean }>(`/history/${id}`, { method: "DELETE" }),

  clearAll: () =>
    apiFetch<{ ok: boolean }>("/history", { method: "DELETE" }),

  exportCsvUrl: () => "/api/v1/history/export",
};
