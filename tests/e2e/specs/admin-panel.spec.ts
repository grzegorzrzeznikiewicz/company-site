import { expect, test } from '@playwright/test';

import { e2eEnvironment } from '../support/environment';

test('renders the admin dashboard after HTTP Basic authentication', async ({
  browser,
}) => {
  const context = await browser.newContext({
    httpCredentials: {
      username: e2eEnvironment.adminUsername,
      password: e2eEnvironment.adminPassword,
    },
  });
  const page = await context.newPage();

  await page.goto(e2eEnvironment.adminUrl, { waitUntil: 'domcontentloaded' });

  await expect(
    page.getByRole('heading', { name: 'Suggested roadmap', level: 3 }),
  ).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText('centrum zarządzania treścią')).toBeVisible({
    timeout: 15_000,
  });
  await expect(page).toHaveURL(/\/admin$/);

  await context.close();
});
