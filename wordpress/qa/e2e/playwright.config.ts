import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './specs',
  fullyParallel: false,
  workers: 1,
  timeout: 60_000,
  expect: { timeout: 15_000 },
  use: {
    baseURL: process.env.WP_BASE_URL ?? 'http://wordpress',
    browserName: 'chromium',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  outputDir: '/artifacts/test-results',
  reporter: [
    ['list'],
    ['html', { outputFolder: '/artifacts/report', open: 'never' }],
  ],
});
