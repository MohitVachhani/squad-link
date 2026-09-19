import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// The dev server proxies API calls to FastAPI, so the browser talks to one origin (no CORS setup needed).
const API = process.env.VITE_API_URL ?? 'http://localhost:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Let a tunnel (cloudflared / ngrok) serve the dev app to someone else. Only these public hostnames.
    allowedHosts: ['.trycloudflare.com', '.ngrok-free.app', '.ngrok.app', '.ngrok.io'],
    proxy: {
      '/api': API,
      '/auth': API,
      '/users': API,
      '/health': API,
    },
  },
})
