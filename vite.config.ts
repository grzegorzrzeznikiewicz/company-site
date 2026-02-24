import path from 'path'
import { defineConfig, loadEnv } from 'vite'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const devHost = env.VITE_DEV_HOST || 'localhost'
  const devPort = Number(env.VITE_DEV_PORT || '5173')

  return {
    plugins: [
      // The React and Tailwind plugins are both required for Make, even if
      // Tailwind is not being actively used – do not remove them
      react(),
      tailwindcss(),
    ],
    resolve: {
      alias: {
        // Alias @ to the src directory
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      host: devHost,
      port: devPort,
    },
    preview: {
      host: devHost,
      port: devPort,
    },
  }
})
2