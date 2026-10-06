import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// The FastAPI backend runs on :8000. Proxying /api and /images keeps every
// frontend URL relative, so no backend address is hard-coded in the app.
// Override with HW4_BACKEND when 8000 is taken (default matches the README).
const BACKEND = process.env.HW4_BACKEND ?? 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': BACKEND,
      '/images': BACKEND,
    },
  },
})
