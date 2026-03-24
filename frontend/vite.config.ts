import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";
import { readFileSync } from "fs";

function readBackendPort(): number {
  const candidates: string[] = [
    path.resolve(__dirname, "../backend/.runtime_port"),
  ];
  if (process.env.APPDATA) {
    candidates.push(path.join(process.env.APPDATA, "Yuki", ".runtime_port"));
  }
  for (const p of candidates) {
    try {
      const content = readFileSync(p, "utf8");
      const port = parseInt(content.trim(), 10);
      if (!isNaN(port)) return port;
    } catch {
      // not written yet, try next
    }
  }
  return 9001;
}

export default defineConfig({
  plugins: [react()],
  server: {
    port: 1421,
    strictPort: true,
    proxy: {
      "/api": {
        target: `http://127.0.0.1:${readBackendPort()}`,
        changeOrigin: true,
        router: () => `http://127.0.0.1:${readBackendPort()}`,
      },
      "/health": {
        target: `http://127.0.0.1:${readBackendPort()}`,
        changeOrigin: true,
        router: () => `http://127.0.0.1:${readBackendPort()}`,
      },
    },
  },
  clearScreen: false,
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
});
