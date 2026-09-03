import { defineConfig } from '@playwright/test';

const artifactRun = process.env.GAMA_PLAYWRIGHT_RUN ?? 'adhoc';
if (!/^[a-z][a-z0-9-]*$/.test(artifactRun)) {
  throw new Error('GAMA_PLAYWRIGHT_RUN must be a safe artifact directory name.');
}
const artifactRoot = `/artifacts/${artifactRun}`;

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
  outputDir: `${artifactRoot}/test-results`,
  reporter: [
    ['list'],
    ['html', { outputFolder: `${artifactRoot}/report`, open: 'never' }],
  ],
});
