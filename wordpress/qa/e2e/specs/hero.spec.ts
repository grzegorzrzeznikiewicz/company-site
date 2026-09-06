import {
  expect,
  test,
  type FrameLocator,
  type Page,
} from '@playwright/test';
import {
  assertDiagnosticsClean,
  login,
  openEditorCanvas,
  rest,
  watchWordPressDiagnostics,
  type BrowserDiagnostics,
} from './support/wordpress';

const heroHeading = 'Gama Software';
const heroLead =
  'Specjalizujemy się w wdrożeniach e-commerce, konsultacjach oraz budowaniu agentów AI dla Twojego biznesu';
const heroButton = 'Poznaj nasze usługi';
let diagnostics: BrowserDiagnostics;

test.beforeEach(async ({ page }) => {
  diagnostics = watchWordPressDiagnostics(page, {
    allowRestrictedSettingsResponse: true,
  });
});

test.afterEach(() => {
  assertDiagnosticsClean(diagnostics);
});

async function clearDisposableHomeContent(page: Page): Promise<void> {
  await login(
    page,
    process.env.WP_ADMIN_USER ?? 'theme-admin',
    process.env.WP_ADMIN_PASSWORD ?? 'theme-test-password-only',
  );
  const homes = await rest<any[]>(page, '/wp/v2/pages?slug=home&context=edit');
  expect(homes).toHaveLength(1);
  const updated = await rest<any>(
    page,
    `/wp/v2/pages/${homes[0].id}`,
    'POST',
    { content: '' },
  );
  expect(updated.content.raw).toBe('');
}

function heroSection(page: Page) {
  return page.locator('main section.gama-hero');
}

async function assertHeroReflows(page: Page, width: number): Promise<void> {
  await page.setViewportSize({ width, height: 900 });
  const response = await page.goto('/', { waitUntil: 'domcontentloaded' });
  expect(response?.status()).toBe(200);

  const hero = heroSection(page);
  const heading = hero.getByRole('heading', {
    level: 1,
    name: heroHeading,
  });
  const lead = hero.getByText(heroLead, { exact: true });
  const button = hero.getByRole('link', { name: heroButton });

  await expect(hero).toHaveCount(1);
  await expect(heading).toHaveCount(1);
  await expect(page.locator('main h1')).toHaveCount(1);
  await expect(lead).toHaveCount(1);
  await expect(button).toHaveAttribute('href', '/#services');
  await expect(heading).toHaveCSS(
    'font-size',
    width >= 768 ? '60px' : '48px',
  );
  await expect(lead).toHaveCSS(
    'font-size',
    width >= 768 ? '24px' : '20px',
  );

  const overflow = await page.evaluate(() => {
    const root = document.documentElement;
    const clipped = Array.from(
      document.querySelectorAll('main .gama-hero *'),
    )
      .filter((element) => {
        const rect = element.getBoundingClientRect();
        return (
          rect.width > 0 &&
          (rect.left < -1 || rect.right > window.innerWidth + 1)
        );
      })
      .map((element) => `${element.tagName}.${element.className}`);
    return {
      documentOverflow: root.scrollWidth - root.clientWidth,
      clipped,
    };
  });
  expect(overflow.documentOverflow).toBeLessThanOrEqual(1);
  expect(overflow.clipped).toEqual([]);
}

async function keyboardFocusesHeroButton(page: Page): Promise<void> {
  await page.locator('body').click({ position: { x: 1, y: 1 } });
  await page.evaluate(() =>
    (document.activeElement as HTMLElement | null)?.blur(),
  );
  let focused = false;
  for (let step = 0; step < 60; step += 1) {
    await page.keyboard.press('Tab');
    focused = await page.evaluate(
      () => document.activeElement?.matches('.gama-hero .wp-block-button__link') ?? false,
    );
    if (focused) break;
  }
  expect(focused, 'Keyboard could not reach the Hero CTA.').toBe(true);
  const focus = await page.evaluate(() => {
    const element = document.activeElement as HTMLElement;
    const style = getComputedStyle(element);
    return {
      outlineColor: style.outlineColor,
      outlineStyle: style.outlineStyle,
      outlineWidth: style.outlineWidth,
      outlineOffset: style.outlineOffset,
    };
  });
  expect(focus.outlineStyle).toBe('solid');
  expect(Number.parseFloat(focus.outlineWidth)).toBeGreaterThanOrEqual(3);
  expect(Number.parseFloat(focus.outlineOffset)).toBeGreaterThanOrEqual(3);
  expect(focus.outlineColor).toBe('rgb(21, 93, 252)');
}

async function openFrontPageTemplate(page: Page): Promise<FrameLocator> {
  const templateId = 'gama-software//front-page';
  const frame = await openEditorCanvas(
    page,
    `/wp-admin/site-editor.php?postId=${encodeURIComponent(templateId)}&postType=wp_template&canvas=edit`,
  );
  await expect(frame.locator('section.gama-hero')).toBeVisible();
  return frame;
}

async function saveFrontPageTemplate(page: Page): Promise<void> {
  const save = page.getByRole('button', { name: 'Save', exact: true });
  await expect(save).toBeEnabled();
  await expect(
    page.getByRole('dialog', { name: 'Are you ready to save?' }),
  ).toHaveCount(0);
  await save.click();
  const confirmation = page
    .locator('.components-snackbar__content')
    .getByText('Template updated.', { exact: true });
  await expect(confirmation).toBeVisible({ timeout: 30_000 });
  await expect(save).toBeDisabled({ timeout: 30_000 });
}

test('renders one accessible responsive Hero and keeps its CTA functional without JavaScript @hero', async ({
  page,
  browser,
}) => {
  await clearDisposableHomeContent(page);
  for (const width of [320, 390, 768, 1440]) {
    await assertHeroReflows(page, width);
  }
  await keyboardFocusesHeroButton(page);

  const noJavaScriptContext = await browser.newContext({
    baseURL: process.env.WP_BASE_URL ?? 'http://wordpress',
    javaScriptEnabled: false,
    reducedMotion: 'reduce',
    viewport: { width: 320, height: 640 },
  });
  try {
    const noJavaScriptPage = await noJavaScriptContext.newPage();
    const response = await noJavaScriptPage.goto('/');
    expect(response?.status()).toBe(200);
    const cta = noJavaScriptPage.getByRole('link', { name: heroButton });
    await expect(cta).toHaveAttribute('href', '/#services');
    await cta.click();
    await noJavaScriptPage.waitForURL('http://wordpress/#services');
  } finally {
    await noJavaScriptContext.close();
  }
});

test('lets a scoped Editor change Hero copy and the CTA destination in the Site Editor @hero', async ({
  page,
}) => {
  await login(page, 'theme-navigation-editor', 'navigation-editor-test-only');
  const currentUser = await rest<any>(page, '/wp/v2/users/me?context=edit');
  expect(currentUser.roles).toEqual(['editor']);
  expect(currentUser.capabilities.activate_plugins ?? false).toBe(false);

  const frame = await openFrontPageTemplate(page);
  await frame
    .locator('[data-type="core/heading"]')
    .filter({ hasText: heroHeading })
    .click();
  const editableHeading = frame
    .locator('[data-type="core/heading"][contenteditable="true"]')
    .filter({ hasText: heroHeading });
  await expect(editableHeading).toHaveCount(1);
  await editableHeading.fill('Gama Software dla redaktora');

  await frame.getByText(heroLead, { exact: true }).click();
  const editableLead = frame
    .locator('[data-type="core/paragraph"][contenteditable="true"]')
    .filter({ hasText: heroLead });
  await expect(editableLead).toHaveCount(1);
  await editableLead.fill('Edytowalny opis Hero bez wdrożenia kodu.');

  await frame.getByText(heroButton, { exact: true }).click();
  const editableButton = frame
    .locator('[data-type="core/button"] [contenteditable="true"]')
    .filter({ hasText: heroButton });
  await expect(editableButton).toHaveCount(1);
  await editableButton.fill('Przejdź do oferty');

  await page.getByRole('button', { name: 'Edit link', exact: true }).click();
  const linkControl = page.getByRole('combobox', {
    name: 'Search or type URL',
  });
  await expect(linkControl).toHaveValue('/#services');
  await linkControl.fill('/#services-editor');
  const applyLink = page.getByRole('button', { name: 'Apply', exact: true });
  await expect(applyLink).toBeEnabled();
  await applyLink.click();

  await saveFrontPageTemplate(page);
  const frontPage = await rest<any>(
    page,
    '/wp/v2/templates/gama-software//front-page?context=edit',
  );
  expect(frontPage.source).toBe('custom');
  expect(frontPage.has_theme_file).toBe(true);
  expect(frontPage.content.raw).toContain('Gama Software dla redaktora');
  expect(frontPage.content.raw).toContain(
    'Edytowalny opis Hero bez wdrożenia kodu.',
  );
  expect(frontPage.content.raw).toContain('Przejdź do oferty');
  expect(frontPage.content.raw).toContain('href="/#services-editor"');

  await page.goto('/', { waitUntil: 'domcontentloaded' });
  await expect(
    heroSection(page).getByRole('heading', {
      level: 1,
      name: 'Gama Software dla redaktora',
    }),
  ).toBeVisible();
  await expect(
    heroSection(page).getByText('Edytowalny opis Hero bez wdrożenia kodu.', {
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    heroSection(page).getByRole('link', { name: 'Przejdź do oferty' }),
  ).toHaveAttribute('href', '/#services-editor');
});
