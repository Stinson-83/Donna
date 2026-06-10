import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// base: './' → relative asset paths so the built bundle loads inside the
// Capacitor webview (served from capacitor://localhost / file://) as well as
// from a web host. The app has no client-side router (tabs are state), so
// relative base is safe everywhere.
export default defineConfig({
  base: './',
  plugins: [react()],
  build: { outDir: 'dist' },
  server: { port: 5173, host: true },
})
