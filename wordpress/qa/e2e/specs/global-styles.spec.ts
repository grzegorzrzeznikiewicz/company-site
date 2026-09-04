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

const palette = [
  ['base', '#ffffff'],
  ['surface-subtle', '#f9fafb'],
  ['border-subtle', '#e5e7eb'],
  ['text-strong', '#101828'],
  ['text', '#364153'],
  ['text-muted', '#4a5565'],
  ['text-card-muted', '#717182'],
  ['text-on-dark-muted', '#99a1af'],
  ['surface-inverse', '#101828'],
  ['accent-soft', '#dbeafe'],
  ['accent', '#155dfc'],
] as const;
const fontSizes = [
  ['small', '.875rem'],
  ['body', '1rem'],
  ['button', '1.125rem'],
  ['lead', '1.25rem'],
  ['heading-3', '1.5rem'],
  ['heading-2', '2.25rem'],
  ['display', '3rem'],
  ['display-large', '3.75rem'],
] as const;
const spacingSizes = [
  ['sm', '.5rem'],
  ['md', '1rem'],
  ['lg', '1.5rem'],
  ['xl', '2rem'],
  ['xxl', '3rem'],
  ['section', '5rem'],
] as const;
const shadowSlugs = ['elevation-1', 'elevation-2', 'elevation-3'];
let diagnostics: BrowserDiagnostics;

function rgb(hex: string): string {
  const value = Number.parseInt(hex.slice(1), 16);
  return `rgb(${(value >> 16) & 255}, ${(value >> 8) & 255}, ${value & 255})`;
}

function channel(value: number): number {
  const normalized = value / 255;
  return normalized <= 0.04045
    ? normalized / 12.92
    : ((normalized + 0.055) / 1.055) ** 2.4;
}

function luminance(color: string): number {
  const values = color
    .match(/[\d.]+/g)
    ?.slice(0, 3)
    .map(Number);
  if (!values || values.length !== 3)
    throw new Error(`Unsupported color: ${color}`);
  return (
    0.2126 * channel(values[0]) +
    0.7152 * channel(values[1]) +
    0.0722 * channel(values[2])
  );
}

function contrast(a: string, b: string): number {
  const values = [luminance(a), luminance(b)];
  return (Math.max(...values) + 0.05) / (Math.min(...values) + 0.05);
}

async function hideCaret(page: Page): Promise<void> {
  await page.addStyleTag({
    content: '* { caret-color: transparent !important; }',
  });
}

async function waitForExactEditorParagraph(
  frame: FrameLocator,
  expectedText: string,
): Promise<void> {
  if (expectedText.trim() === '')
    throw new Error('The editor readiness fixture must be non-empty.');
  const paragraph = frame
    .locator('[data-type="core/paragraph"]')
    .filter({ hasText: expectedText });
  await expect(paragraph).toHaveCount(1, { timeout: 45_000 });
  await expect(paragraph).toHaveText(expectedText, { timeout: 45_000 });
}

type PrimitiveStyles = Record<string, Record<string, string>>;

async function primitiveStyles(
  page: Page,
  rootSelector: string,
): Promise<PrimitiveStyles> {
  return page.locator(rootSelector).evaluate((root) => {
    const selectors = {
      root: ':scope',
      h1: 'h1',
      h2: 'h2',
      h3: 'h3',
      link: '.gama-fixture-link',
      button: '.wp-block-button__link',
      small: '.has-small-font-size',
      body: '.has-body-font-size',
      buttonPreset: '.gama-fixture-button-preset',
      lead: '.has-lead-font-size',
      heading3: '.gama-fixture-heading-3-preset',
      heading2: '.gama-fixture-heading-2-preset',
      display: '.has-display-font-size',
      displayLarge: '.has-display-large-font-size',
      subtle: '.gama-fixture-subtle',
      card: '.gama-fixture-card',
      soft: '.gama-fixture-soft',
      inverse: '.gama-fixture-inverse',
    };
    return Object.fromEntries(
      Object.entries(selectors).map(([name, selector]) => {
        const element =
          selector === ':scope' ? document.body : root.querySelector(selector);
        if (!element)
          throw new Error(`Missing primitive ${name}`);
        const style = getComputedStyle(element);
        return [
          name,
          {
            fontFamily: style.fontFamily,
            fontSize: style.fontSize,
            fontWeight: style.fontWeight,
            lineHeight: style.lineHeight,
            color: style.color,
            backgroundColor: style.backgroundColor,
            borderRadius: style.borderRadius,
            boxShadow: style.boxShadow,
            paddingTop: style.paddingTop,
          },
        ];
      }),
    );
  });
}

function assertPrimitiveContract(
  styles: PrimitiveStyles,
  desktopType: boolean,
): void {
  expect(styles.root.fontFamily).toContain('ui-sans-serif');
  expect(styles.root.fontSize).toBe('16px');
  expect(styles.root.fontWeight).toBe('400');
  expect(styles.root.lineHeight).toBe('24px');
  expect(styles.root.color).toBe(rgb('#364153'));
  expect(styles.root.backgroundColor).toBe(rgb('#ffffff'));
  expect(styles.h1.fontSize).toBe(desktopType ? '60px' : '48px');
  expect(styles.h1.fontWeight).toBe('500');
  expect(styles.h1.lineHeight).toBe(desktopType ? '60px' : '48px');
  expect(styles.h1.color).toBe(rgb('#101828'));
  expect(styles.h2.fontSize).toBe('36px');
  expect(styles.h2.fontWeight).toBe('500');
  expect(styles.h2.lineHeight).toBe('40px');
  expect(styles.h3.fontSize).toBe('24px');
  expect(styles.h3.fontWeight).toBe('500');
  expect(styles.h3.lineHeight).toBe('32px');
  expect(styles.link.color).toBe(rgb('#155dfc'));
  expect(styles.button.fontSize).toBe('18px');
  expect(styles.button.fontWeight).toBe('500');
  expect(styles.button.lineHeight).toBe('28px');
  expect(styles.button.backgroundColor).toBe(rgb('#155dfc'));
  expect(styles.button.color).toBe(rgb('#ffffff'));
  expect(styles.button.borderRadius).toBe('8px');
  expect(styles.small.lineHeight).toBe('20px');
  expect(styles.body.lineHeight).toBe('24px');
  expect(styles.buttonPreset.lineHeight).toBe('28px');
  expect(styles.lead.fontSize).toBe(desktopType ? '24px' : '20px');
  expect(styles.lead.lineHeight).toBe(desktopType ? '32px' : '28px');
  expect(styles.heading3.lineHeight).toBe('32px');
  expect(styles.heading2.lineHeight).toBe('40px');
  expect(styles.display.lineHeight).toBe(desktopType ? '60px' : '48px');
  expect(styles.displayLarge.lineHeight).toBe('60px');
  expect(styles.subtle.backgroundColor).toBe(rgb('#f9fafb'));
  expect(styles.card.color).toBe(rgb('#717182'));
  expect(styles.card.borderRadius).toBe('14px');
  expect(styles.card.boxShadow).not.toBe('none');
  expect(styles.card.paddingTop).toBe('24px');
  expect(styles.soft.backgroundColor).toBe(rgb('#dbeafe'));
  expect(styles.inverse.backgroundColor).toBe(rgb('#101828'));
  expect(styles.inverse.color).toBe(rgb('#99a1af'));
}

async function assertNoOverflow(page: Page): Promise<void> {
  const result = await page.evaluate(() => {
    const documentOverflow =
      document.documentElement.scrollWidth -
      document.documentElement.clientWidth;
    const clipped = Array.from(document.querySelectorAll('main *'))
      .filter((element) => {
        const rect = element.getBoundingClientRect();
        return (
          rect.width > 0 &&
          (rect.left < -1 || rect.right > window.innerWidth + 1)
        );
      })
      .map((element) => `${element.tagName}.${element.className}`);
    return { documentOverflow, clipped };
  });
  expect(result.documentOverflow).toBeLessThanOrEqual(1);
  expect(result.clipped).toEqual([]);
}

async function keyboardFocus(page: Page, selector: string): Promise<void> {
  await page.locator('body').click({ position: { x: 1, y: 1 } });
  await page.evaluate(() =>
    (document.activeElement as HTMLElement | null)?.blur(),
  );
  let found = false;
  for (let step = 0; step < 60; step += 1) {
    await page.keyboard.press('Tab');
    found = await page.evaluate(
      (candidate) => document.activeElement?.matches(candidate) ?? false,
      selector,
    );
    if (found) break;
  }
  expect(found, `Keyboard could not reach ${selector}`).toBe(true);
  const focus = await page.evaluate(() => {
    const element = document.activeElement as HTMLElement;
    const style = getComputedStyle(element);
    const rect = element.getBoundingClientRect();
    let ancestor = element.parentElement;
    let background = 'rgba(0, 0, 0, 0)';
    while (ancestor) {
      const value = getComputedStyle(ancestor).backgroundColor;
      if (value !== 'rgba(0, 0, 0, 0)' && value !== 'transparent') {
        background = value;
        break;
      }
      ancestor = ancestor.parentElement;
    }
    return {
      outlineColor: style.outlineColor,
      outlineStyle: style.outlineStyle,
      outlineWidth: style.outlineWidth,
      outlineOffset: style.outlineOffset,
      boxShadow: style.boxShadow,
      background,
      rect: {
        left: rect.left,
        right: rect.right,
        top: rect.top,
        bottom: rect.bottom,
      },
      viewport: { width: innerWidth, height: innerHeight },
    };
  });
  expect(focus.outlineStyle).toBe('solid');
  expect(Number.parseFloat(focus.outlineWidth)).toBeGreaterThanOrEqual(3);
  expect(Number.parseFloat(focus.outlineOffset)).toBeGreaterThanOrEqual(3);
  expect(focus.outlineColor).toBe(rgb('#155dfc'));
  expect(focus.boxShadow).toContain(rgb('#ffffff'));
  expect(contrast(focus.outlineColor, focus.background)).toBeGreaterThanOrEqual(
    3,
  );
  expect(focus.rect.left).toBeGreaterThanOrEqual(-1);
  expect(focus.rect.right).toBeLessThanOrEqual(focus.viewport.width + 1);
  expect(focus.rect.top).toBeGreaterThanOrEqual(-1);
  expect(focus.rect.bottom).toBeLessThanOrEqual(focus.viewport.height + 1);
}

test.beforeEach(async ({ page }) => {
  diagnostics = watchWordPressDiagnostics(page, {
    allowRestrictedSettingsResponse: true,
  });
});

test.afterEach(() => {
  assertDiagnosticsClean(diagnostics);
});

test('exposes only approved editor choices and lets an Editor save a preset in the ordinary editor @global-styles @global-styles-editor-choices', async ({
  page,
}) => {
  await login(
    page,
    process.env.WP_EDITOR_USER ?? 'style-editor',
    process.env.WP_EDITOR_PASSWORD ?? 'style-editor-test-only',
  );
  const currentUser = await rest<any>(page, '/wp/v2/users/me?context=edit');
  expect(currentUser.slug).toBe('style-editor');
  const fixtures = await rest<any[]>(
    page,
    '/wp/v2/pages?slug=editor-preset-fixture&context=edit',
  );
  expect(fixtures).toHaveLength(1);
  const fixture = fixtures[0];
  const frame = await openEditorCanvas(
    page,
    `/wp-admin/post.php?post=${fixture.id}&action=edit`,
  );
  await waitForExactEditorParagraph(frame, 'Editor preset fixture');
  const editorSettings = await page.evaluate(() => {
    const settings = (window as any).wp.data
      .select('core/block-editor')
      .getSettings();
    const features = settings.__experimentalFeatures;
    return {
      colors: settings.colors.map(({ slug, color }: any) => [slug, color]),
      gradients: settings.gradients,
      fontSizes: settings.fontSizes.map(({ slug, size }: any) => [slug, size]),
      spacingSizes: features.spacing.spacingSizes.theme.map(
        ({ slug, size }: any) => [slug, size],
      ),
      shadows: features.shadow.presets.theme.map(({ slug }: any) => slug),
      fontFamilies: features.typography.fontFamilies.theme.map(
        ({ slug }: any) => slug,
      ),
      flags: {
        disableCustomColors: settings.disableCustomColors,
        disableCustomGradients: settings.disableCustomGradients,
        disableCustomFontSizes: settings.disableCustomFontSizes,
        disableCustomSpacingSizes: settings.disableCustomSpacingSizes,
        enableCustomLineHeight: settings.enableCustomLineHeight,
        enableCustomSpacing: settings.enableCustomSpacing,
        enableCustomUnits: settings.enableCustomUnits,
      },
      allowedBlockTypes: settings.allowedBlockTypes,
    };
  });
  expect(editorSettings.colors).toEqual(palette);
  expect(editorSettings.gradients).toEqual([]);
  expect(editorSettings.fontSizes).toEqual(fontSizes);
  expect(editorSettings.spacingSizes).toEqual(spacingSizes);
  expect(editorSettings.shadows).toEqual(shadowSlugs);
  expect(editorSettings.fontFamilies).toEqual(['system-sans']);
  expect(editorSettings.flags).toEqual({
    disableCustomColors: true,
    disableCustomGradients: true,
    disableCustomFontSizes: true,
    disableCustomSpacingSizes: true,
    enableCustomLineHeight: false,
    enableCustomSpacing: true,
    enableCustomUnits: ['px', 'rem', '%'],
  });
  expect(editorSettings.allowedBlockTypes).toContain('core/paragraph');
  expect(editorSettings.allowedBlockTypes).not.toContain('core/html');
  const saved = await page.evaluate(async () => {
    const wp = (window as any).wp;
    const block = wp.data.select('core/block-editor').getBlocks()[0];
    if (!block || block.name !== 'core/paragraph')
      throw new Error('Expected the fixture paragraph.');
    wp.data
      .dispatch('core/block-editor')
      .updateBlockAttributes(block.clientId, { fontSize: 'lead' });
    await wp.data.dispatch('core/editor').savePost();
    return wp.data.select('core/editor').getCurrentPost().status;
  });
  expect(saved).toBe('publish');
  const updated = await rest<any>(
    page,
    `/wp/v2/pages/${fixture.id}?context=edit`,
  );
  expect(updated.content.raw).toContain('"fontSize":"lead"');
  await page.goto('/editor-preset-fixture/', { waitUntil: 'domcontentloaded' });
  const paragraph = page
    .locator('p.has-lead-font-size')
    .filter({ hasText: 'Editor preset fixture' });
  await expect(paragraph).toHaveClass(/has-lead-font-size/);
  await expect(paragraph).toHaveCSS('font-size', '24px');
  await expect(paragraph).toHaveCSS('line-height', '32px');
});

test('renders exact primitives without overflow across the responsive matrix @global-styles @global-styles-front-snapshots', async ({
  page,
}) => {
  for (const [width, expectedPadding] of [
    [320, 16],
    [390, 16],
    [768, 24],
    [1024, 32],
    [1440, 32],
  ] as const) {
    await page.setViewportSize({ width, height: 900 });
    const response = await page.goto('/');
    expect(response?.status()).toBe(200);
    await hideCaret(page);
    const fixture = page.locator('.gama-global-styles-fixture');
    await expect(fixture).toBeVisible();
    const styles = await primitiveStyles(page, '.gama-global-styles-fixture');
    assertPrimitiveContract(styles, width >= 768);
    const rootPadding = await page
      .locator('main.gama-template--front-page')
      .evaluate((element) => {
        const style = getComputedStyle(element);
        return [
          Number.parseFloat(style.paddingLeft),
          Number.parseFloat(style.paddingRight),
        ];
      });
    expect(rootPadding).toEqual([expectedPadding, expectedPadding]);
    await assertNoOverflow(page);
    const image = fixture.locator('img');
    await expect(image).toHaveAttribute('alt', 'Responsive fixture media');
    const mediaFits = await image.evaluate(
      (element) =>
        element.getBoundingClientRect().width <=
        element.parentElement!.getBoundingClientRect().width + 1,
    );
    expect(mediaFits).toBe(true);
  }
  for (const width of [390, 768, 1440] as const) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto('/');
    await page.addStyleTag({
      content:
        '#blog.gama-blog-latest, #contact.gama-contact { display: none !important; }',
    });
    await hideCaret(page);
    await expect(page).toHaveScreenshot(`global-styles-front-${width}.png`, {
      fullPage: true,
      animations: 'disabled',
    });
  }
  expect(contrast(rgb('#101828'), rgb('#ffffff'))).toBeGreaterThanOrEqual(4.5);
  expect(contrast(rgb('#4a5565'), rgb('#ffffff'))).toBeGreaterThanOrEqual(4.5);
  expect(contrast(rgb('#717182'), rgb('#ffffff'))).toBeGreaterThanOrEqual(4.5);
  expect(contrast(rgb('#ffffff'), rgb('#155dfc'))).toBeGreaterThanOrEqual(4.5);
  expect(contrast(rgb('#99a1af'), rgb('#101828'))).toBeGreaterThanOrEqual(4.5);
});

test('keeps the same primitive styles in the editor canvas @global-styles @global-styles-editor-snapshots', async ({
  page,
}) => {
  test.setTimeout(90_000);
  await login(
    page,
    process.env.WP_ADMIN_USER ?? 'theme-admin',
    process.env.WP_ADMIN_PASSWORD ?? 'theme-test-password-only',
  );
  const home = await rest<any[]>(page, '/wp/v2/pages?slug=home&context=edit');
  expect(home).toHaveLength(1);
  for (const width of [390, 768, 1440] as const) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto('/');
    const front = await primitiveStyles(page, '.gama-global-styles-fixture');
    const frame = await openEditorCanvas(
      page,
      `/wp-admin/post.php?post=${home[0].id}&action=edit`,
    );
    await waitForExactEditorParagraph(
      frame,
      'Body primitive with a visible text link.',
    );
    await frame.locator('body').evaluate((body) => {
      const style = document.createElement('style');
      style.textContent = '* { caret-color: transparent !important; }';
      body.append(style);
    });
    const editorFixture = frame.locator(
      '[data-type="core/group"].gama-global-styles-fixture',
    );
    await expect(editorFixture).toBeVisible();
    await expect(editorFixture.locator('.gama-fixture-link')).toBeVisible();
    const editor = (await editorFixture.evaluate((root) => {
      const selectors = {
        root: ':scope',
        h1: 'h1',
        h2: 'h2',
        h3: 'h3',
        link: '.gama-fixture-link',
        button: '.wp-block-button__link',
        small: '.has-small-font-size',
        body: '.has-body-font-size',
        buttonPreset: '.gama-fixture-button-preset',
        lead: '.has-lead-font-size',
        heading3: '.gama-fixture-heading-3-preset',
        heading2: '.gama-fixture-heading-2-preset',
        display: '.has-display-font-size',
        displayLarge: '.has-display-large-font-size',
        subtle: '.gama-fixture-subtle',
        card: '.gama-fixture-card',
        soft: '.gama-fixture-soft',
        inverse: '.gama-fixture-inverse',
      };
      return Object.fromEntries(
        Object.entries(selectors).map(([name, selector]) => {
          const element =
            selector === ':scope'
              ? root.closest('.editor-styles-wrapper')
              : root.querySelector(selector);
          if (!element)
            throw new Error(`Missing editor primitive ${name}`);
          const style = getComputedStyle(element);
          return [
            name,
            {
              fontFamily: style.fontFamily,
              fontSize: style.fontSize,
              fontWeight: style.fontWeight,
              lineHeight: style.lineHeight,
              color: style.color,
              backgroundColor: style.backgroundColor,
              borderRadius: style.borderRadius,
              boxShadow: style.boxShadow,
              paddingTop: style.paddingTop,
            },
          ];
        }),
      );
    })) as PrimitiveStyles;
    assertPrimitiveContract(editor, width >= 768);
    expect(editor).toEqual(front);
    const editorRootPadding = await frame
      .locator('.is-root-container')
      .evaluate((element) =>
        Number.parseFloat(getComputedStyle(element).paddingLeft),
      );
    expect(editorRootPadding).toBe(width >= 1024 ? 32 : width >= 768 ? 24 : 16);
    await expect(
      page.locator('iframe[name="editor-canvas"]'),
    ).toHaveScreenshot(`global-styles-editor-${width}.png`, {
      animations: 'disabled',
    });
  }
});

test('provides keyboard-visible focus for every current Core interactive surface @global-styles @global-styles-focus', async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 900 });
  await page.goto('/');
  for (const selector of [
    'header .wp-block-site-logo a',
    'header .wp-block-navigation__responsive-container-open',
    '.gama-fixture-link',
    '.wp-block-button__link',
    '.wp-block-search__input',
    '.wp-block-search__button',
    'footer .wp-block-site-logo a',
    'footer .wp-block-navigation-item__content',
  ]) {
    await keyboardFocus(page, selector);
  }
  await page.goto('/blog/');
  await keyboardFocus(page, '.wp-block-query-pagination a');
  await page.goto('/hello-world/');
  await keyboardFocus(page, '.wp-block-post-navigation-link a');
});

test('persists an Administrator Global Styles change and reflects it publicly @global-styles @global-styles-admin-persistence', async ({
  page,
}) => {
  test.setTimeout(90_000);
  await login(
    page,
    process.env.WP_ADMIN_USER ?? 'theme-admin',
    process.env.WP_ADMIN_PASSWORD ?? 'theme-test-password-only',
  );
  await openEditorCanvas(page, '/wp-admin/site-editor.php?path=%2Fstyles');
  const saved = await page.evaluate(async () => {
    const wp = (window as any).wp;
    const id = await wp.data
      .resolveSelect('core')
      .__experimentalGetCurrentGlobalStylesId();
    const record = await wp.data
      .resolveSelect('core')
      .getEntityRecord('root', 'globalStyles', id);
    const styles = {
      ...(record.styles ?? {}),
      color: {
        ...(record.styles?.color ?? {}),
        background: 'var:preset|color|surface-subtle',
      },
    };
    wp.data
      .dispatch('core')
      .editEntityRecord('root', 'globalStyles', id, { styles });
    return wp.data
      .dispatch('core')
      .saveEditedEntityRecord('root', 'globalStyles', id);
  });
  expect(saved.styles.color.background).toBe(
    'var(--wp--preset--color--surface-subtle)',
  );
  await page.goto('/');
  await expect(page.locator('body')).toHaveCSS(
    'background-color',
    rgb('#f9fafb'),
  );
  await expect(page.locator('.gama-global-styles-fixture')).toBeVisible();
});

test('checks DPR2 only as automation and does not satisfy the native 200% zoom checkpoint @global-styles @global-styles-dpr2', async ({
  browser,
}) => {
  const context = await browser.newContext({
    baseURL: process.env.WP_BASE_URL ?? 'http://wordpress',
    viewport: { width: 320, height: 640 },
    deviceScaleFactor: 2,
    reducedMotion: 'reduce',
  });
  const page = await context.newPage();
  const response = await page.goto('/');
  expect(response?.status()).toBe(200);
  expect(await page.evaluate(() => window.devicePixelRatio)).toBe(2);
  await assertNoOverflow(page);
  await context.close();
});
