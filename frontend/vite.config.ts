import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
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
