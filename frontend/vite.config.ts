import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";

export default defineConfig({
  server: {
    host: "localhost",
    port: 8080,
    // In development the Django API runs on :8000; proxying avoids CORS.
    proxy: { "/api": "http://localhost:8000" },
  },
  plugins: [react()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
});
