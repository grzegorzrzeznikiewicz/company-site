import { expect, test } from '@playwright/test';
import { login, rest } from './support/wordpress';

test('matches the approved content inventory, media and destinations @content', async ({
  page,
}) => {
  await login(page);
  const legalPages = await rest<any[]>(
    page,
    '/wp/v2/pages?context=edit&status=draft&per_page=100',
  );
  for (const [slug, title] of [
    ['polityka-prywatnosci', 'Polityka prywatności'],
    ['regulamin', 'Regulamin'],
  ] as const) {
    const legalPage = legalPages.find((candidate) => candidate.slug === slug);
    expect(legalPage?.status).toBe('draft');
    expect(legalPage?.title?.raw).toBe(title);
    expect(legalPage?.content?.raw).toContain(
      'TREŚĆ WYMAGA ZATWIERDZENIA WŁAŚCICIELA',
    );
  }

  const response = await page.goto('/', { waitUntil: 'domcontentloaded' });
  expect(response?.status()).toBe(200);
  const sections = page.locator('main > section');
  await expect(sections).toHaveCount(5);
  expect(await sections.evaluateAll((nodes) => nodes.map((node) => node.id))).toEqual([
    'home',
    'services',
    'modules',
    'blog',
    'contact',
  ]);
  const hero = page.locator('main section#home.gama-hero');
  await expect(hero.getByRole('heading', { level: 1 })).toHaveText('Gama Software');
  await expect(hero.getByRole('heading', { level: 1 })).toHaveCount(1);
  for (const text of [
    'Specjalizujemy się w wdrożeniach e-commerce, konsultacjach oraz budowaniu agentów AI dla Twojego biznesu',
    'Wdrożenia E-commerce',
    'Konsultacje E-commerce',
    'Agenci AI',
    'Advanced SEO Suite',
    'Smart Product Recommendations',
    'Enhanced Checkout',
    'Inventory Management Pro',
    'Customer Loyalty Program',
    'Performance Optimizer',
    'Kontakt',
  ]) {
    await expect(page.getByText(text, { exact: true }).first()).toBeVisible();
  }
  await expect(page.getByText(/Welcome to WordPress|Lorem ipsum/i)).toHaveCount(0);

  const primaryLinks = page
    .locator('header nav[aria-label="Główna nawigacja"]')
    .getByRole('link');
  expect(await primaryLinks.evaluateAll((links) => links.map((link) => [link.textContent?.trim(), link.getAttribute('href')]))).toEqual([
    ['Start', '/#home'],
    ['Usługi', '/#services'],
    ['Moduły', '/#modules'],
    ['Blog', '/blog/'],
    ['Kontakt', '/#contact'],
  ]);
  const placeholderLinks = page.locator('a[href="#"], a:not([href])');
  await expect(placeholderLinks).toHaveCount(0);

  const logos = page.locator('img.custom-logo[alt="Gama Software"]');
  await expect(logos).toHaveCount(2);
  for (const logo of await logos.all()) {
    await expect(logo).toBeVisible();
    expect(await logo.evaluate((image: HTMLImageElement) => image.naturalWidth)).toBe(1024);
  }
});
