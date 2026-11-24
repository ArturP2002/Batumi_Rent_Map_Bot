import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath, URL } from "node:url";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    // Bind IPv4 loopback so ngrok (http://127.0.0.1:5173) can connect;
    // plain "localhost" often resolves to [::1] and gets connection refused.
    port: 5173,
    host: "127.0.0.1",
    strictPort: true,
    allowedHosts: true,
    proxy: {
      "/api": "http://127.0.0.1:8001",
    },
  },
});
