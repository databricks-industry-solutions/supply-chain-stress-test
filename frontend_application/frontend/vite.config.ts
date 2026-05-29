import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: 'build-chat-app',
  },
  server: {
    port: 3000,
    proxy: {
      '/chat-api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
