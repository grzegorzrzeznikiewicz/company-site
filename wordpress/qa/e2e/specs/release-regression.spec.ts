import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';

const viewports = [
  { name: 'desktop', width: 1440, height: 900 },
  { name: 'tablet', width: 768, height: 1024 },
  { name: 'phone', width: 390, height: 844 },
] as const;

for (const viewport of viewports) {
  test(`@release-regression ${viewport.name} is functional, accessible and within budget`, async ({
    page,
  }) => {
    await page.setViewportSize(viewport);
    const consoleErrors: string[] = [];
    const pageErrors: string[] = [];
    const failedRequests: string[] = [];
    page.on('console', (message) => {
      if (message.type() === 'error') consoleErrors.push(message.text());
    });
    page.on('pageerror', (error) => pageErrors.push(error.message));
    page.on('requestfailed', (request) =>
      failedRequests.push(`${request.method()} ${request.url()}`),
    );

    const response = await page.goto('/', { waitUntil: 'networkidle' });
    expect(response?.status()).toBe(200);
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(
      'Gama Software',
    );
    await expect(
      page.locator('img.custom-logo[alt="Gama Software"]'),
    ).toHaveCount(2);
    await expect(page.locator('form.gama-contact-form')).toBeVisible();

    const destinations = [
      ['Start', '#home'],
      ['Usługi', '#services'],
      ['Moduły', '#modules'],
      ['Kontakt', '#contact'],
    ] as const;
    const responsiveMenuButton = page.locator(
      'header nav[aria-label="Główna nawigacja"] .wp-block-navigation__responsive-container-open',
    );
    if (!(await responsiveMenuButton.isVisible())) {
      for (const [label, hash] of destinations) {
        const link = page
          .locator('header nav[aria-label="Główna nawigacja"]')
          .getByRole('link', { name: label });
        await link.click();
        await expect(page).toHaveURL(new RegExp(`${hash}$`));
        await expect(page.locator(hash)).toBeInViewport();
      }
    } else {
      await responsiveMenuButton.click();
      const mobileMenu = page.locator(
        'header .wp-block-navigation__responsive-container.is-menu-open',
      );
      await expect(mobileMenu).toBeVisible();
      for (const [label, hash] of destinations) {
        await expect(
          mobileMenu.locator('a').filter({ hasText: label }),
        ).toHaveAttribute('href', `/${hash}`);
      }
      await mobileMenu.locator('a').filter({ hasText: 'Kontakt' }).click();
      await expect(page).toHaveURL(/#contact$/);
      await expect(page.locator('#contact')).toBeInViewport();
    }
    const blogResponse = await page.request.get('/blog/');
    expect(blogResponse.status()).toBe(200);

    const duplicateIds = await page.locator('[id]').evaluateAll((elements) => {
      const ids = elements.map((element) => element.id).filter(Boolean);
      return ids.filter((id, index) => ids.indexOf(id) !== index);
    });
    expect(duplicateIds).toEqual([]);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);

    const accessibility = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();
    expect(
      accessibility.violations.map(({ id, impact, nodes }) => ({
        id,
        impact,
        targets: nodes.flatMap((node) => node.target),
      })),
    ).toEqual([]);

    const performance = await page.evaluate(() => {
      const navigation = performance.getEntriesByType(
        'navigation',
      )[0] as PerformanceNavigationTiming;
      const resources = performance.getEntriesByType(
        'resource',
      ) as PerformanceResourceTiming[];
      return {
        timeToFirstByte: navigation.responseStart - navigation.startTime,
        domContentLoaded:
          navigation.domContentLoadedEventEnd - navigation.startTime,
        load: navigation.loadEventEnd - navigation.startTime,
        resourceCount: resources.length,
        transferredBytes: resources.reduce(
          (total, resource) => total + resource.transferSize,
          navigation.transferSize,
        ),
      };
    });
    expect(performance.timeToFirstByte).toBeLessThan(1_500);
    expect(performance.domContentLoaded).toBeLessThan(4_000);
    expect(performance.load).toBeLessThan(5_000);
    expect(performance.resourceCount).toBeLessThanOrEqual(50);
    expect(performance.transferredBytes).toBeLessThanOrEqual(1_000_000);
    await test.info().attach(`performance-${viewport.name}.json`, {
      body: JSON.stringify(performance, null, 2),
      contentType: 'application/json',
    });
    expect({ consoleErrors, pageErrors, failedRequests }).toEqual({
      consoleErrors: [],
      pageErrors: [],
      failedRequests: [],
    });
  });
}
