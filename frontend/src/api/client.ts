// In dev: relative URLs are proxied by Vite to the backend.
// In production (Tauri): no Vite server exists, so we must use an absolute URL.
let backendBase: string = import.meta.env.DEV ? "" : "http://127.0.0.1:9001";

export function setPort(port: string) {
  backendBase = `http://127.0.0.1:${port}`;
}

/** Returns a full URL for SSE EventSource connections. */
export function getStreamUrl(path: string): string {
  return `${backendBase}${path}`;
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const res = await fetch(`${backendBase}/api/v1${path}`, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${res.status} ${text || res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export async function checkBackendOnline(): Promise<boolean> {
  try {
    const res = await fetch(`${backendBase}/health`, { signal: AbortSignal.timeout(3000) });
    return res.ok;
  } catch {
    return false;
  }
}
