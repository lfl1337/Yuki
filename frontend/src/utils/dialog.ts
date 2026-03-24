/** Pick a directory using the Tauri dialog plugin.
 *  Returns the chosen path, or null if cancelled / not in Tauri context. */
export async function pickFolder(): Promise<string | null> {
  try {
    const { open } = await import('@tauri-apps/plugin-dialog')
    const result = await open({ directory: true, multiple: false })
    if (typeof result === 'string') return result
    return null
  } catch {
    return null
  }
}
