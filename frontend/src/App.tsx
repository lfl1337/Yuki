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
import { checkBackendOnline, apiFetch } from "./api/client";
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

function AppShell() {
  const { settingsOpen, setBackendOnline, setSettingsOpen } = useStore();

  // Apply saved theme on startup
  useEffect(() => {
    apiFetch<Record<string, string>>('/api/v1/settings')
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

  useEffect(() => {
    if (import.meta.env.DEV) return;
    // Production: wait for Tauri "backend-ready" event
    import("@tauri-apps/api/event").then(({ listen }) => {
      listen("backend-ready", () => setBackendReady(true));
    });
    // Safety fallback after 15s
    const fallback = setTimeout(() => setBackendReady(true), 15_000);
    return () => clearTimeout(fallback);
  }, []);

  return backendReady ? <AppShell /> : <StartupSplash />;
}
