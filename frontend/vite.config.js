import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0', // Permite que o servidor seja acessível externamente
    port: 5173,
    proxy: {
      // Redireciona requisições de /api para o backend
      '/api': {
        target: 'http://backend:8000', // Use o nome do serviço definido no docker-compose
        changeOrigin: true, // Necessário para hosts virtuais
      },
    },
  },
})
