import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: true, // Permite que o servidor seja acessível externamente (necessário para o Docker)
    port: 5173,
    proxy: {
      // Redireciona requisições de /api para o backend
      '/api': {
        target: 'http://localhost:8000', // O backend está rodando na porta 8000
        changeOrigin: true, // Necessário para hosts virtuais
        rewrite: (path) => path.replace(/^\/api/, ''), // Remove /api do caminho da requisição
      },
    },
  },
})
