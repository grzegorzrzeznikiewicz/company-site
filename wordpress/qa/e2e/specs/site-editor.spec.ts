import { expect, test, type Page } from '@playwright/test';

const templateSlugs = ['index', 'front-page', 'page', 'single', 'home', 'archive', 'search', '404'];
const partSlugs = ['header', 'footer'];
const browserErrors: string[] = [];

async function login(page: Page): Promise<void> {
  await page.goto('/wp-login.php');
  await page.locator('#user_login').fill(process.env.WP_ADMIN_USER ?? 'theme-admin');
  await page.locator('#user_pass').fill(process.env.WP_ADMIN_PASSWORD ?? 'theme-test-password-only');
  await Promise.all([
    page.waitForURL(/\/wp-admin\//),
    page.locator('#wp-submit').click(),
  ]);
}

async function rest<T>(page: Page, route: string, method = 'GET', body?: unknown): Promise<T> {
  return page.evaluate(async ({ route, method, body }) => {
    const nonce = await fetch('/wp-admin/admin-ajax.php?action=rest-nonce', { credentials: 'same-origin' }).then((response) => response.text());
    const [restPath, restQuery] = route.split('?', 2);
    const response = await fetch(`/index.php?rest_route=${restPath}${restQuery ? `&${restQuery}` : ''}`, {
      method,
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-WP-Nonce': nonce },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    if (!response.ok) throw new Error(`${method} ${route}: ${response.status} ${await response.text()}`);
    return response.json();
  }, { route, method, body }) as Promise<T>;
}

test.beforeEach(async ({ page }, testInfo) => {
  browserErrors.length = 0;
  page.on('console', (message) => {
    const location = message.location().url;
    const expectedMissingRoute = new URL(page.url()).pathname === '/missing-gsweb12/' && message.text().includes('404 (Not Found)');
    if (message.type() === 'error' && !message.text().includes('Failed to load resource: net::ERR_NAME_NOT_RESOLVED') && !expectedMissingRoute) {
      browserErrors.push(`console: ${message.text()}${location ? ` at ${location}` : ''}`);
    }
  });
  page.on('pageerror', (error) => browserErrors.push(`pageerror: ${error.message}`));
  page.on('requestfailed', (request) => {
    const host = new URL(request.url()).hostname;
    if (!['secure.gravatar.com', 's.w.org'].includes(host) && request.failure()?.errorText !== 'net::ERR_ABORTED') {
      browserErrors.push(`requestfailed: ${request.url()} ${request.failure()?.errorText ?? ''}`);
    }
  });
  if (!testInfo.title.includes('@public')) {
    await login(page);
  }
});

test.afterEach(() => {
  expect(browserErrors, browserErrors.join('\n')).toEqual([]);
});

test('opens every template and part in the Site Editor @open', async ({ page }) => {
  for (const slug of templateSlugs) {
    const entity = await rest<any>(page, `/wp/v2/templates/gama-software//${slug}?context=edit`);
    expect(entity.slug).toBe(slug);
    expect(entity.theme).toBe('gama-software');
    const id = encodeURIComponent(`gama-software//${slug}`);
    await page.goto(`/wp-admin/site-editor.php?postId=${id}&postType=wp_template&canvas=edit`);
    expect(new URL(page.url()).pathname).toBe('/wp-admin/site-editor.php');
    await expect(page.locator('iframe[name="editor-canvas"]')).toBeVisible();
    await expect(page.frameLocator('iframe[name="editor-canvas"]').locator(`main.gama-template--${slug}`)).toHaveCount(1);
  }
  for (const slug of partSlugs) {
    const entity = await rest<any>(page, `/wp/v2/template-parts/gama-software//${slug}?context=edit`);
    expect(entity.slug).toBe(slug);
    expect(entity.theme).toBe('gama-software');
    const id = encodeURIComponent(`gama-software//${slug}`);
    await page.goto(`/wp-admin/site-editor.php?postId=${id}&postType=wp_template_part&canvas=edit`);
    expect(new URL(page.url()).pathname).toBe('/wp-admin/site-editor.php');
    await expect(page.locator('iframe[name="editor-canvas"]')).toBeVisible();
    await expect(page.frameLocator('iframe[name="editor-canvas"]').locator(`.gama-site-${slug}`)).toHaveCount(1);
  }
});

async function addParagraphAndSave(page: Page, type: 'wp_template' | 'wp_template_part', slug: string, content: string): Promise<void> {
  const recordId = `gama-software//${slug}`;
  const id = encodeURIComponent(recordId);
  await page.goto(`/wp-admin/site-editor.php?postId=${id}&postType=${type}&canvas=edit`);
  await expect(page.locator('iframe[name="editor-canvas"]')).toBeVisible();
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
    await page.goto(`/wp-admin/site-editor.php?postId=${encodeURIComponent(id)}&postType=${type}&canvas=edit`);
    await expect(page.locator('iframe[name="editor-canvas"]')).toBeVisible();
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
      expect(headingLevels[index] - headingLevels[index - 1]).toBeLessThanOrEqual(1);
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
