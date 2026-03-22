import { expect, test } from '@playwright/test';

test.describe('Public site', () => {
  test('renders the landing page and key sections', async ({ page }) => {
    await page.goto('/');

    await expect(
      page.getByRole('heading', { name: 'Gama Software', level: 1 }),
    ).toBeVisible();
    await expect(
      page.getByRole('button', { name: 'Poznaj nasze usługi' }),
    ).toBeVisible();
    await expect(
      page.getByRole('heading', { name: 'Usługi', level: 2 }),
    ).toBeVisible();
    await expect(
      page.getByRole('heading', { name: 'Kontakt', level: 2 }),
    ).toBeVisible();
  });

  test('toggles the mobile navigation menu accessibly', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto('/');

    const menuButton = page.getByRole('button', {
      name: 'Otwórz menu nawigacyjne',
    });

    await expect(menuButton).toHaveAttribute('aria-expanded', 'false');
    await menuButton.click();

    await expect(
      page.getByRole('button', { name: 'Zamknij menu nawigacyjne' }),
    ).toHaveAttribute('aria-expanded', 'true');
    await expect(
      page.locator('#mobile-navigation-menu').getByRole('button', {
        name: 'Kontakt',
      }),
    ).toBeVisible();
  });
});
