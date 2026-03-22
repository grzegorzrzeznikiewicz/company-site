import { expect, test } from '@playwright/test';

import { e2eEnvironment } from '../support/environment';
import { findMailhogMessageByToken } from '../support/mailhog';

test('submits the contact form and delivers the message to MailHog', async ({
  page,
  request,
}) => {
  const uniqueToken = `PLAYWRIGHT-MAIL-${Date.now()}`;

  await page.goto('/');
  await page.locator('#contact').scrollIntoViewIfNeeded();

  await page.getByLabel('Imię i nazwisko').fill('Playwright Tester');
  await page.getByLabel('E-mail').fill('playwright@example.com');
  await page.getByLabel('Telefon').fill('+48 123 456 789');
  await page
    .getByLabel('Wiadomość')
    .fill(`${uniqueToken} end-to-end browser verification`);

  const contactResponsePromise = page.waitForResponse(
    (response) =>
      response.url().endsWith('/api/contact') && response.status() === 201,
    { timeout: 15_000 },
  );

  await page.getByRole('button', { name: 'Wyślij wiadomość' }).click();
  await contactResponsePromise;

  await expect(
    page.getByText('Dziękujemy! Wrócimy do Ciebie wkrótce.'),
  ).toBeVisible({ timeout: 15_000 });
  await expect(page.getByLabel('Imię i nazwisko')).toHaveValue('', {
    timeout: 15_000,
  });
  await expect(page.getByLabel('Wiadomość')).toHaveValue('', {
    timeout: 15_000,
  });

  await expect
    .poll(
      async () =>
        findMailhogMessageByToken(
          request,
          e2eEnvironment.mailhogUrl,
          uniqueToken,
        ),
      {
        timeout: 20_000,
        intervals: [1_000, 2_000, 3_000],
        message: 'Expected the contact email to arrive in MailHog.',
      },
    )
    .not.toBeNull();

  const deliveredMessage = await findMailhogMessageByToken(
    request,
    e2eEnvironment.mailhogUrl,
    uniqueToken,
  );

  if (!deliveredMessage) {
    throw new Error('Expected a delivered MailHog message after polling.');
  }

  expect(deliveredMessage.from).toContain('no-reply@gama-software.com');
  expect(deliveredMessage.to).toContain('founders@gama-software.com');
  expect(deliveredMessage.subject).toContain('Gama Software');
  expect(deliveredMessage.subject).toContain('nowe zapytanie kontaktowe');
  expect(deliveredMessage.body).toContain(uniqueToken);
});
