import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Built files land in the Python app's static folder; index.html is served at "/".
export default defineConfig({
  plugins: [react()],
  base: '/static/',
  build: { outDir: '../app/static', emptyOutDir: false, assetsDir: 'assets' },
  server: { proxy: { '/api': process.env.PAI_API || 'http://localhost:8088' } },
  test: { environment: 'node' },
})
