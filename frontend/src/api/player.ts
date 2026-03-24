import { apiFetch } from "./client";

export interface PlayerStatus {
  is_playing: boolean;
  is_paused: boolean;
  position: number;
  duration: number;
  volume: number;
  filepath: string;
  title: string;
  artist: string;
  cover_art_b64: string | null;
}

export const playerApi = {
  load: (filepath: string) =>
    apiFetch<{ ok: boolean }>("/player/load", {
      method: "POST",
      body: JSON.stringify({ filepath }),
    }),

  play: () => apiFetch<{ ok: boolean }>("/player/play", { method: "POST" }),
  pause: () => apiFetch<{ ok: boolean }>("/player/pause", { method: "POST" }),
  stop: () => apiFetch<{ ok: boolean }>("/player/stop", { method: "POST" }),

  seek: (position: number) =>
    apiFetch<{ ok: boolean }>("/player/seek", {
      method: "POST",
      body: JSON.stringify({ position }),
    }),

  volume: (volume: number) =>
    apiFetch<{ ok: boolean }>("/player/volume", {
      method: "POST",
      body: JSON.stringify({ volume }),
    }),

  status: () => apiFetch<PlayerStatus>("/player/status"),
};
