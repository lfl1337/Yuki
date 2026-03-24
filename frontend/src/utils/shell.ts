/** Open a file's containing folder in the OS file explorer.
 *
 * Strategy:
 *  1. Try Tauri shell plugin open() — works inside a Tauri window.
 *  2. Fall back to POST /api/v1/system/open-folder — works if Tauri API
 *     is unavailable or the shell plugin returns an error. */
export async function openFolder(filepath: string): Promise<void> {
  if (!filepath) return

  // Get the directory part (handles both \ and /)
  const folder = filepath.replace(/[/\\][^/\\]+$/, '') || filepath

  // 1. Tauri shell plugin
  try {
    const { open } = await import('@tauri-apps/plugin-shell')
    await open(folder)
    return
  } catch {
    // Tauri not available, or shell plugin error — fall through to backend
  }

  // 2. Backend fallback via explorer subprocess
  try {
    await fetch('/api/v1/system/open-folder', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: filepath }),
    })
  } catch {
    // Nothing we can do
  }
}
