import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      // Preserve the browser origin, including Vite's selected port, so the
      // backend can validate same-origin admin requests without a port allowlist.
      "/api": { target: "http://127.0.0.1:8000", changeOrigin: false },
      "/uploads": { target: "http://127.0.0.1:8000", changeOrigin: false },
    },
  },
});
