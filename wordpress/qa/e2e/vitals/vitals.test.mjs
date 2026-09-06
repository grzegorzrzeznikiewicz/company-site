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
      retainedMetrics: ['LCP', 'CLS', 'INP'],
      callbacksAfterLifecycle: [],
    },
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
