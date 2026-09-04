import { expect, type FrameLocator, type Page } from '@playwright/test';

const knownWelcomeGuideUsers = new Set<string>();
const loggedInUserByPage = new WeakMap<Page, string>();

export type BrowserDiagnostics = {
  browserErrors: string[];
  externalFontRequests: string[];
};

type DiagnosticsOptions = {
  allowRestrictedSettingsResponse?: boolean;
  expectedMissingPaths?: string[];
};

export async function login(
  page: Page,
  user = process.env.WP_ADMIN_USER ?? 'theme-admin',
  password = process.env.WP_ADMIN_PASSWORD ?? 'theme-test-password-only',
): Promise<void> {
  await page.context().clearCookies();
  await page.goto('/wp-login.php', { waitUntil: 'domcontentloaded' });
  await page.waitForLoadState('load');
  const usernameField = page.locator('#user_login');
  const passwordField = page.locator('#user_pass');
  await expect(usernameField).toBeFocused();
  await passwordField.fill(password);
  await usernameField.fill(user);
  const usernameMatchesExpectedValue = await usernameField.evaluate(
    (element, expected) => (element as HTMLInputElement).value === expected,
    user,
  );
  const passwordMatchesExpectedValue = await passwordField.evaluate(
    (element, expected) => (element as HTMLInputElement).value === expected,
    password,
  );
  expect(usernameMatchesExpectedValue).toBe(true);
  expect(passwordMatchesExpectedValue).toBe(true);
  await Promise.all([
    page.waitForURL(/\/wp-admin\//, {
      waitUntil: 'domcontentloaded',
      timeout: 45_000,
    }),
    page.locator('#wp-submit').click(),
  ]);
  await page.waitForLoadState('domcontentloaded', { timeout: 45_000 });
  loggedInUserByPage.set(page, user);
}

export async function rest<T>(
  page: Page,
  route: string,
  method = 'GET',
  body?: unknown,
): Promise<T> {
  return page.evaluate(
    async ({ route, method, body }) => {
      const nonce = await fetch('/wp-admin/admin-ajax.php?action=rest-nonce', {
        credentials: 'same-origin',
      }).then((response) => response.text());
      const [restPath, restQuery] = route.split('?', 2);
      const response = await fetch(
        `/index.php?rest_route=${restPath}${restQuery ? `&${restQuery}` : ''}`,
        {
          method,
          credentials: 'same-origin',
          headers: { 'Content-Type': 'application/json', 'X-WP-Nonce': nonce },
          body: body === undefined ? undefined : JSON.stringify(body),
        },
      );
      if (!response.ok) {
        throw new Error(
          `${method} ${route}: ${response.status} ${await response.text()}`,
        );
      }
      return response.json();
    },
    { route, method, body },
  ) as Promise<T>;
}

export async function openEditorCanvas(
  page: Page,
  route: string,
): Promise<FrameLocator> {
  await page.goto(route, { waitUntil: 'domcontentloaded' });
  return waitForEditorCanvas(page);
}

export async function waitForEditorCanvas(page: Page): Promise<FrameLocator> {
  const canvas = page.locator('iframe[name="editor-canvas"]');
  const visibleCanvas = page.locator('iframe[name="editor-canvas"]:visible');
  const welcome = page.getByRole('dialog', {
    name: /Welcome to the (?:site )?editor/i,
  });
  await expect(visibleCanvas.or(welcome).first()).toBeVisible({
    timeout: 60_000,
  });
  const loggedInUser = loggedInUserByPage.get(page);
  const shouldCheckWelcome =
    loggedInUser === undefined || !knownWelcomeGuideUsers.has(loggedInUser);
  if (shouldCheckWelcome && (await welcome.isVisible())) {
    const dismiss = welcome.getByRole('button', {
      name: /^(?:Get started|Close)$/,
    });
    await dismiss.click();
    await expect(welcome).toBeHidden();
  }
  if (loggedInUser !== undefined) {
    knownWelcomeGuideUsers.add(loggedInUser);
  }
  await expect(canvas).toBeVisible({ timeout: 60_000 });

  const frame = page.frameLocator('iframe[name="editor-canvas"]');
  await expect(frame.locator('body')).toBeVisible({ timeout: 60_000 });
  return frame;
}

export function watchWordPressDiagnostics(
  page: Page,
  options: DiagnosticsOptions = {},
): BrowserDiagnostics {
  const diagnostics: BrowserDiagnostics = {
    browserErrors: [],
    externalFontRequests: [],
  };
  page.on('console', (message) => {
    const location = message.location().url;
    let locationPath = '';
    try {
      locationPath = location === '' ? '' : new URL(location).pathname;
    } catch {
      locationPath = '';
    }
    const expectedRestrictedSettingsResponse =
      options.allowRestrictedSettingsResponse === true &&
      message.type() === 'error' &&
      message.text().includes('403 (Forbidden)') &&
      locationPath === '/wp-json/wp/v2/settings';
    const expectedMissingRoute =
      message.type() === 'error' &&
      message.text().includes('404 (Not Found)') &&
      (options.expectedMissingPaths ?? []).includes(locationPath);
    if (
      message.type() === 'error' &&
      !expectedRestrictedSettingsResponse &&
      !expectedMissingRoute &&
      !message
        .text()
        .includes('Failed to load resource: net::ERR_NAME_NOT_RESOLVED')
    ) {
      diagnostics.browserErrors.push(
        `console: ${message.text()}${location ? ` at ${location}` : ''}`,
      );
    }
  });
  page.on('pageerror', (error) =>
    diagnostics.browserErrors.push(`pageerror: ${error.message}`),
  );
  page.on('requestfailed', (request) => {
    const hostname = new URL(request.url()).hostname;
    if (
      !['secure.gravatar.com', 's.w.org'].includes(hostname) &&
      request.failure()?.errorText !== 'net::ERR_ABORTED'
    ) {
      diagnostics.browserErrors.push(
        `requestfailed: ${request.url()} ${request.failure()?.errorText ?? ''}`,
      );
    }
  });
  page.on('request', (request) => {
    const url = new URL(request.url());
    if (request.resourceType() === 'font' && url.hostname !== 'wordpress') {
      diagnostics.externalFontRequests.push(request.url());
    }
  });
  return diagnostics;
}

export function assertDiagnosticsClean(
  diagnostics: BrowserDiagnostics,
): void {
  expect(
    diagnostics.browserErrors,
    diagnostics.browserErrors.join('\n'),
  ).toEqual([]);
  expect(
    diagnostics.externalFontRequests,
    'Remote font requests are forbidden.',
  ).toEqual([]);
}
