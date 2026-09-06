import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import test from 'node:test';

const runner = fileURLToPath(new URL('./runner.mjs', import.meta.url));

function metric(name, value) {
  return {
    name,
    value,
    unit: name === 'CLS' ? 'score' : 'ms',
    valid: true,
    reported: true,
    id: `v5-${name.toLowerCase()}`,
  };
}

function sample(overrides = {}) {
  return {
    formatVersion: 1,
    target: 'baseline',
    route: 'home',
    viewport: { name: 'desktop', width: 1440, height: 900 },
    sample: 1,
    order: 1,
    startedAt: '2026-09-06T13:48:45.000Z',
    completedAt: '2026-09-06T13:48:46.000Z',
    sourceRevision: 'c26e19699c7a66a15e0854cf3bb4fce342bf2e2c',
    browserImage: `sha256:${'a'.repeat(64)}`,
    serverImage: `sha256:${'b'.repeat(64)}`,
    buildImage: `sha256:${'c'.repeat(64)}`,
    browser: {
      name: 'chromium',
      version: '151.0.7922.34',
      node: '24.18.1',
      architecture: 'arm64',
    },
    conditions: {
      network: 'unthrottled',
      cache: 'fresh-context',
      reducedMotion: 'reduce',
    },
    support: {
      secureContext: true,
      performanceObserver: true,
      largestContentfulPaint: true,
      layoutShift: true,
      event: true,
    },
    interactions: {
      trustedClicks: 1,
      trustedKeydowns: 2,
      trustedInputs: 1,
      total: 4,
    },
    finalization: {
      mechanism: 'same-origin-navigation',
      visibilityHidden: true,
      pagehide: true,
      recoveredMetrics: ['LCP', 'CLS', 'INP'],
      callbacksAfterLifecycle: [],
    },
    bindingMetrics: ['LCP', 'CLS', 'INP'],
    bindingEvents: ['LCP', 'CLS', 'INP'].map((name) => ({ kind: 'metric', metric: { name } })),
    recoveredEvents: ['LCP', 'CLS', 'INP'].map((name) => ({ kind: 'metric', metric: { name } })),
    metrics: {
      LCP: metric('LCP', 1000),
      CLS: metric('CLS', 0),
      INP: metric('INP', 0),
    },
    httpFailures: [],
    consoleFailures: [],
    ...overrides,
  };
}

function run(args) {
  return spawnSync(process.execPath, [runner, ...args], {
    encoding: 'utf8',
  });
}

test('validator rejects a missing INP instead of fabricating zero', () => {
  const fixture = mkdtempSync(join(tmpdir(), 'gama-vitals-test.'));
  try {
    const input = join(fixture, 'missing-inp.json');
    const invalid = sample();
    delete invalid.metrics.INP;
    writeFileSync(input, JSON.stringify({ samples: [invalid] }));

    const result = run(['validate', input]);

    assert.equal(result.status, 2);
    assert.match(result.stderr, /sample baseline\/home\/desktop\/1: INP is missing/);
  } finally {
    rmSync(fixture, { recursive: true, force: true });
  }
});

test('validator accepts genuinely reported CLS and INP zero values', () => {
  const fixture = mkdtempSync(join(tmpdir(), 'gama-vitals-test.'));
  try {
    const input = join(fixture, 'reported-zero.json');
    writeFileSync(input, JSON.stringify({ samples: [sample()] }));

    const result = run(['validate', input]);

    assert.equal(result.status, 0, result.stderr);
    assert.match(result.stdout, /Validated 1 sample/);
  } finally {
    rmSync(fixture, { recursive: true, force: true });
  }
});

test('validator rejects missing or inverted sample collection timestamps', () => {
  const fixture = mkdtempSync(join(tmpdir(), 'gama-vitals-test.'));
  try {
    const missingInput = join(fixture, 'missing-time.json');
    const invertedInput = join(fixture, 'inverted-time.json');
    const missing = sample();
    delete missing.startedAt;
    writeFileSync(missingInput, JSON.stringify({ samples: [missing] }));
    writeFileSync(
      invertedInput,
      JSON.stringify({
        samples: [
          sample({
            startedAt: '2026-09-06T13:48:47.000Z',
            completedAt: '2026-09-06T13:48:46.000Z',
          }),
        ],
      }),
    );

    const missingResult = run(['validate', missingInput]);
    const invertedResult = run(['validate', invertedInput]);

    assert.equal(missingResult.status, 2);
    assert.match(missingResult.stderr, /startedAt must be an ISO timestamp/);
    assert.equal(invertedResult.status, 2);
    assert.match(invertedResult.stderr, /completedAt must not precede startedAt/);
  } finally {
    rmSync(fixture, { recursive: true, force: true });
  }
});

test('merged collection span uses explicit phase start and completion', () => {
  const fixture = mkdtempSync(join(tmpdir(), 'gama-vitals-test.'));
  try {
    const home = join(fixture, 'home.json');
    const wordpressOnly = join(fixture, 'wordpress-only.json');
    const output = join(fixture, 'merged.json');
    const homeStartedAt = '2026-09-06T13:48:40.000Z';
    const homeCompletedAt = '2026-09-06T13:49:03.000Z';
    const wordpressStartedAt = '2026-09-06T13:49:04.000Z';
    const wordpressCompletedAt = '2026-09-06T13:49:16.000Z';
    writeFileSync(
      home,
      JSON.stringify({
        startedAt: homeStartedAt,
        completedAt: homeCompletedAt,
        samples: Array.from({ length: 20 }, (_, index) =>
          sample({
            sample: index + 1,
            order: index + 1,
            startedAt: new Date(Date.parse(homeStartedAt) + index * 500).toISOString(),
            completedAt: new Date(Date.parse(homeStartedAt) + index * 500 + 250).toISOString(),
          }),
        ),
      }),
    );
    writeFileSync(
      wordpressOnly,
      JSON.stringify({
        startedAt: wordpressStartedAt,
        completedAt: wordpressCompletedAt,
        samples: Array.from({ length: 20 }, (_, index) =>
          sample({
            sample: index + 21,
            order: index + 21,
            startedAt: new Date(Date.parse(wordpressStartedAt) + index * 500).toISOString(),
            completedAt: new Date(
              Date.parse(wordpressStartedAt) + index * 500 + 250,
            ).toISOString(),
          }),
        ),
      }),
    );

    const result = run(['merge', home, wordpressOnly, output]);

    assert.equal(result.status, 0, result.stderr);
    const merged = JSON.parse(readFileSync(output, 'utf8'));
    assert.equal(merged.startedAt, homeStartedAt);
    assert.equal(merged.completedAt, wordpressCompletedAt);
    assert.deepEqual(merged.phases, [
      { name: 'home', startedAt: homeStartedAt, completedAt: homeCompletedAt },
      {
        name: 'wordpress-only',
        startedAt: wordpressStartedAt,
        completedAt: wordpressCompletedAt,
      },
    ]);
  } finally {
    rmSync(fixture, { recursive: true, force: true });
  }
});

test('validator rejects sample timing that overlaps the prior sequential sample', () => {
  const fixture = mkdtempSync(join(tmpdir(), 'gama-vitals-test.'));
  try {
    const input = join(fixture, 'overlap.json');
    writeFileSync(
      input,
      JSON.stringify({
        samples: [
          sample(),
          sample({
            sample: 2,
            order: 2,
            startedAt: '2026-09-06T13:48:45.500Z',
            completedAt: '2026-09-06T13:48:46.500Z',
          }),
        ],
      }),
    );

    const result = run(['validate', input]);

    assert.equal(result.status, 2);
    assert.match(result.stderr, /sample order 2 must not start before order 1 completed/);
  } finally {
    rmSync(fixture, { recursive: true, force: true });
  }
});

test('validator requires target-specific immutable image provenance', () => {
  const fixture = mkdtempSync(join(tmpdir(), 'gama-vitals-test.'));
  try {
    const baselineInput = join(fixture, 'baseline.json');
    const wordpressInput = join(fixture, 'wordpress.json');
    const baseline = sample();
    delete baseline.buildImage;
    const wordpress = sample({
      target: 'wordpress',
      sourceRevision: 'c631efbff87dfdb33888e431feac91b3572c4e9f',
    });
    delete wordpress.buildImage;
    writeFileSync(baselineInput, JSON.stringify({ samples: [baseline] }));
    writeFileSync(wordpressInput, JSON.stringify({ samples: [wordpress] }));

    const baselineResult = run(['validate', baselineInput]);
    const wordpressResult = run(['validate', wordpressInput]);

    assert.equal(baselineResult.status, 2);
    assert.match(baselineResult.stderr, /buildImage must be an immutable image ID/);
    assert.equal(wordpressResult.status, 2);
    assert.match(wordpressResult.stderr, /candidateImage must be an immutable image ID/);
  } finally {
    rmSync(fixture, { recursive: true, force: true });
  }
});

test('report calculation records hand-derived median and min/max', () => {
  const fixture = mkdtempSync(join(tmpdir(), 'gama-vitals-test.'));
  try {
    const input = join(fixture, 'raw.json');
    const output = join(fixture, 'summary.json');
    const lcp = [900, 1100, 1000, 1300, 950];
    const cls = [0, 0.01, 0.02, 0.03, 0.04];
    const inp = [24, 40, 32, 48, 16];
    writeFileSync(
      input,
      JSON.stringify({
        samples: lcp.map((value, index) =>
          sample({
            sample: index + 1,
            order: index + 1,
            startedAt: new Date(Date.parse('2026-09-06T13:48:45.000Z') + index * 2_000).toISOString(),
            completedAt: new Date(
              Date.parse('2026-09-06T13:48:45.000Z') + index * 2_000 + 1_000,
            ).toISOString(),
            metrics: {
              LCP: metric('LCP', value),
              CLS: metric('CLS', cls[index]),
              INP: metric('INP', inp[index]),
            },
          }),
        ),
      }),
    );

    const result = run(['summarize', input, output]);

    assert.equal(result.status, 0, result.stderr);
    const summary = JSON.parse(readFileSync(output, 'utf8'));
    assert.deepEqual(summary.groups[0].metrics, {
      LCP: { unit: 'ms', median: 1000, min: 900, max: 1300 },
      CLS: { unit: 'score', median: 0.02, min: 0, max: 0.04 },
      INP: { unit: 'ms', median: 32, min: 16, max: 48 },
    });
    assert.equal(summary.groups[0].sampleCount, 5);
    assert.equal(summary.groups[0].interactionCount, 20);
  } finally {
    rmSync(fixture, { recursive: true, force: true });
  }
});
