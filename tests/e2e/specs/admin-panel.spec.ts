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

  await page.goto(e2eEnvironment.adminUrl);

  await expect(page).toHaveTitle(/Panel startowy/);
  await expect(
    page.getByRole('heading', { name: 'Suggested roadmap', level: 3 }),
  ).toBeVisible();
  await expect(page.getByText('centrum zarządzania treścią')).toBeVisible();

  await context.close();
});
