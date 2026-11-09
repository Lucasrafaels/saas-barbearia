import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    // Mantém a origem alinhada ao CORS de desenvolvimento do Django.
    port: 5173,
    strictPort: true,
  },
})
