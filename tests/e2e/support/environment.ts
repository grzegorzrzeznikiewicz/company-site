export const e2eEnvironment = {
  frontendUrl: process.env.PLAYWRIGHT_FRONTEND_URL ?? 'http://127.0.0.1:5173',
  backendUrl: process.env.PLAYWRIGHT_BACKEND_URL ?? 'http://127.0.0.1:8080',
  adminUrl: process.env.PLAYWRIGHT_ADMIN_URL ?? 'http://127.0.0.1:8080/admin',
  mailhogUrl: process.env.PLAYWRIGHT_MAILHOG_URL ?? 'http://127.0.0.1:8026',
  adminUsername: process.env.E2E_ADMIN_USERNAME ?? 'admin',
  adminPassword: process.env.E2E_ADMIN_PASSWORD ?? 'Admin123!',
} as const;
