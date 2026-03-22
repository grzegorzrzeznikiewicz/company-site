import { expect, test } from '@playwright/test';

import { e2eEnvironment } from '../support/environment';

test('renders the admin dashboard after HTTP Basic authentication', async ({
  browser,
}) => {
  const authHeader = Buffer.from(
    `${e2eEnvironment.adminUsername}:${e2eEnvironment.adminPassword}`,
  ).toString('base64');
  const context = await browser.newContext({
    extraHTTPHeaders: {
      Authorization: `Basic ${authHeader}`,
    },
  });
  const page = await context.newPage();

  const response = await page.goto(e2eEnvironment.adminUrl, {
    waitUntil: 'domcontentloaded',
  });

  expect(response).not.toBeNull();
  expect(response?.status()).toBe(200);

  await expect(
    page.getByRole('heading', { name: 'Suggested roadmap', level: 3 }),
  ).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText('centrum zarządzania treścią')).toBeVisible({
    timeout: 15_000,
  });
  await expect(page).toHaveURL(/\/admin$/);

  await context.close();
});
