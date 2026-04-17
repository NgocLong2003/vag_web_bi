import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@shared': path.resolve(__dirname, './src/shared'),
      '@features': path.resolve(__dirname, './src/features'),
      '@types': path.resolve(__dirname, './src/types'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      // Proxy API calls to Flask backend during dev
      '/api': 'http://localhost:5000',
      '/admin': 'http://localhost:5000',
      '/reports': 'http://localhost:5000',
      '/login': 'http://localhost:5000',
      '/logout': 'http://localhost:5000',
      '/settings': 'http://localhost:5000',
      // /d/:slug — must use /d/ (trailing slash) so it doesn't match /dashboards
      '/d/': 'http://localhost:5000',
    },
  },
  build: {
    outDir: '../static/dist',  // Build output → Flask serves this
    emptyOutDir: true,
    sourcemap: false,
  },
})