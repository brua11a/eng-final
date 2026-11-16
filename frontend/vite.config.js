import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    host: true,
    proxy: {
      // The whole API is under /api; every other path is a page of the frontend.
      '/api': {
        target: process.env.VITE_DEV_API_PROXY ?? 'https://localhost:8000',
        changeOrigin: true,
        secure: true,
      },
    },
  },
})
