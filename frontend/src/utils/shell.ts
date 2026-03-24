import { apiFetch } from '../api/client'

/** Open a file's containing folder in Windows Explorer via the backend.
 * Uses the backend's /system/open-folder endpoint which calls explorer.exe.
 * Skips the Tauri shell plugin — it silently fails to open the window. */
export async function openFolder(filepath: string): Promise<void> {
  if (!filepath) return
  try {
    await apiFetch<{ ok: boolean }>('/system/open-folder', {
      method: 'POST',
      body: JSON.stringify({ path: filepath }),
    })
  } catch (e) {
    console.error('[Yuki] openFolder failed:', e)
  }
}
