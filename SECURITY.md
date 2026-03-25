# Yuki Security Documentation

## Audit: 2026-03-25 | Version: v2.2.0

### Security Fixes in v2.2.0

| ID | Severity | Component | Issue | Fix |
|----|----------|-----------|-------|-----|
| SEC-01 | High | services/converter.py | Path traversal via filename_pattern — user-supplied format string could escape output directory | Resolve output path and validate it stays within allowed directory |
| SEC-02 | Medium | services/tagger.py | No image size validation — malicious images could cause memory exhaustion | 20 MB byte limit + Image.MAX_IMAGE_PIXELS = 50M (Pillow decompression bomb guard) |
| SEC-03 | Medium | app/main.py | CORS allowed bare http://localhost (port 80) — any local HTTP server could reach backend | Restricted to http://localhost:1421 (Vite dev port only) |
| SEC-04 | Medium | routers/download.py | No URL scheme validation — file://, ftp://, javascript:// not rejected | Validate scheme is http or https before enqueuing |
| SEC-05 | Medium | routers/player.py, routers/tagger.py | No filepath validation — path traversal to arbitrary files | Resolve path, check existence, reject system directories |
| SEC-06 | Medium | api/client.ts | No request timeout on apiFetch() — backend freeze causes indefinite frontend hang | AbortSignal.timeout(10 000 ms) on all regular requests |

### Architecture Security Baseline

- Backend binds only to `127.0.0.1` (localhost) — no network exposure
- No `shell=True` in any subprocess call across the entire codebase
- Frontend uses `credentials: "omit"` on all API requests (CSRF protection)
- CSP restricts `script-src` to `'self'` only — no inline scripts, no remote scripts
- All outgoing HTTP requests include timeouts (requests library: 10–15s, auto-updater: 300s for installer download)
- Tauri capabilities: minimal set — `core:default`, `shell:allow-open`, `shell:allow-kill`, `dialog:default`
- No hardcoded credentials, tokens, or secrets in source code

### Known Acceptable Risks

- `img-src` in CSP allows `https: http:` — required for loading YouTube/Spotify CDN thumbnails in history view
- `style-src 'unsafe-inline'` — required for Tailwind CSS runtime (generated at build time into one file, no user-controlled styles)
- Backend auto-updater downloads installer from GitHub Releases (HTTPS only, no SSL bypass)
