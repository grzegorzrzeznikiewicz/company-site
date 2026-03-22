import { expect, test } from '@playwright/test';

import { e2eEnvironment } from '../support/environment';

test('renders the admin dashboard after HTTP Basic authentication', async ({
  browser,
}) => {
  const context = await browser.newContext();
  const page = await context.newPage();
  const adminUrl = new URL(e2eEnvironment.adminUrl);
  adminUrl.username = e2eEnvironment.adminUsername;
  adminUrl.password = e2eEnvironment.adminPassword;

  const response = await page.goto(adminUrl.toString(), {
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
