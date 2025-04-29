import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// If you want path aliases like "@/components", add them here:
import { resolve } from "path";
const alias = {
  "@": resolve(__dirname, "src"),
};

// ────────────────────────────────────────────────────────────
// Vite configuration
// ────────────────────────────────────────────────────────────
export default defineConfig({
  plugins: [react()],

  resolve: { alias },

  // Dev-server settings
  server: {
    host: "localhost",        // or 0.0.0.0 if you want LAN access
    port: 5173,               // default vite port
    open: true,               // auto-open browser on `pnpm dev`
    proxy: {
      // --- FastAPI backend ---------------------------------
      // 127.0.0.1 强制走 IPv4，避免 “ECONNREFUSED ::1:8000” 问题
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      // static graphs served by FastAPI’s StaticFiles
      "/static": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },

  // Build settings (optional tweaks)
  build: {
    outDir: "dist",
    sourcemap: true,
  },
});
