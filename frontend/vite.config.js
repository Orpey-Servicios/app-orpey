import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Configuración de Vite para Orpey Servicios
// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Puerto donde corre el frontend en desarrollo
    port: 5173,
    // Permite acceso desde otros dispositivos en la red local
    host: true,
    // Proxy: redirige /api/* al backend (evita CORS y problemas de redirect 307)
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        // followRedirects: true para que el proxy siga los redirects 307 del backend
      },
    },
  },
})
