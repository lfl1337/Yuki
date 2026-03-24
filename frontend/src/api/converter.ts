import { apiFetch } from "./client";

export interface ConversionJob {
  job_id: string;
  input_path: string;
  output_path: string;
  status: string;
  progress_pct: number;
  error: string;
}

export interface QualitySettings {
  audio_bitrate?: string;
  sample_rate?: string;
  video_resolution?: string;
  video_codec?: string;
  video_audio_bitrate?: string;
}

export const converterApi = {
  start: (
    files: string[],
    outputFormat: string,
    quality: QualitySettings,
    outputDir: string,
    options?: {
      filename_mode?: string;
      filename_suffix?: string;
      filename_pattern?: string;
      create_subfolder?: boolean;
    }
  ) =>
    apiFetch<{ job_ids: string[] }>("/converter/start", {
      method: "POST",
      body: JSON.stringify({
        files,
        output_format: outputFormat,
        quality,
        output_dir: outputDir,
        ...options,
      }),
    }),

  status: (jobId: string) =>
    apiFetch<ConversionJob>(`/converter/status/${jobId}`),

  cancel: (jobId: string) =>
    apiFetch<{ ok: boolean }>(`/converter/cancel/${jobId}`, { method: "DELETE" }),
};
