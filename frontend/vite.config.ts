import path from "node:path";

import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

/**
 * Vite configuration.
 *
 * The dev server proxies `/api` to the backend so the frontend and API share an
 * origin in development (avoiding CORS complexity), matching the Nginx reverse
 * proxy used in production. The proxy target is read from the environment
 * (`VITE_API_PROXY_TARGET`, including `.env` files) and defaults to :8000.
 */
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  return {
    plugins: [react()],
    resolve: {
      alias: { "@": path.resolve(__dirname, "./src") },
    },
    server: {
      port: 5173,
      proxy: {
        "/api": {
          target: env.VITE_API_PROXY_TARGET ?? "http://localhost:8000",
          changeOrigin: true,
        },
      },
    },
    build: {
      outDir: "dist",
      sourcemap: true,
    },
  };
});
