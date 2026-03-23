import { apiFetch } from "./client";

export interface DownloadJob {
  job_id: string;
  url: string;
  format: string;
  quality: string;
  status: string;
  title: string;
  artist: string;
  platform: string;
  thumbnail_url: string;
  progress_pct: number;
  speed: number;
  eta: number;
  filepath: string;
  error: string;
}

export interface DetectResult {
  platform: string;
  valid: boolean;
  type: string;
  title: string;
  thumbnail_url: string;
  duration: number;
  uploader: string;
}

export const downloadApi = {
  start: (url: string, format: string, quality: string, outputDir: string) =>
    apiFetch<DownloadJob>("/download/start", {
      method: "POST",
      body: JSON.stringify({ url, format, quality, output_dir: outputDir }),
    }),

  batch: (urls: string[], format: string, quality: string, outputDir: string) =>
    apiFetch<{ job_ids: string[] }>("/download/batch", {
      method: "POST",
      body: JSON.stringify({ urls, format, quality, output_dir: outputDir }),
    }),

  status: (jobId: string) =>
    apiFetch<DownloadJob>(`/download/status/${jobId}`),

  cancel: (jobId: string) =>
    apiFetch<{ ok: boolean }>(`/download/cancel/${jobId}`, { method: "DELETE" }),

  detect: (url: string) =>
    apiFetch<DetectResult>(`/download/detect?url=${encodeURIComponent(url)}`),
};
