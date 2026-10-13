import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// The FastAPI backend runs on :8000 (README). Proxying /api keeps every
// frontend URL relative, so no backend address is hard-coded in the app.
// Override with HW5_BACKEND if 8000 is taken.
const BACKEND = process.env.HW5_BACKEND ?? 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    open: !process.env.HW5_NO_OPEN, // `npm run dev` opens the desk in the browser
    proxy: { '/api': BACKEND },
  },
})
