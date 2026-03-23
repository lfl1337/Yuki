/** Open a file's containing folder in the OS file explorer.
 *  Uses the Tauri shell plugin; silently does nothing in browser context. */
export async function openFolder(filepath: string): Promise<void> {
  if (!filepath) return
  try {
    const { open } = await import('@tauri-apps/plugin-shell')
    // Strip the filename to get the directory (handles both \ and /)
    const folder = filepath.replace(/[/\\][^/\\]+$/, '') || filepath
    await open(folder)
  } catch {
    // Non-Tauri context or permission denied — no-op
  }
}
