import path from 'path';
import { defineConfig, loadEnv } from 'vite';
import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const devHost = process.env.VITE_DEV_HOST ?? env.VITE_DEV_HOST ?? 'localhost';
  const devPort = Number(
    process.env.VITE_DEV_PORT ?? env.VITE_DEV_PORT ?? '5173',
  );
  const apiProxyTarget =
    process.env.VITE_API_PROXY_TARGET ??
    env.VITE_API_PROXY_TARGET ??
    'http://localhost:8080';
  const usePolling =
    (process.env.VITE_USE_POLLING ?? env.VITE_USE_POLLING) === '1';
  const allowedHosts = [
    'localhost',
    '127.0.0.1',
    'host.docker.internal',
    'frontend',
    'company.test',
    '.company.test',
  ];

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
      allowedHosts,
      host: devHost,
      port: devPort,
      watch: {
        usePolling,
      },
      proxy: {
        '/api': {
          target: apiProxyTarget,
          changeOrigin: true,
        },
      },
    },
    preview: {
      host: devHost,
      port: devPort,
      proxy: {
        '/api': {
          target: apiProxyTarget,
          changeOrigin: true,
        },
      },
    },
    test: {
      environment: 'jsdom',
      setupFiles: './src/test/setup.ts',
      css: true,
      include: ['src/**/*.test.{ts,tsx}'],
      exclude: ['tests/e2e/**', 'backend/**'],
    },
  };
});
