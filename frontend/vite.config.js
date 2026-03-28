import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import path from "node:path";

/**
 * Configure Vite with Vue and path aliases.
 * @returns {import("vite").UserConfigExport} Vite configuration.
 */
export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
