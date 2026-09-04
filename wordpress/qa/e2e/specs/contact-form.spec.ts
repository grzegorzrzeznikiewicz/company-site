import { expect, test } from '@playwright/test';

test('@contact-form validates, delivers and reports transport errors in the browser', async ({
  page,
  request,
}) => {
  await page.goto('/#contact', { waitUntil: 'domcontentloaded' });
  const form = page.locator('form.gama-contact-form');
  await expect(form).toBeVisible();
  await expect(page.locator('.gama-contact__form-placeholder')).toBeHidden();

  await form.getByRole('button', { name: 'Wyślij wiadomość' }).click();
  const name = form.getByLabel('Imię i nazwisko');
  await expect(name).toHaveAttribute('aria-invalid', 'true');
  await expect(name).toHaveAttribute(
    'aria-describedby',
    'gama-contact-name-error',
  );
  await expect(name).toBeFocused();
  await expect(page.locator('#gama-contact-name-error')).not.toBeEmpty();

  const marker = `GSWEB20-browser-${Date.now()}`;
  await name.fill('Jan Kowalski');
  await form.getByLabel('E-mail').fill('jan@example.test');
  await form.getByLabel('Telefon').fill('+48 500 600 700');
  await form.getByLabel('Wiadomość').fill(marker);
  await form.getByRole('button', { name: 'Wyślij wiadomość' }).click();
  await expect(form.locator('.gama-contact-form__status')).toContainText(
    'Wiadomość została wysłana',
  );

  const mailpitUrl = process.env.MAILPIT_API_URL ?? 'http://mailpit:8025';
  await expect
    .poll(async () => {
      const messages = await request.get(`${mailpitUrl}/api/v1/messages`);
      return (await messages.text()).includes(marker);
    })
    .toBe(true);

  await page.route('**/wp-json/gama-contact/v1/messages', (route) =>
    route.abort('failed'),
  );
  await name.fill('Jan Kowalski');
  await form.getByLabel('E-mail').fill('jan@example.test');
  await form.getByLabel('Telefon').fill('+48 500 600 700');
  await form.getByLabel('Wiadomość').fill('Transport failure fixture');
  await form.getByRole('button', { name: 'Wyślij wiadomość' }).click();
  await expect(form.locator('.gama-contact-form__status')).toContainText(
    'Coś poszło nie tak',
  );
});
