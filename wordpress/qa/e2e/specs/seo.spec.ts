import { expect, test } from '@playwright/test';

test('@seo publishes one coherent SEO source and keeps local runtime out of search indexes', async ({
  page,
  request,
}) => {
  await page.goto('/');

  await expect(page).toHaveTitle(
    'Gama Software — E-commerce, Magento 2 i agenci AI',
  );
  await expect(page.locator('meta[name="description"]')).toHaveAttribute(
    'content',
    'Gama Software specjalizuje się we wdrożeniach i konsultacjach e-commerce oraz budowaniu agentów AI dla biznesu.',
  );
  await expect(page.locator('link[rel="canonical"]')).toHaveCount(1);
  await expect(page.locator('link[rel="canonical"]')).toHaveAttribute(
    'href',
    /\/$/,
  );
  await expect(page.locator('meta[property="og:title"]')).toHaveCount(1);
  await expect(page.locator('meta[property="og:description"]')).toHaveCount(1);
  await expect(page.locator('meta[property="og:url"]')).toHaveCount(1);
  await expect(page.locator('meta[property="og:type"]')).toHaveAttribute(
    'content',
    'website',
  );
  await expect(page.locator('meta[name="robots"]')).toHaveAttribute(
    'content',
    /noindex/,
  );

  const structuredData = page.locator('script[type="application/ld+json"]');
  await expect(structuredData).toHaveCount(1);
  const schema = JSON.parse((await structuredData.textContent()) ?? '{}') as {
    '@graph'?: Array<{ '@type'?: string }>;
  };
  expect(schema['@graph']?.map((entry) => entry['@type'])).toEqual([
    'Organization',
    'WebSite',
  ]);

  const robots = await request.get('/robots.txt');
  expect(robots.status()).toBe(200);
  expect(robots.headers()['content-type']).toContain('text/plain');
  expect(await robots.text()).toContain('Disallow: /');

  const sitemapRedirect = await request.get('/sitemap.xml', {
    maxRedirects: 0,
  });
  expect(sitemapRedirect.status()).toBe(301);
  expect(sitemapRedirect.headers().location).toMatch(/\/wp-sitemap\.xml$/);

  const sitemap = await request.get('/wp-sitemap.xml');
  expect(sitemap.status()).toBe(200);
  expect(sitemap.headers()['content-type']).toContain('application/xml');
  expect(await sitemap.text()).toContain('<sitemapindex');

  const missing = await request.get('/__gsweb22_missing_path__');
  expect(missing.status()).toBe(404);
});
