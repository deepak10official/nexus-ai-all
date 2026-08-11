import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Frontend calls /api/* and Vite forwards to FastAPI on 8000.
    proxy: {
      "/api": { target: "http://127.0.0.1:8001", changeOrigin: true },
      // Generated images are written to disk by the backend and served
      // from there — proxy them too or the <img> tags 404.
      "/generated": { target: "http://127.0.0.1:8001", changeOrigin: true },
    },
  },
});
