import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    host: true,
    proxy: {
      '^/(login|teachers|subjects|curricula|organizational-units|me|opinions|students|groups|admin)(/|$)': {
        target: process.env.VITE_DEV_API_PROXY ?? 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
