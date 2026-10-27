import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// En dev, /api est relayé vers le backend Django.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': process.env.VITE_API_PROXY || 'http://localhost:8000',
    },
  },
})
