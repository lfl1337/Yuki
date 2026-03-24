import { useEffect, useState } from "react";
import { Routes, Route } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import PlayerBar from "./components/PlayerBar";
import Settings from "./components/Settings";
import Downloader from "./views/Downloader";
import History from "./views/History";
import Editor from "./views/Editor";
import Converter from "./views/Converter";
import { useStore } from "./store";
import { checkBackendOnline, apiFetch, setPort } from "./api/client";
import { applyTheme } from "./utils/theme";

function StartupSplash() {
  return (
    <div className="flex h-screen items-center justify-center bg-bg-primary flex-col gap-4">
      <div className="text-6xl text-accent font-bold">雪</div>
      <div className="text-lg text-zinc-400">Starting Yuki…</div>
      <div className="w-48 h-1 bg-bg-elevated rounded-full overflow-hidden">
        <div className="h-full bg-accent rounded-full animate-pulse" style={{ width: "60%" }} />
      </div>
    </div>
  );
}

function ErrorSplash({ message }: { message: string }) {
  return (
    <div className="flex h-screen items-center justify-center bg-bg-primary flex-col gap-4 px-8 text-center">
      <div className="text-5xl text-red-500 font-bold">✕</div>
      <div className="text-white text-lg font-semibold">Backend failed to start</div>
      <div className="text-zinc-400 text-sm max-w-md">{message}</div>
      <div className="text-zinc-500 text-xs mt-1">
        Logs: %APPDATA%\Yuki\yuki-tauri.log
      </div>
      <button
        onClick={() => window.location.reload()}
        className="mt-2 px-5 py-2 rounded-xl bg-accent text-white text-sm hover:bg-accent-hover transition-colors"
      >
        Retry
      </button>
    </div>
  );
}

function AppShell() {
  const { settingsOpen, setBackendOnline, setSettingsOpen } = useStore();

  // Apply saved theme on startup
  useEffect(() => {
    apiFetch<Record<string, string>>('/settings')
      .then((data) => {
        const raw = data['theme']
        const theme = raw ? (JSON.parse(raw) as string) : 'dark'
        applyTheme(theme)
      })
      .catch(() => applyTheme('dark'))
  }, [])

  // Poll backend health
  useEffect(() => {
    const poll = async () => {
      const online = await checkBackendOnline();
      setBackendOnline(online);
    };
    poll();
    const id = setInterval(poll, 30_000);
    // Pause when tab hidden
    const onVisibility = () => {
      if (!document.hidden) poll();
    };
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      clearInterval(id);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [setBackendOnline]);

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-bg-primary text-zinc-100 select-none">
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-auto min-w-0">
          <Routes>
            <Route path="/" element={<Downloader />} />
            <Route path="/history" element={<History />} />
            <Route path="/editor" element={<Editor />} />
            <Route path="/converter" element={<Converter />} />
          </Routes>
        </main>
      </div>
      <PlayerBar />
      <Settings open={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </div>
  );
}

export default function App() {
  const [backendReady, setBackendReady] = useState(import.meta.env.DEV);
  const [backendError, setBackendError] = useState<string | null>(null);

  useEffect(() => {
    if (import.meta.env.DEV) return;

    let unlistenPort: (() => void) | undefined;
    let unlistenReady: (() => void) | undefined;
    let unlistenError: (() => void) | undefined;
    let mounted = true;

    // Secondary: event listeners (may be missed due to timing race, but kept as bonus)
    import("@tauri-apps/api/event").then(async ({ listen }) => {
      unlistenPort = await listen<string>("backend-port", (event) => {
        setPort(event.payload);
      });
      unlistenReady = await listen("backend-ready", () => {
        if (mounted) setBackendReady(true);
      });
      unlistenError = await listen<string>("backend-error", (event) => {
        if (mounted) setBackendError(event.payload);
      });
    });

    // Primary: invoke-based port discovery — frontend asks when ready, no race condition.
    // Rust stores the port in DiscoveredPort state; we poll until it appears.
    const pollPort = async () => {
      const { invoke } = await import("@tauri-apps/api/core");
      for (let i = 0; i < 60 && mounted; i++) {
        const port = await invoke<string | null>("get_backend_port").catch(() => null);
        if (port) {
          setPort(port);
          // Now health-poll on the correct port
          for (let j = 0; j < 60 && mounted; j++) {
            if (await checkBackendOnline()) {
              if (mounted) setBackendReady(true);
              return;
            }
            await new Promise<void>(r => setTimeout(r, 500));
          }
          // Health check timed out but port found — show UI anyway
          if (mounted) setBackendReady(true);
          return;
        }
        await new Promise<void>(r => setTimeout(r, 500));
      }
      // 30s total — backend never appeared
      if (mounted) setBackendError("Backend did not start within 30 seconds.");
    };
    pollPort();

    return () => {
      mounted = false;
      unlistenPort?.();
      unlistenReady?.();
      unlistenError?.();
    };
  }, []);

  if (backendError) return <ErrorSplash message={backendError} />;
  return backendReady ? <AppShell /> : <StartupSplash />;
}
