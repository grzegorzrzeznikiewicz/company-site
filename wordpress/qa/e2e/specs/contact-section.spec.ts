import { expect, test } from '@playwright/test';

test('renders an accessible editable Contact fallback without the form plugin @contact-section', async ({
  page,
}) => {
  for (const width of [320, 768, 1440] as const) {
    await page.setViewportSize({ width, height: 900 });
    const response = await page.goto('/#contact', {
      waitUntil: 'domcontentloaded',
    });
    expect(response?.status()).toBe(200);
    const contact = page.locator('main section#contact.gama-contact');
    await expect(contact).toHaveCount(1);
    await expect(
      contact.getByRole('heading', { level: 2, name: 'Kontakt' }),
    ).toHaveCount(1);
    await expect(
      contact.getByRole('link', { name: 'founders@gama-software.com' }),
    ).toHaveAttribute('href', 'mailto:founders@gama-software.com');
    await expect(
      contact.getByText(
        'Formularz kontaktowy zostanie wyświetlony po aktywowaniu wtyczki Gama Contact.',
        { exact: true },
      ),
    ).toBeVisible();
    expect(
      await page.evaluate(
        () =>
          document.documentElement.scrollWidth >
          document.documentElement.clientWidth + 1,
      ),
    ).toBe(false);
  }
});
