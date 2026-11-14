import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  // same-origin /api in dev, so no CORS setup is needed on the backend
  server: { proxy: { '/api': 'http://localhost:8000' } },
})
