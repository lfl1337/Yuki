import { apiFetch } from './client'

/** Load all settings from the backend. Returns an empty object on error. */
export async function loadSettings(): Promise<Record<string, unknown>> {
  try {
    return await apiFetch<Record<string, unknown>>('/settings')
  } catch {
    return {}
  }
}

/** Partially update settings — only the supplied keys are written. */
export async function patchSettings(partial: Record<string, unknown>): Promise<void> {
  try {
    await apiFetch<{ ok: boolean }>('/settings', {
      method: 'PATCH',
      body: JSON.stringify(partial),
    })
  } catch {
    // Best-effort — don't throw on save failure
  }
}
