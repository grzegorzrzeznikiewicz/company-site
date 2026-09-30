import { expect, test, type Page } from '@playwright/test';
import {
  assertDiagnosticsClean,
  login,
  openEditorCanvas,
  rest,
  watchWordPressDiagnostics,
  type BrowserDiagnostics,
} from './support/wordpress';

const templateSlugs = ['index', 'front-page', 'page', 'single', 'home', 'archive', 'search', '404'];
const partSlugs = ['header', 'footer'];
let diagnostics: BrowserDiagnostics;

test.beforeEach(async ({ page }, testInfo) => {
  diagnostics = watchWordPressDiagnostics(page, {
    expectedMissingPaths: ['/missing-gsweb12/'],
  });
  if (!testInfo.title.includes('@public')) {
    await login(page);
  }
});

test.afterEach(() => {
  assertDiagnosticsClean(diagnostics);
});

for (const slug of templateSlugs) {
  test(`opens the ${slug} template in the Site Editor @open`, async ({ page }) => {
    const entity = await rest<any>(page, `/wp/v2/templates/gama-software//${slug}?context=edit`);
    expect(entity.slug).toBe(slug);
    expect(entity.theme).toBe('gama-software');
    const id = encodeURIComponent(`gama-software//${slug}`);
    const frame = await openEditorCanvas(
      page,
      `/wp-admin/site-editor.php?postId=${id}&postType=wp_template&canvas=edit`,
    );
    expect(new URL(page.url()).pathname).toBe('/wp-admin/site-editor.php');
    await expect(frame.locator(`main.gama-template--${slug}`)).toHaveCount(1);
  });
}

for (const slug of partSlugs) {
  test(`opens the ${slug} template part in the Site Editor @open`, async ({ page }) => {
    const entity = await rest<any>(page, `/wp/v2/template-parts/gama-software//${slug}?context=edit`);
    expect(entity.slug).toBe(slug);
    expect(entity.theme).toBe('gama-software');
    const id = encodeURIComponent(`gama-software//${slug}`);
    const frame = await openEditorCanvas(
      page,
      `/wp-admin/site-editor.php?postId=${id}&postType=wp_template_part&canvas=edit`,
    );
    expect(new URL(page.url()).pathname).toBe('/wp-admin/site-editor.php');
    await expect(frame.locator(`.gama-site-${slug}__surface`)).toHaveCount(1);
  });
}

async function addParagraphAndSave(page: Page, type: 'wp_template' | 'wp_template_part', slug: string, content: string): Promise<void> {
  const recordId = `gama-software//${slug}`;
  const id = encodeURIComponent(recordId);
  await openEditorCanvas(
    page,
    `/wp-admin/site-editor.php?postId=${id}&postType=${type}&canvas=edit`,
  );
  const saved = await page.evaluate(async ({ type, recordId, paragraph }) => {
    const wp = (window as any).wp;
    const record = wp.data.select('core').getEntityRecord('postType', type, recordId);
    const raw = record?.content?.raw ?? record?.content ?? '';
    wp.data.dispatch('core').editEntityRecord('postType', type, recordId, {
      content: `${raw}\n<!-- wp:paragraph --><p>${paragraph}</p><!-- /wp:paragraph -->`,
    });
    if (!wp.data.select('core').hasEditsForEntityRecord('postType', type, recordId)) {
      throw new Error('Site Editor core-data store did not become dirty.');
    }
    return wp.data.dispatch('core').saveEditedEntityRecord('postType', type, recordId);
  }, { type, recordId, paragraph: content });
  expect(saved.source).toBe('custom');
  expect(saved.has_theme_file).toBe(true);
}

test('saves one template and one part through the Site Editor core-data save action @save', async ({ page }) => {
  await addParagraphAndSave(page, 'wp_template', 'front-page', 'GSWEB12 template override A');
  await addParagraphAndSave(page, 'wp_template_part', 'header', 'GSWEB12 part override A');
  for (const [route, slug] of [['/wp/v2/templates/gama-software//front-page?context=edit', 'front-page'], ['/wp/v2/template-parts/gama-software//header?context=edit', 'header']]) {
    const saved = await rest<any>(page, route);
    expect(saved.slug).toBe(slug);
    expect(saved.source).toBe('custom');
    expect(saved.has_theme_file).toBe(true);
  }
  await page.goto('/');
  await expect(page.getByText('GSWEB12 template override A')).toBeVisible();
  await expect(page.getByText('GSWEB12 part override A')).toBeVisible();
});

test('uses the Site Editor core-data revert action for overrides @reset', async ({ page }) => {
  for (const [type, slug] of [['wp_template', 'front-page'], ['wp_template_part', 'header']] as const) {
    const id = `gama-software//${slug}`;
    await openEditorCanvas(
      page,
      `/wp-admin/site-editor.php?postId=${encodeURIComponent(id)}&postType=${type}&canvas=edit`,
    );
    const result = await page.evaluate(async ({ type, id }) => {
      return (window as any).wp.data.dispatch('core').deleteEntityRecord('postType', type, id, { force: true });
    }, { type, id });
    expect(result.deleted).toBe(true);
  }
  await page.goto('/');
  await expect(page.getByText('GSWEB12 template override A')).toHaveCount(0);
  await expect(page.getByText('GSWEB12 part override A')).toHaveCount(0);
});

test('public routes retain structural accessibility at 320px and a 200% page-scale reflow proxy @public', async ({ page, context }) => {
  const routes = [
    ['/', 'front-page', 200],
    ['/sample-page/', 'page', 200],
    ['/hello-world/', 'single', 200],
    ['/blog/', 'home', 200],
    ['/?m=202609', 'archive', 200],
    ['/?s=Hello', 'search', 200],
    ['/missing-gsweb12/', '404', 404],
  ] as const;
  await page.setViewportSize({ width: 320, height: 640 });
  const cdp = await context.newCDPSession(page);
  await cdp.send('Emulation.setPageScaleFactor', { pageScaleFactor: 2 });
  expect(await page.evaluate(() => window.visualViewport?.scale)).toBe(2);
  for (const [route, marker, expectedStatus] of routes) {
    const response = await page.goto(route);
    expect(response?.status()).toBe(expectedStatus);
    await expect(page.locator(`main.gama-template--${marker}`)).toHaveCount(1);
    await expect(page.locator('header')).toHaveCount(1);
    await expect(page.locator('main')).toHaveCount(1);
    await expect(page.locator('footer')).toHaveCount(1);
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1);
    expect(overflow).toBe(false);
    const headingLevels = await page.locator('h1,h2,h3,h4,h5,h6').evaluateAll((nodes) => nodes.map((node) => Number(node.tagName.slice(1))));
    for (let index = 1; index < headingLevels.length; index += 1) {
      const currentHeadingLevel = headingLevels.at(index);
      const previousHeadingLevel = headingLevels.at(index - 1);
      if (currentHeadingLevel === undefined || previousHeadingLevel === undefined)
        throw new Error('Heading hierarchy inspection lost an expected level.');
      expect(currentHeadingLevel - previousHeadingLevel).toBeLessThanOrEqual(1);
    }
    for (const image of await page.locator('img').all()) {
      await expect(image).toHaveAttribute('alt');
    }
    await page.keyboard.press('Tab');
    expect(await page.evaluate(() => ['A', 'BUTTON', 'INPUT'].includes((document.activeElement as HTMLElement).tagName))).toBe(true);
    await page.evaluate(() => (document.activeElement as HTMLElement).setAttribute('data-gama-keyboard-origin', 'true'));
    await page.keyboard.press('Tab');
    expect(await page.evaluate(() => ['A', 'BUTTON', 'INPUT'].includes((document.activeElement as HTMLElement).tagName))).toBe(true);
    await page.keyboard.press('Shift+Tab');
    expect(await page.evaluate(() => (document.activeElement as HTMLElement).getAttribute('data-gama-keyboard-origin'))).toBe('true');
  }
});
