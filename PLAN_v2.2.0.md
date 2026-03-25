# Yuki v2.2.0 Implementation Plan
**Goal:** Security hardening, stability, performance optimization, bundle size reduction
**Core principle:** Fully self-contained, self-healing, zero user intervention needed
**Status:** Ready to execute

---

## Phase 0: Documentation Discovery (COMPLETE)

All relevant files have been read. Findings are grounded in actual source — no assumptions.

### Verified Good Patterns (DO NOT CHANGE)
- `lib.rs` CloseRequested: 3-layer kill (child.kill → taskkill → delete port file → exit(0)) ✓
- `lib.rs` startup: kills old process + deletes stale `.runtime_port` before spawning ✓
- `lib.rs` port discovery: invoke-based `get_backend_port()` stored in Tauri State ✓
- `spotify.py`: `CREATE_NO_WINDOW`, `timeout=600`, no `shell=True`, captures output ✓
- `updater.py`: `asyncio.create_subprocess_exec()`, no `shell=True`, proper await ✓
- SSE cleanup in `Downloader.tsx`, `Converter.tsx`, `PlayerBar.tsx`: all properly close on unmount ✓
- `capabilities/default.json`: minimal — only `core:default`, `shell:allow-open`, `shell:allow-kill`, `dialog:default` ✓
- `.gitignore`: covers `__pycache__/`, `*.pyc`, `*.spec`, `.env`, `build/`, `dist/`, `*.db`, `.runtime_port`, binaries ✓

### Confirmed Issues (verified line numbers)
See each phase for exact locations and fixes.

---

## Phase 1: Backend Stability & Resource Management

**Files:** `backend/app/logger.py`, `backend/app/services/player_engine.py`, `backend/app/services/player.py`, `backend/app/routers/player.py`, `backend/app/routers/tagger.py`

### 1.1 — Fix log rotation (logger.py:48-50)

**Problem:** Plain `FileHandler` — log grows unbounded. Lines 33-38 try to clean up old rotated files but rotation was never configured.

**Fix:** Replace `FileHandler` with `RotatingFileHandler`. Remove the now-pointless old-file cleanup loop (lines 33-38).

```python
# Replace (logger.py:48-50):
fh = logging.FileHandler(log_file, mode="a", encoding="utf-8")

# With:
from logging.handlers import RotatingFileHandler
fh = RotatingFileHandler(
    log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
)
```

Also remove lines 33-38 (the old startup cleanup loop for rotated files — no longer needed).

**Verification:** After fix, `logging.handlers.RotatingFileHandler` appears in logger.py. Old cleanup loop is gone.

### 1.2 — Fix relative import in player_engine.py (line 236)

**Problem:** `from config import PLAYER_UPDATE_INTERVAL_MS` — bare import, will fail in packaged context.

**Fix:**
```python
# Replace:
from config import PLAYER_UPDATE_INTERVAL_MS
# With:
from ..config import PLAYER_UPDATE_INTERVAL_MS
```

**Verification:** `grep -n "from config import" backend/app/services/player_engine.py` returns nothing.

### 1.3 — Add threading.Lock to player tag cache (player.py:25-30)

**Problem:** `_tag_cache` dict is accessed from both the main thread (load, notify_loaded) and the SSE generator thread without locking. Race condition.

**Fix:** Add `_cache_lock = threading.Lock()` at module level. Wrap every read and write to `_tag_cache` with `with _cache_lock:`.

```python
import threading
_tag_cache: dict[str, dict] = {}
_cache_lock = threading.Lock()

# In notify_loaded():
with _cache_lock:
    _tag_cache[filepath] = {...}

# In get_tag_cache():
with _cache_lock:
    return _tag_cache.get(filepath)
```

**Verification:** All `_tag_cache[` and `_tag_cache.get(` accesses are inside `with _cache_lock:` blocks.

### 1.4 — Wrap blocking file checks in async context

**Problem:** `Path(filepath).exists()` and `p.stat()` called directly in async endpoints — blocks the event loop.

**Files and lines:**
- `backend/app/routers/player.py:24` — `Path(body.filepath).exists()`
- `backend/app/routers/tagger.py:37` — `Path(body.filepath).exists()`
- `backend/app/routers/tagger.py:43` — `p.stat().st_size`
- `backend/app/routers/tagger.py:78` — `Path(body.filepath).exists()`
- `backend/app/routers/tagger.py:145` — `Path(filepath).exists()`

**Fix pattern:**
```python
# Replace:
if not Path(body.filepath).exists():
# With:
if not await asyncio.to_thread(Path(body.filepath).exists):
```
```python
# Replace:
size = p.stat().st_size
# With:
size = (await asyncio.to_thread(Path(body.filepath).stat)).st_size
```

**Verification:** `grep -n "Path(" backend/app/routers/player.py backend/app/routers/tagger.py | grep -v "to_thread"` — no bare `.exists()` or `.stat()` in async functions.

### 1.5 — Fix VERSION file duplicate line

**Problem:** `VERSION` file contains `2.1.3` on two lines due to `bump_version.py` using `r".*"` pattern which replaces ALL lines.

**Fix in `scripts/bump_version.py`:** Change the VERSION entry pattern:
```python
# Replace:
("VERSION", r".*", "{version}"),
# With:
("VERSION", r"^\d+\.\d+\.\d+$", "{version}"),
```

**Also fix `VERSION` file** — it should contain exactly one line: the version string.

**Verification:** `cat VERSION` returns exactly one line. Running `bump_version.py 2.2.0` updates only the version line.

### 1.6 — Add pyproject.toml to version bump targets

**Problem:** `backend/pyproject.toml` version is stuck at `2.0.0`. Not included in `bump_version.py`.

**Fix in `scripts/bump_version.py`:** Add to `FILES_TO_PATCH`:
```python
("backend/pyproject.toml", r'^version = "\d+\.\d+\.\d+"', 'version = "{version}"'),
```

Then manually update pyproject.toml version to `2.1.3` (current) before bumping to 2.2.0.

**Verification:** After running bump_version.py, `grep version backend/pyproject.toml` shows `version = "2.2.0"`.

---

## Phase 2: Security Hardening

**Files:** `backend/app/services/converter.py`, `backend/app/services/tagger.py`, `backend/app/main.py`, `backend/app/routers/download.py`, `backend/app/routers/player.py`, `backend/app/routers/tagger.py`

### 2.1 — Fix path traversal in converter filename_pattern (converter.py:106-110)

**Problem:** `filename_pattern.format(...)` is applied to user-supplied `pattern` without validation. A pattern like `../../sensitive/{name}` could write files outside the output directory.

**Fix:** After constructing `output_path`, validate it stays within the output directory:
```python
# After building output_path (line ~109):
output_path = Path(output_dir / formatted_filename).resolve()
allowed_dir = Path(output_dir).resolve()
if not str(output_path).startswith(str(allowed_dir) + os.sep) and output_path != allowed_dir:
    raise ValueError(f"Illegal filename pattern: path escapes output directory")
```

**Verification:** Unit test: pattern `"../../evil"` raises ValueError. Pattern `"{artist} - {title}"` works normally.

### 2.2 — Add image size/dimension validation in tagger service (tagger.py:418)

**Problem:** No size check before `Image.open()`. Maliciously crafted images (zip-bombs, decompression bombs) could exhaust memory.

**Fix in `backend/app/services/tagger.py` inside `_load_image_bytes()` or wherever PIL is called:**
```python
MAX_IMAGE_BYTES = 20 * 1024 * 1024  # 20 MB
MAX_IMAGE_PIXELS = 50_000_000  # 50 megapixels (~7071×7071)

if len(data) > MAX_IMAGE_BYTES:
    raise ValueError(f"Image too large ({len(data) // 1024 // 1024} MB, max 20 MB)")

Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS  # Pillow's built-in decompression bomb guard
img = Image.open(io.BytesIO(data))
img.verify()  # Raises on corrupt/malformed data
img = Image.open(io.BytesIO(data))  # Must re-open after verify()
img = img.convert("RGB")
```

Note: `Image.MAX_IMAGE_PIXELS` is a global — set it at module import time, not in the function.

**Verification:** Passing a 25 MB image returns an error. Normal cover art (< 1 MB) works.

### 2.3 — Tighten CORS configuration (main.py:59-68)

**Problem:** `http://localhost` (port 80) in allowed origins. Any app running a local HTTP server on port 80 can make requests to the Yuki backend.

**Fix:** Replace `"http://localhost"` with `"http://localhost:1421"` (specific Vite dev port only):
```python
allow_origins=[
    "http://localhost:1421",   # Vite dev server (specific port)
    "tauri://localhost",       # Tauri production
    "https://tauri.localhost", # Tauri production (alt)
],
```

**Verification:** `grep -n "allow_origins" backend/app/main.py` — no bare `http://localhost` without port.

### 2.4 — Add URL scheme validation in download router (download.py:42-44)

**Problem:** URL validation only checks for empty string. Non-HTTP schemes (file://, ftp://, javascript://) are not rejected.

**Fix in `backend/app/routers/download.py`:**
```python
from urllib.parse import urlparse

# In the validate-and-enqueue endpoint, after empty check:
parsed = urlparse(url.strip())
if parsed.scheme not in ("http", "https"):
    raise HTTPException(status_code=400, detail="URL must use http or https scheme")
```

Apply to both the single-URL endpoint and the batch endpoint.

**Verification:** `file:///etc/passwd` returns 400. `https://youtube.com/watch?v=...` proceeds normally.

### 2.5 — Add filepath validation in player and tagger routers

**Problem:** User-supplied `filepath` in player and tagger endpoints is not validated — potential path traversal to read arbitrary files.

**Fix:** Create a small validation helper, place it in `backend/app/utils/` or inline in each router:
```python
def _validate_filepath(filepath: str) -> Path:
    """Resolve and validate that filepath is an absolute path to an existing file."""
    p = Path(filepath).resolve()
    if not p.exists():
        raise HTTPException(status_code=404, detail="File not found")
    if not p.is_file():
        raise HTTPException(status_code=400, detail="Path is not a file")
    # Reject paths that escape to system directories
    forbidden = [Path("C:/Windows"), Path("C:/Program Files")]
    for f in forbidden:
        if str(p).startswith(str(f)):
            raise HTTPException(status_code=403, detail="Access denied")
    return p
```

Apply this validation at the start of every tagger endpoint that accepts `filepath`, and in the player load endpoint.

**Note:** The app is desktop-only and the user controls their own machine. The primary threat is a malicious URL that tricks yt-dlp into setting a filepath; absolute path validation mitigates this.

**Verification:** A request with `filepath="/etc/passwd"` returns 403 or 404.

### 2.6 — Create SECURITY.md

Document all findings, their severity, and how they were fixed. Template:

```markdown
# Yuki Security Documentation

## Audit Date: 2026-03-25
## Version: v2.2.0

### Fixed in v2.2.0

| ID | Severity | Component | Issue | Fix |
|----|----------|-----------|-------|-----|
| SEC-01 | High | converter.py:106 | Path traversal in filename_pattern | Resolve + validate against output dir |
| SEC-02 | Medium | tagger.py:418 | No image size validation (DoS) | 20 MB limit + MAX_IMAGE_PIXELS |
| SEC-03 | Medium | main.py:68 | Overly broad CORS (http://localhost) | Restrict to :1421 + tauri:// |
| SEC-04 | Medium | download.py:42 | No URL scheme validation | Reject non-http(s) schemes |
| SEC-05 | Medium | player.py/tagger.py | No filepath validation | Resolve + existence check |
| SEC-06 | Low | client.ts:25 | No request timeout | AbortSignal.timeout(10s) |

### Architecture Security Notes
- Backend binds only to 127.0.0.1 (localhost only)
- No shell=True in any subprocess call
- Frontend uses credentials: "omit" on all requests
- CSP restricts scripts to 'self' only
- All outgoing requests use HTTPS with timeouts
```

---

## Phase 3: Frontend Memory Leak Fixes

**Files:** `frontend/src/api/client.ts`, `frontend/src/components/PlayerBar.tsx`, `frontend/src/views/Editor.tsx`, `frontend/src/App.tsx`, `frontend/src/components/Settings.tsx`, `frontend/src/components/Sidebar.tsx`, `frontend/src/api/settings.ts`

### 3.1 — Add timeout to apiFetch (client.ts:25)

**Problem:** `apiFetch()` has no timeout. Any request can hang indefinitely (if backend freezes mid-request, the frontend hangs too).

**Fix in `frontend/src/api/client.ts`:**
```typescript
export async function apiFetch<T>(url: string, options?: RequestInit): Promise<T> {
  // Use caller's signal if provided, otherwise enforce 10s timeout
  const signal = (options as RequestInit & { signal?: AbortSignal })?.signal
    ?? AbortSignal.timeout(10_000);

  const response = await fetch(url, {
    ...options,
    signal,
    credentials: "omit",
  });
  if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  return response.json() as Promise<T>;
}
```

**Note:** SSE connections use `new EventSource()` directly, NOT `apiFetch`. This timeout does not affect streaming.

**Verification:** A request to a non-responsive endpoint resolves with an AbortError after ~10 seconds rather than hanging forever.

### 3.2 — Fix PlayerBar untracked setTimeout (PlayerBar.tsx:91)

**Problem:** `setTimeout(() => playerApi.play(), 100)` created in a useEffect with no cleanup. Timer can fire after unmount.

**Fix:** Store the ID and clear it:
```typescript
// Find the useEffect that has the setTimeout on line ~91
useEffect(() => {
  if (/* repeat condition */) {
    const id = setTimeout(() => playerApi.play(), 100);
    return () => clearTimeout(id);
  }
}, [/* deps */]);
```

**Verification:** `grep -n "setTimeout" frontend/src/components/PlayerBar.tsx` — every setTimeout has a corresponding clearTimeout in the cleanup return.

### 3.3 — Fix Editor.tsx async setState after unmount (Editor.tsx:115-118)

**Problem:** `loadFile()` is an async function called in useEffect. If the component unmounts mid-request, `setLoading(false)` / `setTags(...)` fire on an unmounted component.

**Fix:** Add a `mounted` flag:
```typescript
useEffect(() => {
  let mounted = true;

  async function load() {
    if (!filePath) return;
    setLoading(true);
    try {
      const [tags, cover] = await Promise.all([
        taggerApi.read(filePath),
        taggerApi.getCover(filePath),
      ]);
      if (mounted) {
        setTags(tags);
        setCover(cover);
      }
    } catch (e) {
      if (mounted) setError(String(e));
    } finally {
      if (mounted) setLoading(false);
    }
  }

  load();
  return () => { mounted = false; };
}, [filePath]);
```

**Verification:** The useEffect that loads file data has `let mounted = true` and `return () => { mounted = false; }`.

### 3.4 — Fix Editor.tsx FileReader cleanup (Editor.tsx:153-158, 222-226)

**Problem:** `FileReader.onload` callbacks call `setState` without checking if component is still mounted.

**Fix:** Use the same `mounted` flag pattern or check via `useRef`:
```typescript
// In cover art change handler:
const coverReader = new FileReader();
coverReader.onload = (e) => {
  if (!mountedRef.current) return;
  setCoverPreview(e.target?.result as string);
};
coverReader.readAsDataURL(file);
```

Add `const mountedRef = useRef(true)` to the component, and set it to `false` in a cleanup useEffect:
```typescript
useEffect(() => {
  mountedRef.current = true;
  return () => { mountedRef.current = false; };
}, []);
```

**Verification:** FileReader onload callbacks reference `mountedRef.current` before calling setState.

### 3.5 — Fix App.tsx useEffect missing cleanup (App.tsx:49)

**Problem:** The settings-loading useEffect (line 49) has no cleanup return. If the component unmounts before the fetch resolves, setState fires on unmounted component.

**Fix:**
```typescript
useEffect(() => {
  let mounted = true;
  apiFetch<Record<string, string>>('/settings')
    .then(data => { if (mounted) applySettings(data); })
    .catch(() => {});
  return () => { mounted = false; };
}, []);
```

**Verification:** The settings-load useEffect has a return cleanup function.

### 3.6 — Fix Settings.tsx async tracking (Settings.tsx:72-77)

**Problem:** `loadSettings()` called in useEffect without a mounted flag or cleanup.

**Fix:**
```typescript
useEffect(() => {
  if (!isOpen) return;
  let mounted = true;
  loadSettings().then(() => {
    // loadSettings itself sets state via setState calls
    // Add mounted checks inside loadSettings, or use the flag here
  }).catch(console.error);
  return () => { mounted = false; };
}, [isOpen]);
```

**Verification:** Settings useEffect has a return function.

### 3.7 — Remove console.logs from Sidebar.tsx (lines 25-34)

**Problem:** Multiple `console.log` calls expose backend URL and health check status in production.

**Fix:** Remove all `console.log` and `console.error` calls in Sidebar.tsx, OR guard them:
```typescript
if (import.meta.env.DEV) {
  console.log('[Sidebar] health check:', ...);
}
```

Prefer removal entirely — the green/red dot provides all the visual feedback needed.

**Verification:** `grep -n "console\." frontend/src/components/Sidebar.tsx` — no unguarded console calls.

### 3.8 — Add error logging to settings.ts (lines 7, 19)

**Problem:** `catch` blocks swallow errors silently. Settings failures go completely unnoticed.

**Fix:**
```typescript
} catch (error) {
  console.error('[settings] failed to load settings:', error);
  return {};
}
```

**Verification:** `grep -A2 "catch" frontend/src/api/settings.ts` — catch blocks log errors.

---

## Phase 4: Tauri Single-Instance Enforcement

**Files:** `frontend/src-tauri/Cargo.toml`, `frontend/src-tauri/src/lib.rs`, `frontend/src-tauri/capabilities/default.json`

### 4.1 — Add single-instance plugin

**Problem:** No single-instance enforcement. If user double-clicks the Yuki icon while it's already running, a second instance starts, spawning a second backend, causing port conflicts.

**Add to `Cargo.toml` `[dependencies]`:**
```toml
tauri-plugin-single-instance = "2"
```

**Add to `lib.rs` in `run()` before `.manage(...)` calls:**
```rust
.plugin(
    tauri_plugin_single_instance::init(|app, _argv, _cwd| {
        // Focus the existing window when a second instance tries to start
        if let Some(window) = app.get_webview_window("main") {
            let _ = window.show();
            let _ = window.set_focus();
            let _ = window.unminimize();
        }
    })
)
```

**No capability entry needed** — single-instance is handled entirely in Rust, not exposed to frontend.

**Verification:** Build and run Yuki. Double-click shortcut while Yuki is open. Existing window comes to front instead of a second window opening.

---

## Phase 5: Performance Optimization

**Files:** `backend/app/services/tagger.py`, `frontend/src/App.tsx`, `frontend/src/components/HistoryCard.tsx`

### 5.1 — Lazy-load heavy imports in tagger service

**Problem:** `requests` is imported at module top-level in `tagger.py` service but only used in `_load_image_bytes()` (URL cover art fetching). PIL is imported at module level but only used in cover art operations.

**Fix:** Move `requests` import inside the function that uses it:
```python
# In _load_image_bytes() or wherever requests.get() is called:
def _load_image_bytes(source: str, timeout: int = 10) -> bytes:
    import requests  # lazy — only loaded when cover URL is fetched
    response = requests.get(source, timeout=timeout)
    ...
```

PIL (`from PIL import Image`) is used in more places — keep at top level but note this is acceptable since it's in the service layer, not at import time.

**Verification:** `grep -n "^import requests" backend/app/services/tagger.py` returns nothing.

### 5.2 — Add React.lazy() for heavy views

**Problem:** `Editor.tsx`, `Converter.tsx` are large components loaded eagerly on startup. Settings modal is also loaded eagerly.

**Fix in `frontend/src/App.tsx`:**
```typescript
import React, { lazy, Suspense } from 'react';

// Replace direct imports:
const Editor = lazy(() => import('./views/Editor'));
const Converter = lazy(() => import('./views/Converter'));

// Keep Downloader and History as eager (they are the main views)
import Downloader from './views/Downloader';
import History from './views/History';
```

Wrap routes in Suspense:
```tsx
<Suspense fallback={<div className="flex items-center justify-center h-full text-text2">Loading…</div>}>
  <Routes>
    <Route path="/" element={<Downloader />} />
    <Route path="/history" element={<History />} />
    <Route path="/editor" element={<Editor />} />
    <Route path="/converter" element={<Converter />} />
  </Routes>
</Suspense>
```

**Note:** Do NOT lazy-load Settings component — it's a modal that opens from within the already-loaded layout. Lazy-loading it would cause a flash.

**Verification:** After build, `dist/assets/` contains separate chunk files for Editor and Converter. Network tab shows they load on first navigation to those views.

### 5.3 — Add lazy loading to history thumbnails (HistoryCard.tsx)

**Problem:** All history thumbnails load immediately, even those not visible in the viewport.

**Fix in `frontend/src/components/HistoryCard.tsx`:** Add `loading="lazy"` to all `<img>` elements:
```tsx
<img
  src={entry.thumbnail}
  alt=""
  loading="lazy"
  onError={...}
  className="..."
/>
```

**Verification:** `grep -n '<img' frontend/src/components/HistoryCard.tsx` — all img tags have `loading="lazy"`.

### 5.4 — Debounce search input in History (verify/add)

**Check:** History.tsx already has a 300ms debounce on search (line 59). This is correct — no change needed.

---

## Phase 6: Bundle Size Reduction

**Files:** `scripts/build_backend.py`

### 6.1 — Measure BEFORE sizes

Before making any PyInstaller changes, record:
```
backend exe:     scripts\build_backend.py output size (MB)
installer:       Yuki_2.1.3_x64-setup.exe size (MB)
frontend dist/:  du -sh frontend/dist/
```
Document in commit message.

### 6.2 — Add --exclude-module flags to PyInstaller build

**Problem:** No `--exclude-module` flags. PyInstaller pulls in many unused stdlib modules.

**Add to `scripts/build_backend.py`:**
```python
EXCLUDE_MODULES = [
    "tkinter", "_tkinter", "tcl", "tk",
    "unittest", "test", "tests",
    "distutils", "setuptools", "pip", "ensurepip",
    "lib2to3", "idlelib", "pydoc_data", "turtledemo",
    "doctest", "turtle", "curses",
    "antigravity", "this",
    "xmlrpc.server", "ftplib",
    "http.server", "cgi", "cgitb",
    "numpy",   # add only if confirmed not used by any dep
    "pandas",  # add only if confirmed not used by any dep
    "scipy",   # add only if confirmed not used by any dep
    "matplotlib",  # add only if confirmed not used
]

# In cmd construction:
for mod in EXCLUDE_MODULES:
    cmd += ["--exclude-module", mod]
```

**Important:** Only exclude `numpy`/`pandas`/`scipy` after verifying they're not pulled in by `yt_dlp`, `spotdl`, or `Pillow`. Test the built exe before releasing.

### 6.3 — Add --clean flag

**Fix in `scripts/build_backend.py`:** Add `"--clean"` to cmd:
```python
cmd = [
    str(PYTHON), "-m", "PyInstaller",
    "--onefile",
    "--clean",          # <-- add this
    "--target-arch", "x86_64",
    ...
]
```

### 6.4 — Test UPX compression (optional, risk-assessed)

**Try:** Add `--upx-dir` to PyInstaller command with a local UPX binary. Measure size reduction.

**If UPX increases antivirus false positives:** Remove it. PyInstaller executables already trigger some AVs due to format abuse by malware. UPX can make this worse.

**Decision point:** Only keep UPX if size reduction > 20% AND no new AV detections.

### 6.5 — Measure AFTER sizes and document delta

Compare sizes after PyInstaller changes. Document in commit message:
```
Size before: backend=XX MB, installer=XX MB
Size after:  backend=XX MB, installer=XX MB
Delta:       -XX MB (XX%)
```

---

## Phase 7: Installer Verification

**Files:** `frontend/src-tauri/nsis/hooks.nsh` (READ FIRST — was not read by audit agents)

### 7.1 — Read and verify hooks.nsh

Read `frontend/src-tauri/nsis/hooks.nsh` to confirm it:
1. Kills both `Yuki.exe` AND `yuki-backend-x86_64-pc-windows-msvc.exe` before install
2. Uses `taskkill /f /im` for both
3. Has a short `Sleep` after kill to allow file handles to release

If hooks.nsh is correct from v2.1.3 work, no change needed.

### 7.2 — Verify uninstaller handles AppData cleanup

Tauri's NSIS installer uninstalls from `$INSTDIR` but does NOT remove `%APPDATA%\Yuki\` (settings, history, logs). This is INTENTIONAL — user data should persist across reinstalls.

For a clean uninstall, the uninstaller should ASK the user if they want to keep their data. Verify this prompt exists in Tauri's generated NSIS script, or add it to hooks.nsh.

**Note:** The legacy `installer.nsi` at the project root already has this prompt (line 149). Tauri's NSIS may need a similar hook.

---

## Phase 8: Build, Version Bump, and Release

Execute in this exact order:

### Step 1 — Record current sizes
```
dir frontend\src-tauri\binaries\yuki-backend-x86_64-pc-windows-msvc.exe
dir frontend\src-tauri\target\release\bundle\nsis\*.exe
```

### Step 2 — Run all tests (manual, per test checklist)
From `dev.bat`:
1. Download a YouTube video (mp4)
2. Download a YouTube audio (mp3)
3. Open file in editor, change a tag, save
4. Batch editor: select 3 files, apply artist tag
5. Converter: convert mp4 to mp3
6. History: verify entries appear with thumbnails
7. Player: load and play an mp3, switch tracks, stop
8. Settings: switch light/dark mode
9. Close app: verify backend dies in Task Manager within 2s
10. Reopen app: verify no port conflict, dot turns green
11. Double-click icon while running: verify single instance (window comes to front)
12. Close app during active download: verify clean shutdown, no orphan processes

### Step 3 — Bump version
```bash
python scripts/bump_version.py 2.2.0
```

### Step 4 — Build backend
```bash
python scripts/build_backend.py
```
Verify output: `64-bit` confirmed, size recorded.

### Step 5 — Build Tauri installer
```bash
cd frontend && npx tauri build
```

### Step 6 — Record new sizes
Compare with Step 1.

### Step 7 — Commit
```bash
git add .
git commit -m "release: v2.2.0 — security hardening, stability, performance

Size before: backend=XXX MB, installer=XXX MB
Size after:  backend=XXX MB, installer=XXX MB

Security: path traversal fix (converter), image size validation, CORS lockdown,
          URL scheme validation, filepath validation, request timeouts
Stability: log rotation, thread-safe cache, relative import fix, blocking I/O fix,
           single-instance enforcement
Memory:    apiFetch timeout, PlayerBar timer cleanup, Editor async safety,
           FileReader cleanup, Settings/App.tsx mounted flags
Performance: lazy imports (requests), React.lazy (Editor/Converter),
             lazy image loading, --exclude-module PyInstaller flags
See SECURITY.md for full audit details"
```

### Step 8 — GitHub release
```bash
gh release create v2.2.0 \
  "frontend/src-tauri/target/release/bundle/nsis/Yuki_2.2.0_x64-setup.exe" \
  --title "Yuki v2.2.0 — Security & Stability" \
  --notes "Security hardening, memory leak fixes, performance optimization.
Zero orphan processes, single-instance enforcement, self-healing startup.
See SECURITY.md for full security audit details."
```

---

## Summary of All Changes

| Phase | File | Change | Severity |
|-------|------|--------|----------|
| 1.1 | logger.py | RotatingFileHandler (5MB, 3 backups) | Medium |
| 1.2 | player_engine.py:236 | Fix relative import | Medium |
| 1.3 | player.py | threading.Lock for _tag_cache | Medium |
| 1.4 | player.py, tagger.py routers | Wrap Path.exists/stat in asyncio.to_thread | Low |
| 1.5 | bump_version.py, VERSION | Fix VERSION file duplicate + pattern | Low |
| 1.6 | bump_version.py, pyproject.toml | Add pyproject.toml to version bump | Low |
| 2.1 | converter.py:106-110 | **Path traversal fix** | **High** |
| 2.2 | tagger.py service:418 | Image size validation (20MB + pixel limit) | Medium |
| 2.3 | main.py:68 | CORS lockdown (http://localhost → :1421) | Medium |
| 2.4 | download.py | URL scheme validation (http/https only) | Medium |
| 2.5 | player.py, tagger.py routers | Filepath validation | Medium |
| 2.6 | SECURITY.md | Create security documentation | — |
| 3.1 | client.ts:25 | **apiFetch timeout (10s)** | **High** |
| 3.2 | PlayerBar.tsx:91 | Fix untracked setTimeout | High |
| 3.3 | Editor.tsx:115-118 | Async setState with mounted flag | High |
| 3.4 | Editor.tsx:153-226 | FileReader mounted flag | Medium |
| 3.5 | App.tsx:49 | useEffect cleanup return | Medium |
| 3.6 | Settings.tsx:72-77 | Async tracking with mounted flag | Medium |
| 3.7 | Sidebar.tsx:25-34 | Remove console.logs | Low |
| 3.8 | api/settings.ts | Error logging in catch blocks | Low |
| 4.1 | Cargo.toml, lib.rs | Single-instance plugin | Medium |
| 5.1 | tagger.py service | Lazy-load requests import | Low |
| 5.2 | App.tsx | React.lazy for Editor, Converter | Low |
| 5.3 | HistoryCard.tsx | loading="lazy" on img tags | Low |
| 6.2 | build_backend.py | --exclude-module flags | Low |
| 6.3 | build_backend.py | --clean flag | Low |

**Total changes: 25 items across 18 files**

---

## Anti-Patterns to Avoid During Implementation

1. **DO NOT** use `shell=True` in any new subprocess calls
2. **DO NOT** add `dangerouslySetInnerHTML` anywhere in React
3. **DO NOT** remove or weaken the existing 3-layer kill strategy in lib.rs
4. **DO NOT** add new top-level imports in backend service files — import inside functions
5. **DO NOT** use `React.lazy()` for components that are always visible (Sidebar, PlayerBar)
6. **DO NOT** add SSL verification bypass (`verify=False`) anywhere
7. **DO NOT** store secrets or paths in code — use config/env
8. **DO NOT** call `apiFetch` without handling the AbortError it can now throw
