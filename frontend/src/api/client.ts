// In dev: relative URLs are proxied by Vite to the backend.
// In production (Tauri): no Vite server exists, use absolute URL.
let backendBase: string = import.meta.env.DEV ? "" : "http://127.0.0.1:9001";

export function setPort(port: string | number) {
  // Only update in production — dev mode uses Vite proxy via relative URLs.
  if (!import.meta.env.DEV) {
    backendBase = `http://127.0.0.1:${port}`;
  }
}

export function getBase(): string {
  return backendBase;
}

/** Returns a full URL for SSE EventSource connections. */
export function getStreamUrl(path: string): string {
  return `${backendBase}${path}`;
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  // Use caller's signal if provided (e.g., for abort), otherwise enforce 10-second timeout
  const signal = (options as any)?.signal ?? AbortSignal.timeout(10_000);
  const res = await fetch(`${backendBase}/api/v1${path}`, {
    credentials: "omit",
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
    signal,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${res.status} ${text || res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export async function checkBackendOnline(): Promise<boolean> {
  try {
    const res = await fetch(`${backendBase}/health`, {
      credentials: "omit",
      signal: AbortSignal.timeout(3000),
    });
    return res.ok;
  } catch {
    return false;
  }
}
