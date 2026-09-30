'use strict';

import { chromium, request, webkit } from '@playwright/test';

const mode = process.argv.at(2);
const supportedModes = new Set([
  'reject-untrusted',
  'reject-wrong-hostname',
  'accept-valid',
]);
if (!supportedModes.has(mode)) {
  console.error(`Unsupported TLS probe mode: ${mode ?? '(missing)'}`);
  process.exitCode = 64;
}

const targetUrl = process.env.WP_BASE_URL;
const certificateFailurePattern =
  /ERR_CERT_|certificate|SSL_ERROR|TLS certificate|TLS handshake/i;
const transportFailurePattern =
  /ERR_NAME_NOT_RESOLVED|ERR_CONNECTION_REFUSED|ENOTFOUND|EAI_AGAIN|timed out|Timeout/i;

function publicError(error) {
  return error instanceof Error ? error.message : String(error);
}

function ensure(condition, message) {
  if (!condition) throw new Error(message);
}

function assertCertificateFailure(error, engine) {
  const message = publicError(error);
  ensure(
    !transportFailurePattern.test(message),
    `${engine} failed at DNS/connectivity instead of certificate verification: ${message}`,
  );
  ensure(
    certificateFailurePattern.test(message),
    `${engine} did not report a certificate-specific failure: ${message}`,
  );
  return message.split('\n').at(0);
}

async function expectCertificateRejection(browserType, engine) {
  const browser = await browserType.launch();
  try {
    const page = await browser.newPage();
    let navigationError;
    try {
      await page.goto(targetUrl, {
        timeout: 15_000,
        waitUntil: 'domcontentloaded',
      });
    } catch (error) {
      navigationError = error;
    }
    ensure(
      navigationError !== undefined,
      `${engine} unexpectedly accepted ${mode} at ${targetUrl}`,
    );
    return {
      engine,
      result: 'rejected',
      error: assertCertificateFailure(navigationError, engine),
    };
  } finally {
    await browser.close();
  }
}

async function expectValidHttps(browserType, engine) {
  const browser = await browserType.launch();
  try {
    const page = await browser.newPage();
    const requestedUrls = [];
    page.on('request', (browserRequest) =>
      requestedUrls.push(browserRequest.url()),
    );
    const response = await page.goto(targetUrl, {
      timeout: 15_000,
      waitUntil: 'networkidle',
    });
    ensure(response?.status() === 200, `${engine} HTTPS status was not 200`);
    ensure(
      (await page.getByRole('heading', { level: 1 }).textContent()) ===
        'Gama Software',
      `${engine} did not render the expected heading`,
    );
    const insecureRequests = requestedUrls.filter((url) =>
      /^http:\/\//i.test(url),
    );
    ensure(
      insecureRequests.length === 0,
      `${engine} issued mixed-content HTTP requests`,
    );
    return {
      engine,
      result: 'accepted',
      status: response.status(),
      requestCount: requestedUrls.length,
      insecureRequests,
    };
  } finally {
    await browser.close();
  }
}

async function expectValidRequestContext() {
  const context = await request.newContext({ baseURL: targetUrl });
  try {
    const response = await context.get('/');
    ensure(
      response.status() === 200,
      'request-context HTTPS status was not 200',
    );
    return { result: 'accepted', status: response.status() };
  } finally {
    await context.dispose();
  }
}

async function main() {
  ensure(targetUrl !== undefined, 'TLS probe requires WP_BASE_URL.');
  const engines = [
    ['chromium', chromium],
    ['webkit', webkit],
  ];
  const results = [];
  for (const [engine, browserType] of engines) {
    results.push(
      mode === 'accept-valid'
        ? await expectValidHttps(browserType, engine)
        : await expectCertificateRejection(browserType, engine),
    );
  }
  const requestContext =
    mode === 'accept-valid' ? await expectValidRequestContext() : undefined;
  const evidence = {
    mode,
    target: new URL(targetUrl).hostname,
    engines: results,
    ...(requestContext === undefined ? {} : { requestContext }),
  };
  console.log(JSON.stringify(evidence, null, 2));
}

if (supportedModes.has(mode)) {
  main().catch((error) => {
    console.error(publicError(error));
    process.exitCode = 1;
  });
}
