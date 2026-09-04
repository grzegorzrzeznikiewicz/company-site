import {
  expect,
  test,
  type FrameLocator,
  type Locator,
  type Page,
  type TestInfo,
} from '@playwright/test';
import {
  assertDiagnosticsClean,
  login,
  openEditorCanvas,
  rest,
  watchWordPressDiagnostics,
  type BrowserDiagnostics,
} from './support/wordpress';

const publicRoutes = [
  ['/', 'front-page', 200],
  ['/sample-page/', 'page', 200],
  ['/hello-world/', 'single', 200],
  ['/blog/', 'home', 200],
  ['/missing-gsweb14/', '404', 404],
] as const;

const initialPrimaryLinks = [
  ['Start', '/#home'],
  ['Usługi', '/#services'],
  ['Moduły', '/#modules'],
  ['Blog', '/blog/'],
  ['Kontakt', '/#contact'],
] as const;

const persistedMobileWidths = [320, 390] as const;

type StoredNavigationAttributes = {
  ariaLabel?: string;
  className?: string;
  overlayMenu?: string;
  style?: Record<string, unknown>;
};

let diagnostics: BrowserDiagnostics;

test.beforeEach(async ({ page }) => {
  diagnostics = watchWordPressDiagnostics(page, {
    allowRestrictedSettingsResponse: true,
    expectedMissingPaths: ['/missing-gsweb14/'],
  });
});

test.afterEach(() => {
  assertDiagnosticsClean(diagnostics);
});

function primaryNavigation(page: Page): Locator {
  return page.getByRole('navigation', { name: 'Główna nawigacja' });
}

function auxiliaryNavigation(page: Page): Locator {
  return page.getByRole('navigation', { name: 'Nawigacja pomocnicza' });
}

function extractNavigationBlockAttributes(
  serialized: string,
): StoredNavigationAttributes | undefined {
  const marker = /<!--\s+wp:navigation(?=\s|\/-->|-->)/.exec(serialized);
  if (marker === null) {
    return undefined;
  }

  let cursor = marker.index + marker[0].length;
  while (/\s/.test(serialized.charAt(cursor))) {
    cursor += 1;
  }
  if (
    serialized.startsWith('/-->', cursor) ||
    serialized.startsWith('-->', cursor)
  ) {
    return {};
  }
  if (serialized.charAt(cursor) !== '{') {
    return undefined;
  }

  const jsonStart = cursor;
  let depth = 0;
  let escaped = false;
  let inString = false;
  for (; cursor < serialized.length; cursor += 1) {
    const character = serialized.charAt(cursor);
    if (inString) {
      if (escaped) {
        escaped = false;
      } else if (character === '\\') {
        escaped = true;
      } else if (character === '"') {
        inString = false;
      }
      continue;
    }
    if (character === '"') {
      inString = true;
    } else if (character === '{') {
      depth += 1;
    } else if (character === '}') {
      depth -= 1;
      if (depth === 0) {
        cursor += 1;
        break;
      }
    }
  }
  if (depth !== 0 || inString) {
    return undefined;
  }

  const json = serialized.slice(jsonStart, cursor);
  while (/\s/.test(serialized.charAt(cursor))) {
    cursor += 1;
  }
  if (
    !serialized.startsWith('/-->', cursor) &&
    !serialized.startsWith('-->', cursor)
  ) {
    return undefined;
  }

  try {
    return JSON.parse(json) as StoredNavigationAttributes;
  } catch {
    return undefined;
  }
}

async function assertNoHorizontalOverflow(page: Page): Promise<void> {
  const overflow = await page.evaluate(() => ({
    document: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    clipped: Array.from(
      document.querySelectorAll(
        '.gama-site-header *, .gama-site-footer *',
      ),
    )
      .filter((element) => {
        const rect = element.getBoundingClientRect();
        return (
          rect.width > 0 &&
          (rect.left < -1 || rect.right > window.innerWidth + 1)
        );
      })
      .map((element) => `${element.tagName}.${element.className}`),
  }));
  expect(overflow.document).toBeLessThanOrEqual(1);
  expect(overflow.clipped).toEqual([]);
}

async function assertDocumentScrollUnlocked(page: Page): Promise<void> {
  expect(
    await page
      .locator('html')
      .evaluate((element) => getComputedStyle(element).overflow),
  ).not.toBe('hidden');
}

async function assertLandmarksAndLogo(page: Page): Promise<void> {
  await expect(page.locator('header.gama-site-header')).toHaveCount(1);
  await expect(page.locator('main')).toHaveCount(1);
  await expect(page.locator('footer.gama-site-footer')).toHaveCount(1);
  await expect(primaryNavigation(page)).toHaveCount(1);
  await expect(auxiliaryNavigation(page)).toHaveCount(1);

  const skipLink = page.locator('#wp-skip-link');
  await expect(skipLink).toHaveCount(1);
  await expect(skipLink).toHaveAttribute('href', '#wp--skip-link--target');
  await expect(page.locator('main#wp--skip-link--target')).toHaveCount(1);

  const logos = page.locator('.wp-block-site-logo img');
  await expect(logos).toHaveCount(2);
  for (const logo of await logos.all()) {
    await expect(logo).toHaveAttribute('alt', 'Gama Software');
    await expect(logo).not.toHaveAttribute('alt', /\.png$/i);
  }
  const logoLinks = page.getByRole('link', { name: 'Gama Software' });
  await expect(logoLinks).toHaveCount(2);
  for (const link of await logoLinks.all()) {
    await expect(link).toHaveAttribute('href', 'http://wordpress/');
  }
}

async function assertPersistedMobileNavigation(
  page: Page,
  width: (typeof persistedMobileWidths)[number],
): Promise<void> {
  await page.setViewportSize({ width, height: 844 });
  const response = await page.goto('/sample-page/');
  expect(response?.status()).toBe(200);
  await assertNoHorizontalOverflow(page);

  const primary = primaryNavigation(page);
  const open = primary.getByRole('button', { name: 'Open menu' });
  await expect(open).toBeVisible();
  await expect(open).toHaveAttribute('aria-haspopup', 'dialog');
  await expect(open).toHaveAttribute('aria-expanded', 'false');
  const controlledId = await open.getAttribute('aria-controls');
  expect(controlledId).toMatch(/^modal-[0-9]+$/);
  await expect(page.locator(`#${controlledId}`)).toHaveCount(1);
  await assertDocumentScrollUnlocked(page);

  await open.focus();
  await page.keyboard.press('Enter');
  await expect(open).toHaveAttribute('aria-expanded', 'true');
  await expect(page.locator('html')).toHaveClass(/has-modal-open/);
  expect(
    await page
      .locator('html')
      .evaluate((element) => getComputedStyle(element).overflow),
  ).toBe('hidden');
  const dialog = primary.getByRole('dialog', { name: 'Menu' });
  await expect(dialog).toHaveAttribute('aria-modal', 'true');
  await expect(dialog.getByRole('link', { name: 'Oferta' })).toBeVisible();

  await page.keyboard.press('Escape');
  await expect(open).toHaveAttribute('aria-expanded', 'false');
  await expect(page.locator('html')).not.toHaveClass(/has-modal-open/);
  await assertDocumentScrollUnlocked(page);
  expect(await open.evaluate((element) => element === document.activeElement)).toBe(
    true,
  );
}

test('renders one semantic shell and the exact editable fallback links on every required route @navigation-initial', async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  for (const [route, marker, expectedStatus] of publicRoutes) {
    const response = await page.goto(route);
    expect(response?.status()).toBe(expectedStatus);
    await expect(page.locator(`main.gama-template--${marker}`)).toHaveCount(1);
    await assertLandmarksAndLogo(page);

    const primary = primaryNavigation(page);
    const links = primary.getByRole('link');
    await expect(links).toHaveCount(initialPrimaryLinks.length);
    for (const [index, [label, pathname]] of initialPrimaryLinks.entries()) {
      const link = links.nth(index);
      await expect(link).toHaveText(label);
      await expect(link).toHaveAttribute('href', pathname);
      expect(await link.evaluate((element) => (element as HTMLAnchorElement).href)).toBe(
        `http://wordpress${pathname}`,
      );
    }
    const auxiliary = auxiliaryNavigation(page).getByRole('link');
    await expect(auxiliary).toHaveCount(1);
    await expect(auxiliary).toHaveText('Kontakt');
    await expect(auxiliary).toHaveAttribute('href', '/#contact');
    expect(
      await auxiliary.evaluate(
        (element) => (element as HTMLAnchorElement).href,
      ),
    ).toBe('http://wordpress/#contact');
    await expect(page.locator('a[href="#"]')).toHaveCount(0);
  }

  await page.goto('/sample-page/');
  await primaryNavigation(page).getByRole('link', { name: 'Usługi' }).click();
  await page.waitForURL('http://wordpress/#services');
  expect(new URL(page.url()).pathname).toBe('/');
  expect(new URL(page.url()).hash).toBe('#services');
});

test('switches only the primary Core Navigation at 768px and keeps sticky surfaces reflowable @navigation-initial', async ({
  page,
}, testInfo) => {
  for (const width of [320, 599, 600, 767, 768, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto('/', { waitUntil: 'domcontentloaded' });
    const header = page.locator('header.gama-site-header');
    const primary = primaryNavigation(page);
    const open = primary.locator(
      '.wp-block-navigation__responsive-container-open',
    );
    const container = primary.locator(
      '.wp-block-navigation__responsive-container',
    );
    expect(await header.evaluate((element) => getComputedStyle(element).position)).toBe(
      'sticky',
    );
    expect(await header.evaluate((element) => getComputedStyle(element).top)).toBe(
      '0px',
    );
    expect(
      Number(
        await header.evaluate((element) => getComputedStyle(element).zIndex),
      ),
    ).toBeLessThan(100000);
    if (width < 768) {
      await expect(open).toBeVisible();
      await expect(container).toBeHidden();
    } else {
      await expect(open).toBeHidden();
      await expect(container).toBeVisible();
    }
    await expect(
      auxiliaryNavigation(page).locator(
        '.wp-block-navigation__responsive-container-open',
      ),
    ).toHaveCount(0);
    await assertNoHorizontalOverflow(page);
    if ([320, 768, 1440].includes(width)) {
      await page.screenshot({
        path: testInfo.outputPath(`navigation-shell-${width}.png`),
        fullPage: true,
      });
    }
  }

  await login(page);
  for (const [width, expectedTop] of [
    [320, '46px'],
    [768, '46px'],
    [1440, '32px'],
  ] as const) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto('/', { waitUntil: 'domcontentloaded' });
    await expect(page.locator('#wpadminbar')).toBeVisible();
    expect(
      await page
        .locator('header.gama-site-header')
        .evaluate((element) => getComputedStyle(element).top),
    ).toBe(expectedTop);
    await assertNoHorizontalOverflow(page);
  }
});

test('uses the Core mobile dialog for keyboard focus, state, Escape and scroll lock @navigation-initial', async ({
  page,
}, testInfo) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/sample-page/');
  const primary = primaryNavigation(page);
  const open = primary.getByRole('button', { name: 'Open menu' });
  await expect(open).toHaveAttribute('aria-haspopup', 'dialog');
  await expect(open).toHaveAttribute('aria-expanded', 'false');
  const controlledId = await open.getAttribute('aria-controls');
  expect(controlledId).toMatch(/^modal-[0-9]+$/);
  await expect(page.locator(`#${controlledId}`)).toHaveCount(1);
  await assertDocumentScrollUnlocked(page);

  await open.focus();
  await page.keyboard.press('Enter');
  await expect(open).toHaveAttribute('aria-expanded', 'true');
  await expect(page.locator('html')).toHaveClass(/has-modal-open/);
  expect(
    await page
      .locator('html')
      .evaluate((element) => getComputedStyle(element).overflow),
  ).toBe('hidden');
  const dialog = primary.getByRole('dialog', { name: 'Menu' });
  await expect(dialog).toHaveAttribute('aria-modal', 'true');
  const close = dialog.getByRole('button', { name: 'Close menu' });
  await expect(close).toBeVisible();
  const focusables = dialog.locator(
    'a:visible, button:visible, input:visible, select:visible, textarea:visible, [tabindex]:visible:not([tabindex="-1"])',
  );
  expect(await focusables.count()).toBeGreaterThan(1);
  const contentFocusables = dialog
    .locator('.wp-block-navigation__responsive-container-content')
    .locator(
      'a:visible, button:visible, input:visible, select:visible, textarea:visible, [tabindex]:visible:not([tabindex="-1"])',
    );
  expect(await contentFocusables.first().evaluate((element) => element === document.activeElement)).toBe(true);

  await focusables.last().focus();
  await page.keyboard.press('Tab');
  expect(await focusables.first().evaluate((element) => element === document.activeElement)).toBe(
    true,
  );
  await focusables.first().focus();
  await page.keyboard.press('Shift+Tab');
  expect(await focusables.last().evaluate((element) => element === document.activeElement)).toBe(
    true,
  );

  await page.keyboard.press('Escape');
  await expect(open).toHaveAttribute('aria-expanded', 'false');
  await expect(page.locator('html')).not.toHaveClass(/has-modal-open/);
  await assertDocumentScrollUnlocked(page);
  expect(await open.evaluate((element) => element === document.activeElement)).toBe(
    true,
  );

  await page.keyboard.press('Enter');
  await expect(open).toHaveAttribute('aria-expanded', 'true');
  await page.screenshot({
    path: testInfo.outputPath('navigation-overlay-390.png'),
    fullPage: true,
  });
  await dialog.getByRole('link', { name: 'Blog' }).click();
  await page.waitForURL('http://wordpress/blog/');
  await expect(
    primaryNavigation(page).getByRole('button', { name: 'Open menu' }),
  ).toHaveAttribute('aria-expanded', 'false');
  await expect(page.locator('html')).not.toHaveClass(/has-modal-open/);
  await assertDocumentScrollUnlocked(page);
});

async function openTemplatePart(
  page: Page,
  slug: 'header' | 'footer',
): Promise<FrameLocator> {
  const id = `gama-software//${slug}`;
  const frame = await openEditorCanvas(
    page,
    `/wp-admin/site-editor.php?postId=${encodeURIComponent(id)}&postType=wp_template_part&canvas=edit`,
  );
  await expect(
    frame.locator(
      slug === 'header'
        ? '.gama-site-header__surface'
        : '.gama-site-footer__surface',
    ),
  ).toBeVisible();
  return frame;
}

async function openNavigationListView(page: Page): Promise<Locator> {
  const settings = page.getByRole('region', { name: 'Editor settings' });
  await page.getByRole('button', { name: 'Settings' }).click();
  const listViewTab = settings.getByRole('tab', { name: 'List View' });
  await expect(listViewTab).toBeVisible();
  await listViewTab.click();

  const listView = settings
    .getByRole('tabpanel', { name: 'List View' })
    .getByRole('treegrid', { name: 'Block navigation structure' });
  await expect(listView).toBeVisible();
  return listView;
}

async function openNavigationItemOptions(listView: Locator, label: string) {
  const row = listView.getByRole('row', {
    name: new RegExp(`^${label} Options$`),
  });
  await expect(row).toHaveCount(1);
  await row.getByRole('button', { name: 'Options' }).click();
}

async function choosePageLink(page: Page, title: string) {
  const dialog = page.getByRole('dialog', { name: 'Add link' });
  await dialog
    .getByRole('combobox', { name: 'Search or type URL' })
    .fill(title);
  await dialog.getByText(title, { exact: true }).click();
}

async function saveAllShownChanges(
  page: Page,
  expectedEntities: readonly string[],
  testInfo: TestInfo,
) {
  await page.getByRole('button', { name: 'Save', exact: true }).click();
  const dialog = page.getByRole('dialog', {
    name: 'Are you ready to save?',
  });
  await expect(dialog).toBeVisible();
  const checkboxes = dialog.getByRole('checkbox');
  expect(await checkboxes.count()).toBeGreaterThan(0);
  for (const checkbox of await checkboxes.all()) {
    await expect(checkbox).toBeChecked();
  }
  for (const entity of expectedEntities) {
    await expect(dialog.getByRole('checkbox', { name: entity })).toBeChecked();
  }
  await testInfo.attach('core-save-modal.txt', {
    body: await dialog.innerText(),
    contentType: 'text/plain',
  });
  await dialog.getByRole('button', { name: 'Save', exact: true }).click();
  await expect(dialog).toBeHidden({ timeout: 30_000 });
  await expect(
    page.getByRole('button', { name: 'Save', exact: true }),
  ).toBeDisabled({ timeout: 30_000 });
}

async function saveSingleShownChange(page: Page, testInfo: TestInfo) {
  const save = page.getByRole('button', { name: 'Save', exact: true });
  await expect(save).toBeEnabled();
  await expect(
    page.getByRole('dialog', { name: 'Are you ready to save?' }),
  ).toHaveCount(0);
  await save.click();
  const confirmation = page
    .locator('.components-snackbar__content')
    .getByText('Template part updated.', { exact: true });
  await expect(confirmation).toBeVisible({ timeout: 30_000 });
  await expect(save).toBeDisabled({ timeout: 30_000 });
  await testInfo.attach('core-direct-save.txt', {
    body: await confirmation.innerText(),
    contentType: 'text/plain',
  });
}

async function assertDisposableEditorBoundary(page: Page) {
  const currentUser = await rest<any>(page, '/wp/v2/users/me?context=edit');
  expect(currentUser.roles).toEqual(['editor']);
  expect(currentUser.capabilities.edit_theme_options).toBe(true);
  expect(currentUser.capabilities.activate_plugins ?? false).toBe(false);
}

test('lets the disposable Editor transform and save native header navigation through the Site Editor UI @navigation-save', async ({
  page,
}, testInfo) => {
  test.setTimeout(90_000);
  await login(
    page,
    'theme-navigation-editor',
    'navigation-editor-test-only',
  );
  await assertDisposableEditorBoundary(page);
  const frame = await openTemplatePart(page, 'header');
  await frame.getByText('Start', { exact: true }).click();
  await expect(
    frame.locator('[data-type="core/navigation-link"].is-selected'),
  ).toHaveCount(1);
  await page.getByRole('button', { name: 'Link', exact: true }).click();
  await page.getByRole('button', { name: 'Edit link', exact: true }).click();
  const linkDialog = page.getByRole('dialog', { name: 'Add link' });
  await linkDialog.getByRole('textbox', { name: 'Text' }).fill('Początek');
  await linkDialog.getByRole('combobox', { name: 'Link' }).fill('/#welcome');
  await linkDialog.getByRole('button', { name: 'Apply' }).click();
  await expect(frame.getByText('Początek', { exact: true })).toBeVisible();

  const navigationList = await openNavigationListView(page);
  await openNavigationItemOptions(navigationList, 'Usługi');
  await page.getByRole('menuitem', { name: 'Add submenu link' }).click();
  await choosePageLink(page, 'Sample Page');
  await expect(
    navigationList.getByRole('row', {
      name: /^Sample Page Options$/,
    }),
  ).toHaveCount(1);

  await openNavigationItemOptions(navigationList, 'Blog');
  await page.getByRole('menuitem', { name: 'Add after' }).click();
  await choosePageLink(page, 'Sample Page');
  await page.getByRole('textbox', { name: 'Text' }).fill('Oferta');
  await expect(frame.getByText('Oferta', { exact: true })).toBeVisible();

  await page
    .getByRole('button', { name: 'Select parent block: Navigation' })
    .click();
  await expect(
    navigationList.getByRole('row', { name: /^Oferta Options$/ }),
  ).toHaveCount(1);
  await openNavigationItemOptions(navigationList, 'Kontakt');
  await page.getByRole('menuitem', { name: 'Remove Kontakt' }).click();
  await expect(
    navigationList.getByRole('row', { name: /^Kontakt Options$/ }),
  ).toHaveCount(0);
  for (let index = 0; index < 2; index += 1) {
    await openNavigationItemOptions(navigationList, 'Moduły');
    await page.getByRole('menuitem', { name: 'Move up' }).click();
  }

  await saveAllShownChanges(page, ['Header', 'Menu'], testInfo);

  const header = await rest<any>(
    page,
    '/wp/v2/template-parts/gama-software//header?context=edit',
  );
  expect(header.source).toBe('custom');
  expect(header.has_theme_file).toBe(true);
  let navigationContent = header.content.raw as string;
  const navigationRef = navigationContent.match(/"ref":(\d+)/)?.[1];
  if (navigationRef !== undefined) {
    const navigation = await rest<any>(
      page,
      `/wp/v2/navigation/${navigationRef}?context=edit`,
    );
    expect(navigation.status).toBe('publish');
    navigationContent = navigation.content.raw;
  }
  for (const text of ['Początek', 'Sample Page', 'Oferta']) {
    expect(navigationContent).toContain(`"label":"${text}"`);
  }
  expect(navigationContent).toContain('"url":"/#welcome"');
  expect(navigationContent).toContain('wp:navigation-submenu');
  expect(navigationContent).not.toContain('"label":"Kontakt"');
  for (const [earlierLabel, laterLabel] of [
    ['Moduły', 'Początek'],
    ['Początek', 'Usługi'],
    ['Usługi', 'Blog'],
    ['Blog', 'Oferta'],
  ]) {
    expect(
      navigationContent.indexOf(`"label":"${earlierLabel}"`),
    ).toBeLessThan(
      navigationContent.indexOf(`"label":"${laterLabel}"`),
    );
  }
});

test('lets the disposable Editor change and save the native footer copyright through the Site Editor UI @navigation-save', async ({
  page,
}, testInfo) => {
  await login(
    page,
    'theme-navigation-editor',
    'navigation-editor-test-only',
  );
  await assertDisposableEditorBoundary(page);
  const frame = await openTemplatePart(page, 'footer');
  await frame
    .getByText('© 2026 Gama Software. Wszystkie prawa zastrzeżone.', {
      exact: true,
    })
    .click();
  const copyright = frame.locator(
    '[data-type="core/paragraph"].is-selected[contenteditable="true"], [data-type="core/paragraph"].is-selected [contenteditable="true"]',
  );
  await expect(copyright).toHaveCount(1);
  await copyright.fill('© 2026 Gama Software. Test redaktora.');
  await expect(
    frame.getByText('© 2026 Gama Software. Test redaktora.', { exact: true }),
  ).toBeVisible();

  await saveSingleShownChange(page, testInfo);

  const footer = await rest<any>(
    page,
    '/wp/v2/template-parts/gama-software//footer?context=edit',
  );
  expect(footer.source).toBe('custom');
  expect(footer.has_theme_file).toBe(true);
  expect(footer.content.raw).toContain(
    '© 2026 Gama Software. Test redaktora.',
  );
});

test('keeps saved navigation and copyright public on every route after lifecycle boundaries @navigation-persisted', async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  for (const [route, marker, expectedStatus] of publicRoutes) {
    const response = await page.goto(route);
    expect(response?.status()).toBe(expectedStatus);
    await expect(page.locator(`main.gama-template--${marker}`)).toHaveCount(1);
    await assertLandmarksAndLogo(page);
    const primary = primaryNavigation(page);
    await expect(primary.getByText('Początek', { exact: true })).toBeVisible();
    await expect(primary.getByText('Moduły', { exact: true })).toBeVisible();
    await expect(primary.getByText('Usługi', { exact: true })).toBeVisible();
    const submenu = primary.getByRole('button', { name: 'Usługi submenu' });
    await expect(submenu).toHaveAttribute('aria-expanded', 'false');
    await submenu.click();
    await expect(submenu).toHaveAttribute('aria-expanded', 'true');
    await expect(
      primary.getByRole('link', { name: 'Sample Page' }),
    ).toHaveAttribute('href', 'http://wordpress/sample-page/');
    await expect(primary.getByRole('link', { name: 'Oferta' })).toHaveAttribute(
      'href',
      'http://wordpress/sample-page/',
    );
    await expect(
      primary.getByRole('link', { name: 'Kontakt' }),
    ).toHaveCount(0);
    await expect(
      page.getByText('© 2026 Gama Software. Test redaktora.', {
        exact: true,
      }),
    ).toBeVisible();
  }

  for (const width of persistedMobileWidths) {
    await assertPersistedMobileNavigation(page, width);
  }

  await login(page);
  const header = await rest<any>(
    page,
    '/wp/v2/template-parts/gama-software//header?context=edit',
  );
  const footer = await rest<any>(
    page,
    '/wp/v2/template-parts/gama-software//footer?context=edit',
  );
  for (const entity of [header, footer]) {
    expect(entity.source).toBe('custom');
    expect(entity.status).toBe('publish');
    expect(entity.has_theme_file).toBe(true);
  }
  const navigationFixtureAttributes = {
    ariaLabel: 'Fixture navigation',
    style: { spacing: { blockGap: '1rem' } },
  };
  // The self-closing Navigation fixture covers ref-backed serialization.
  expect(
    extractNavigationBlockAttributes(
      '<!-- wp:navigation {"ariaLabel":"Fixture navigation","style":{"spacing":{"blockGap":"1rem"}}} /-->',
    ),
  ).toEqual(navigationFixtureAttributes);
  // The inline-inner-block Navigation fixture covers legal nested serialization.
  expect(
    extractNavigationBlockAttributes(
      '<!-- wp:navigation {"ariaLabel":"Fixture navigation","style":{"spacing":{"blockGap":"1rem"}}} --><!-- wp:navigation-link {"label":"Start","url":"/"} /--><!-- /wp:navigation -->',
    ),
  ).toEqual(navigationFixtureAttributes);

  const storedNavigationAttributes = extractNavigationBlockAttributes(
    header.content.raw as string,
  );
  expect(storedNavigationAttributes).toBeDefined();
  if (storedNavigationAttributes === undefined) {
    throw new Error('Saved header lost serialized Core Navigation attributes.');
  }
  const navigationBlockType = await rest<any>(
    page,
    '/wp/v2/block-types/core/navigation?context=edit',
  );
  expect(
    storedNavigationAttributes.overlayMenu ??
      navigationBlockType.attributes.overlayMenu.default,
  ).toBe('mobile');
  expect(storedNavigationAttributes.ariaLabel).toBe('Główna nawigacja');
  expect(storedNavigationAttributes.className).toBe(
    'gama-primary-navigation',
  );
  let navigationContent = header.content.raw as string;
  const navigationRef = navigationContent.match(/"ref":(\d+)/)?.[1];
  if (navigationRef !== undefined) {
    const navigation = await rest<any>(
      page,
      `/wp/v2/navigation/${navigationRef}?context=edit`,
    );
    expect(navigation.status).toBe('publish');
    navigationContent = navigation.content.raw;
  }
  expect(navigationContent).toContain('"label":"Początek"');
  expect(navigationContent).toContain('"label":"Sample Page"');
  expect(navigationContent).toContain('"label":"Oferta"');
  expect(footer.content.raw).toContain('Test redaktora');
});
