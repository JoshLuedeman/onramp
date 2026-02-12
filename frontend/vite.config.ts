import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    hmr: {
      // Use the browser's own host for WebSocket so HMR works across WSL/Docker
      clientPort: 5173,
    },
    proxy: {
      '/api': 'http://backend:8000',
      '/health': 'http://backend:8000',
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor-react': ['react', 'react-dom', 'react-router-dom'],
          'vendor-fluent': ['@fluentui/react-components', '@fluentui/react-icons'],
          'vendor-msal': ['@azure/msal-browser', '@azure/msal-react'],
        },
      },
    },
  },
})
