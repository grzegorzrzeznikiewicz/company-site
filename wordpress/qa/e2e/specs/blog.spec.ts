import { expect, test } from '@playwright/test';

test('renders a real paginated blog, latest-post homepage section and single article @blog', async ({
  page,
}) => {
  let response = await page.goto('/blog/', { waitUntil: 'domcontentloaded' });
  expect(response?.status()).toBe(200);
  await expect(page.locator('main.gama-template--home')).toHaveCount(1);
  await expect(page.getByRole('heading', { level: 1, name: 'Blog' })).toHaveCount(
    1,
  );
  await expect(
    page.getByRole('heading', { level: 2, name: 'Focus neighbour' }),
  ).toHaveCount(1);
  const next = page.getByRole('link', { name: /next/i });
  await expect(next).toBeVisible();
  await next.click();
  await expect(page).toHaveURL(/\/blog\/page\/2\/$/);
  await expect(
    page.getByRole('heading', { level: 2, name: 'Second fixture article' }),
  ).toHaveCount(1);

  response = await page.goto('/focus-neighbour/', {
    waitUntil: 'domcontentloaded',
  });
  expect(response?.status()).toBe(200);
  await expect(page.locator('main.gama-template--single')).toHaveCount(1);
  await expect(
    page.getByRole('heading', { level: 1, name: 'Focus neighbour' }),
  ).toHaveCount(1);
  await expect(page.locator('article time')).toHaveCount(1);

  response = await page.goto('/', { waitUntil: 'domcontentloaded' });
  expect(response?.status()).toBe(200);
  const latest = page.locator('main section#blog.gama-blog-latest');
  await expect(latest).toHaveCount(1);
  await expect(
    latest.getByRole('heading', { level: 2, name: 'Blog' }),
  ).toHaveCount(1);
  await expect(
    latest.getByRole('heading', { level: 3, name: 'Focus neighbour' }),
  ).toHaveCount(1);
  await expect(
    page.getByText('Welcome to WordPress. This is your first post.', {
      exact: false,
    }),
  ).toHaveCount(0);
});
