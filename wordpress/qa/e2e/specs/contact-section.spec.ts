import { expect, test } from '@playwright/test';

test('renders an accessible editable Contact fallback without the form plugin @contact-section', async ({
  page,
}) => {
  const response = await page.goto('/#contact', {
    waitUntil: 'domcontentloaded',
  });
  expect(response?.status()).toBe(200);

  for (const width of [320, 768, 1440] as const) {
    await page.setViewportSize({ width, height: 900 });
    const contact = page.locator('main section#contact.gama-contact');
    await expect(contact).toHaveCount(1);
    await expect(
      contact.getByRole('heading', { level: 2, name: 'Kontakt' }),
    ).toHaveCount(1);
    await expect(
      contact.getByRole('link', { name: 'founders@gama-software.com' }),
    ).toHaveAttribute('href', 'mailto:founders@gama-software.com');
    await expect(
      contact.locator('.gama-contact__form-placeholder'),
    ).toBeVisible();
    await expect(
      contact.locator('.gama-contact__form-placeholder'),
    ).toContainText('Formularz jest chwilowo niedostępny. Napisz do nas:');
    const card = contact.locator('.gama-contact__card');
    const bounds = await card.boundingBox();
    expect(bounds?.width).toBeCloseTo(Math.min(width - 32, 672), 0);
    expect(
      await page.evaluate(
        () =>
          document.documentElement.scrollWidth >
          document.documentElement.clientWidth + 1,
      ),
    ).toBe(false);
  }
});
