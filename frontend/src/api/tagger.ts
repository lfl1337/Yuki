import { apiFetch } from "./client";

export interface BatchSaveResponse {
  success: string[]
  failed: { file: string; error: string }[]
  total: number
  succeeded: number
  failed_count: number
}

export interface TagsData {
  filepath: string;
  title: string;
  artist: string;
  album: string;
  album_artist: string;
  year: string;
  genre: string;
  track_number: string;
  total_tracks: string;
  disc_number: string;
  bpm: string;
  composer: string;
  comment: string;
  cover_art_b64: string | null;
  filesize: number;
  duration: number;
  filename: string;
  format?: string;
}

export const taggerApi = {
  read: (filepath: string) =>
    apiFetch<TagsData>("/tagger/read", {
      method: "POST",
      body: JSON.stringify({ filepath }),
    }),

  write: (data: Partial<TagsData> & { filepath: string }) =>
    apiFetch<{ ok: boolean }>("/tagger/write", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  coverFromUrl: (url: string) =>
    apiFetch<{ cover_art_b64: string }>("/tagger/cover-from-url", {
      method: "POST",
      body: JSON.stringify({ url }),
    }),

  rename: (filepath: string, newName: string) =>
    apiFetch<{ ok: boolean; new_filepath?: string; error?: string }>("/tagger/rename", {
      method: "POST",
      body: JSON.stringify({ filepath, new_name: newName }),
    }),

  autoName: (filepath: string) =>
    apiFetch<{ suggested_name: string }>(`/tagger/auto-name?filepath=${encodeURIComponent(filepath)}`),

  batchSave: (filepaths: string[], tags: Record<string, string>) =>
    apiFetch<BatchSaveResponse>('/tagger/batch-save', {
      method: 'POST',
      body: JSON.stringify({ filepaths, tags }),
    }),
};
