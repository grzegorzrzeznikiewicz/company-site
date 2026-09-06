import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, join } from 'node:path';
import { chromium } from '@playwright/test';

import { validateSample } from './schema.mjs';

const require = createRequire(import.meta.url);
const webVitalsDist = dirname(require.resolve('web-vitals'));
const webVitalsSource = readFileSync(join(webVitalsDist, 'web-vitals.iife.js'), 'utf8');

const bootstrapSource = `
(() => {
  const documentHref = location.href;
  const state = {
    support: {
      secureContext: globalThis.isSecureContext,
      performanceObserver: 'PerformanceObserver' in globalThis,
      largestContentfulPaint: PerformanceObserver.supportedEntryTypes?.includes('largest-contentful-paint') === true,
      layoutShift: PerformanceObserver.supportedEntryTypes?.includes('layout-shift') === true,
      event: PerformanceObserver.supportedEntryTypes?.includes('event') === true,
    },
    interactions: { trustedClicks: 0, trustedKeydowns: 0, trustedInputs: 0, total: 0 },
    lifecycle: { visibilityHidden: false, pagehide: false },
    sequence: 0,
  };
  const emit = (event) => {
    const payload = {
      ...event,
      sequence: ++state.sequence,
      support: { ...state.support },
      interactions: { ...state.interactions },
      lifecycle: { ...state.lifecycle },
      href: documentHref,
      timestamp: performance.now(),
    };
    let persisted = [];
    try {
      persisted = JSON.parse(sessionStorage.getItem('__GAMA_VITALS__') ?? '[]');
    } catch {}
    persisted.push(payload);
    try {
      sessionStorage.setItem('__GAMA_VITALS__', JSON.stringify(persisted));
    } catch {}
    globalThis.__gamaVitalsBinding(payload).catch(() => {});
  };
  const count = (field) => (event) => {
    if (event.isTrusted) {
      state.interactions[field] += 1;
      state.interactions.total += 1;
      emit({ kind: 'interaction', name: field });
    }
  };
  addEventListener('click', count('trustedClicks'), true);
  addEventListener('keydown', count('trustedKeydowns'), true);
  addEventListener('input', count('trustedInputs'), true);
  addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') state.lifecycle.visibilityHidden = true;
    emit({ kind: 'lifecycle', name: 'visibilitychange', value: document.visibilityState });
  });
  addEventListener('pagehide', () => {
    state.lifecycle.pagehide = true;
    emit({ kind: 'lifecycle', name: 'pagehide', value: true });
  });
  const report = (metric) => emit({
    kind: 'metric',
    metric: {
      name: metric.name,
      value: metric.value,
      delta: metric.delta,
      id: metric.id,
      rating: metric.rating,
      navigationType: metric.navigationType,
      entryCount: metric.entries.length,
    },
  });
  emit({ kind: 'support' });
  webVitals.onLCP(report, { reportAllChanges: true });
  webVitals.onCLS(report, { reportAllChanges: true });
  webVitals.onINP(report, { reportAllChanges: true, durationThreshold: 0 });
})();
`;

function metricRecord(name, event) {
  if (!event) return undefined;
  return {
    ...event.metric,
    unit: name === 'CLS' ? 'score' : 'ms',
    reported: true,
    valid: Number.isFinite(event.metric.value) && event.metric.value >= 0,
    reportedAt: event.timestamp,
  };
}

export async function launchChromium() {
  return chromium.launch({ headless: true });
}

export async function collectPage({
  browser,
  target,
  route,
  url,
  viewport,
  sample,
  order,
  sourceRevision,
  browserImage,
  serverImage,
  buildImage,
  candidateImage,
  server,
  journey,
  finalizeUrl = new URL('/__gama-vitals-finalize.html', url).href,
}) {
  const events = [];
  const httpFailures = [];
  const consoleFailures = [];
  const context = await browser.newContext({
    viewport: { width: viewport.width, height: viewport.height },
    reducedMotion: 'reduce',
    serviceWorkers: 'block',
  });
  await context.exposeBinding('__gamaVitalsBinding', (_source, event) => {
    events.push(event);
  });
  await context.addInitScript({ content: `${webVitalsSource}\n${bootstrapSource}` });
  const page = await context.newPage();
  let collectingDiagnostics = true;
  page.on('console', (message) => {
    if (collectingDiagnostics && message.type() === 'error') {
      consoleFailures.push(`console: ${message.text()}`);
    }
  });
  page.on('pageerror', (error) => {
    if (collectingDiagnostics) consoleFailures.push(`pageerror: ${error.message}`);
  });
  page.on('requestfailed', (request) => {
    if (collectingDiagnostics) {
      httpFailures.push(`requestfailed: ${request.url()} ${request.failure()?.errorText ?? ''}`);
    }
  });
  page.on('response', (response) => {
    if (collectingDiagnostics && response.status() >= 400) {
      httpFailures.push(`http ${response.status()}: ${response.url()}`);
    }
  });

  let journeyEvidence = {};
  try {
    await page.goto(url, { waitUntil: 'load' });
    await page.waitForTimeout(350);
    journeyEvidence = journey ? await journey(page) : {};
    if (journey) {
      await page.waitForFunction(
        () =>
          JSON.parse(sessionStorage.getItem('__GAMA_VITALS__') ?? '[]').some(
            (event) => event.kind === 'metric' && event.metric.name === 'INP',
          ),
        undefined,
        { timeout: 2_000 },
      );
    }
    collectingDiagnostics = false;
    await page.goto(finalizeUrl, { waitUntil: 'load' });
    const persistedEvents = await page.evaluate(() => {
      try {
        return JSON.parse(sessionStorage.getItem('__GAMA_VITALS__') ?? '[]');
      } catch {
        return [];
      }
    });
    for (const event of persistedEvents) {
      if (
        !events.some(
          (candidate) => candidate.href === event.href && candidate.sequence === event.sequence,
        )
      ) {
        events.push(event);
      }
    }
  } catch (error) {
    error.collectorEvents = events;
    throw error;
  } finally {
    await context.close();
  }

  const targetEvents = events.filter((event) => event.href === url);
  const supportEvent = targetEvents.find((event) => event.kind === 'support');
  const lifecycleEvents = targetEvents.filter((event) => event.kind === 'lifecycle');
  const firstLifecycleIndex = targetEvents.findIndex((event) => event.kind === 'lifecycle');
  const metricEvents = Object.fromEntries(
    ['LCP', 'CLS', 'INP'].map((name) => [
      name,
      targetEvents.filter((event) => event.kind === 'metric' && event.metric.name === name).at(-1),
    ]),
  );
  const latestState = [...targetEvents].reverse().find((event) => event.interactions);
  const callbacksAfterLifecycle = ['LCP', 'CLS', 'INP'].filter((name) => {
    const index = targetEvents.lastIndexOf(metricEvents[name]);
    return firstLifecycleIndex >= 0 && index > firstLifecycleIndex;
  });
  const retainedMetrics = ['LCP', 'CLS', 'INP'].filter((name) => metricEvents[name]);
  const result = {
    formatVersion: 1,
    target,
    route,
    url,
    viewport,
    sample,
    order,
    sourceRevision,
    browserImage,
    serverImage,
    ...(buildImage ? { buildImage } : {}),
    ...(candidateImage ? { candidateImage } : {}),
    server,
    ...journeyEvidence,
    browser: {
      name: 'chromium',
      version: browser.version(),
      node: process.version.replace(/^v/, ''),
      architecture: process.arch,
    },
    conditions: {
      network: 'unthrottled',
      cache: 'fresh-context',
      reducedMotion: 'reduce',
    },
    support: supportEvent?.support ?? {},
    interactions: latestState?.interactions ?? {
      trustedClicks: 0,
      trustedKeydowns: 0,
      trustedInputs: 0,
      total: 0,
    },
    finalization: {
      mechanism: 'same-origin-navigation',
      visibilityHidden: lifecycleEvents.some(
        (event) => event.name === 'visibilitychange' && event.value === 'hidden',
      ),
      pagehide: lifecycleEvents.some((event) => event.name === 'pagehide'),
      retainedMetrics,
      callbacksAfterLifecycle,
    },
    metrics: Object.fromEntries(
      Object.entries(metricEvents)
        .map(([name, event]) => [name, metricRecord(name, event)])
        .filter(([, metric]) => metric !== undefined),
    ),
    collectorEvents: events,
    httpFailures,
    consoleFailures,
  };
  return result;
}

export function collectionResult(sample) {
  const errors = validateSample(sample);
  return { ...sample, valid: errors.length === 0, errors };
}
