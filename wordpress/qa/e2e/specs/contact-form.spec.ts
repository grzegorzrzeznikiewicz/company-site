import { expect, test } from '@playwright/test';

test('preserves the legacy contact layout at mobile and desktop widths @contact-form-layout', async ({
  page,
}) => {
  const response = await page.goto('/#contact', {
    waitUntil: 'domcontentloaded',
  });
  expect(response?.status()).toBe(200);
  for (const width of [320, 390, 767, 768, 1440] as const) {
    await page.setViewportSize({ width, height: 900 });

    const contact = page.locator('main section#contact.gama-contact');
    const form = contact.locator('form.gama-contact-form');
    await expect(form).toBeVisible();
    // A missing stylesheet used to produce a false pass in Docker (localhost
    // asset URLs resolving to the browser container instead of WordPress).
    await expect(form).toHaveCSS('display', 'flex');
    await expect(contact.locator('.gama-contact__content')).toHaveCSS(
      'display',
      'flex',
    );
    const geometry = await contact.evaluate((section) => {
      const rect = (selector: string) => {
        const element = section.querySelector<HTMLElement>(selector);
        if (!element) throw new Error(`Contact element missing: ${selector}`);
        return element.getBoundingClientRect().toJSON() as {
          x: number;
          y: number;
          width: number;
          height: number;
        };
      };

      return {
        card: rect('.gama-contact__card'),
        form: rect('.gama-contact-form'),
        name: rect('#gama-contact-name'),
        email: rect('#gama-contact-email'),
        phone: rect('#gama-contact-phone'),
        message: rect('#gama-contact-message'),
        button: rect('[type="submit"]'),
      };
    });

    expect(geometry.card.width).toBeCloseTo(Math.min(width - 32, 672), 0);
    expect(geometry.card.x + geometry.card.width / 2).toBeCloseTo(width / 2, 0);
    expect(geometry.form.width).toBeCloseTo(
      geometry.card.width - (width < 768 ? 64 : 96),
      0,
    );
    expect(geometry.phone.width).toBeCloseTo(geometry.form.width, 0);
    expect(geometry.message.width).toBeCloseTo(geometry.form.width, 0);
    if (width < 768) {
      expect(geometry.email.y).toBeGreaterThan(
        geometry.name.y + geometry.name.height,
      );
      expect(geometry.name.width).toBeCloseTo(geometry.form.width, 0);
    } else {
      expect(geometry.email.y).toBeCloseTo(geometry.name.y, 0);
      expect(geometry.email.x).toBeGreaterThan(
        geometry.name.x + geometry.name.width,
      );
    }
    expect(geometry.button.x + geometry.button.width / 2).toBeCloseTo(
      width / 2,
      0,
    );
    expect(geometry.button.height).toBeCloseTo(40, 0);
    expect(geometry.card.height).toBeLessThan(520);
    await expect(contact.locator('.gama-contact__details')).toHaveCount(0);
    await expect(form.locator('br, p:not([class])')).toHaveCount(0);
    await expect(form.locator('noscript')).toBeHidden();
    for (const name of ['name', 'email', 'phone', 'message']) {
      await expect(form.locator(`[name="${name}"]`)).toHaveCSS(
        'font-size',
        width < 768 ? '16px' : '14px',
      );
    }
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth),
    ).toBe(width);
    await test.info().attach(`contact-${width}.png`, {
      body: await contact.screenshot(),
      contentType: 'image/png',
    });
  }
});

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
