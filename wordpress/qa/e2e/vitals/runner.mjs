#!/usr/bin/env node
import { existsSync, readFileSync, statSync, writeFileSync } from 'node:fs';
import { isAbsolute } from 'node:path';
import { collectPage, collectionResult, launchChromium } from './collector.mjs';
import { summarize, validateDocument } from './schema.mjs';
import { startStaticServer } from './fixture-server.mjs';
import { performContactJourney, performReadingJourney } from './journeys.mjs';

function readJson(path) {
  return JSON.parse(readFileSync(path, 'utf8'));
}

const [command, input, output, extra] = process.argv.slice(2);

function measurementPlan() {
  const viewports = [
    { name: 'desktop', width: 1440, height: 900 },
    { name: 'phone', width: 390, height: 844 },
  ];
  const plan = [];
  let order = 0;
  for (const viewport of viewports) {
    for (let sample = 1; sample <= 5; sample += 1) {
      for (const target of ['baseline', 'wordpress']) {
        plan.push({ target, route: 'home', viewport, sample, order: ++order });
      }
    }
  }
  for (const route of ['blog-archive', 'representative-article']) {
    for (const viewport of viewports) {
      for (let sample = 1; sample <= 5; sample += 1) {
        plan.push({ target: 'wordpress', route, viewport, sample, order: ++order });
      }
    }
  }
  return plan;
}

function selectMeasurementPlan(phase = 'all') {
  const plan = measurementPlan();
  if (phase === 'home') return plan.slice(0, 20);
  if (phase === 'wordpress-only') return plan.slice(20);
  if (phase === 'all') return plan;
  const error = new Error(`unknown measurement phase: ${phase}`);
  error.validationErrors = [error.message];
  throw error;
}

function validateMeasurementConfig(config) {
  const errors = [];
  const image = /^sha256:[a-f0-9]{64}$/;
  const revision = /^[a-f0-9]{40}$/;
  if (
    typeof config.baselineRoot !== 'string' ||
    !isAbsolute(config.baselineRoot) ||
    !existsSync(config.baselineRoot) ||
    !statSync(config.baselineRoot).isDirectory()
  ) {
    errors.push('baselineRoot must be an existing absolute directory');
  }
  for (const field of ['candidateImage', 'browserImage', 'baselineBuildImage']) {
    if (!image.test(config[field] ?? '')) errors.push(`${field} must be an immutable image ID`);
  }
  for (const field of ['candidateRevision', 'baselineRevision']) {
    if (!revision.test(config[field] ?? '')) errors.push(`${field} must be an exact commit SHA`);
  }
  if (config.wordpressBaseUrl !== 'http://127.0.0.1') {
    errors.push('wordpressBaseUrl must be exactly http://127.0.0.1');
  }
  if (typeof config.wordpressServerVersion !== 'string' || config.wordpressServerVersion === '') {
    errors.push('wordpressServerVersion is required');
  }
  if (errors.length > 0) {
    const error = new Error(errors.join('\n'));
    error.validationErrors = errors;
    throw error;
  }
}

async function runMeasurement(configPath, outputPath, phase = 'all') {
  const config = readJson(configPath);
  validateMeasurementConfig(config);
  const startedAt = new Date().toISOString();
  const staticServer = await startStaticServer({ root: config.baselineRoot, port: 4173 });
  const browser = await launchChromium();
  const samples = [];
  try {
    for (const item of selectMeasurementPlan(phase)) {
      const sampleStartedAt = new Date().toISOString();
      const isBaseline = item.target === 'baseline';
      const paths = {
        home: '/',
        'blog-archive': '/blog/',
        'representative-article': '/gama-cwv-representative-article/',
      };
      const baseUrl = isBaseline ? 'http://127.0.0.1:4173' : config.wordpressBaseUrl;
      const url = new URL(paths[item.route], baseUrl).href;
      const provenance = {
        ...item,
        url,
        sourceRevision: isBaseline ? config.baselineRevision : config.candidateRevision,
        browserImage: config.browserImage,
        serverImage: isBaseline ? config.browserImage : config.candidateImage,
        ...(isBaseline
          ? { buildImage: config.baselineBuildImage }
          : { candidateImage: config.candidateImage }),
      };
      try {
        const result = await collectPage({
          browser,
          ...provenance,
          server: isBaseline
            ? {
                implementation: 'node:http',
                version: process.version.replace(/^v/, ''),
                compression: 'none',
                cacheControl: 'no-store',
                deployment: 'source-built static bytes',
              }
            : {
                implementation: 'Apache HTTP Server',
                version: config.wordpressServerVersion,
                compression: 'none observed',
                cacheControl: 'WordPress defaults',
                deployment: 'immutable local candidate image',
              },
          finalizeUrl: isBaseline
            ? 'http://127.0.0.1:4173/__gama-vitals-finalize.html'
            : 'http://127.0.0.1/wp-login.php?gama-vitals-finalize=1',
          journey:
            item.route === 'home'
              ? (page) => performContactJourney(page, isBaseline ? 'react' : 'wordpress')
              : performReadingJourney,
        });
        samples.push(collectionResult(result));
      } catch (error) {
        samples.push({
          formatVersion: 1,
          ...provenance,
          startedAt: error.startedAt ?? sampleStartedAt,
          completedAt: error.completedAt ?? new Date().toISOString(),
          valid: false,
          collectionError: error.message,
          errors: [`collection failed: ${error.message}`],
        });
      }
    }
  } finally {
    await browser.close();
    await staticServer.close();
  }

  const document = {
    formatVersion: 1,
    startedAt,
    completedAt: new Date().toISOString(),
    library: {
      name: 'web-vitals',
      version: '6.2.1',
      license: 'Apache-2.0',
    },
    phase,
    plan: selectMeasurementPlan(phase),
    samples,
  };
  writeFileSync(outputPath, `${JSON.stringify(document, null, 2)}\n`);
  const errors = validateDocument(document);
  if (errors.length > 0) {
    const error = new Error(errors.join('\n'));
    error.validationErrors = errors;
    throw error;
  }
}

function mergeMeasurements(firstPath, secondPath, outputPath) {
  const first = readJson(firstPath);
  const second = readJson(secondPath);
  const windows = [
    { name: 'home', startedAt: first.startedAt, completedAt: first.completedAt },
    {
      name: 'wordpress-only',
      startedAt: second.startedAt,
      completedAt: second.completedAt,
    },
  ];
  const windowErrors = windows.flatMap((window, index) => {
    const start = Date.parse(window.startedAt ?? '');
    const completion = Date.parse(window.completedAt ?? '');
    const errors = [];
    if (!Number.isFinite(start)) errors.push(`${window.name}: startedAt must be an ISO timestamp`);
    if (!Number.isFinite(completion)) {
      errors.push(`${window.name}: completedAt must be an ISO timestamp`);
    }
    if (Number.isFinite(start) && Number.isFinite(completion) && completion < start) {
      errors.push(`${window.name}: completedAt must not precede startedAt`);
    }
    if (index > 0 && Number.isFinite(start) && start < Date.parse(windows[index - 1].completedAt)) {
      errors.push(`${window.name}: phase must not precede the prior phase`);
    }
    return errors;
  });
  const document = {
    formatVersion: 1,
    startedAt: first.startedAt,
    completedAt: second.completedAt,
    phases: windows,
    library: first.library,
    plan: measurementPlan(),
    samples: [...(first.samples ?? []), ...(second.samples ?? [])],
  };
  writeFileSync(outputPath, `${JSON.stringify(document, null, 2)}\n`);
  const errors = [...windowErrors, ...validateDocument(document)];
  if (document.samples.length !== 40) errors.unshift('document: expected exactly 40 samples');
  if (errors.length > 0) {
    const error = new Error(errors.join('\n'));
    error.validationErrors = errors;
    throw error;
  }
}

async function runControls(path) {
  const sourceRevision = process.env.GAMA_SOURCE_REVISION ?? '0000000000000000000000000000000000000000';
  const browserImage = process.env.GAMA_BROWSER_IMAGE_ID ?? `sha256:${'0'.repeat(64)}`;
  const serverImage = process.env.GAMA_SERVER_IMAGE_ID ?? browserImage;
  const viewport = { name: 'control', width: 1280, height: 720 };
  const server = await startStaticServer({ port: 0 });
  const controlBaseUrl = `http://127.0.0.1:${server.server.address().port}`;
  const browser = await launchChromium();
  try {
    let order = 0;
    const common = {
      browser,
      target: 'control',
      viewport,
      sourceRevision,
      browserImage,
      serverImage,
      server: {
        implementation: 'node:http',
        version: process.version.replace(/^v/, ''),
        compression: 'none',
        cacheControl: 'no-store',
      },
    };
    const missingMetric = collectionResult(
      await collectPage({
        ...common,
        route: 'missing-input',
        url: `${controlBaseUrl}/control-missing.html`,
        sample: 1,
        order: ++order,
      }),
    );
    const layoutShift = collectionResult(
      await collectPage({
        ...common,
        route: 'layout-shift',
        url: `${controlBaseUrl}/control-layout.html`,
        sample: 1,
        order: ++order,
        journey: async (page) => {
          await page.locator('#spacer[data-shifted="true"]').waitFor();
          await page.locator('#control').click();
        },
      }),
    );
    const slowInput = collectionResult(
      await collectPage({
        ...common,
        route: 'slow-input',
        url: `${controlBaseUrl}/control-slow.html`,
        sample: 1,
        order: ++order,
        journey: async (page) => {
          await page.locator('#control').click();
          await page.locator('#done').waitFor();
        },
      }),
    );
    const recoveryLoss = collectionResult(
      await collectPage({
        ...common,
        route: 'recovery-loss',
        url: `${controlBaseUrl}/control-slow.html`,
        finalizeUrl: `${controlBaseUrl}/__gama-vitals-finalize-partial.html`,
        sample: 1,
        order: ++order,
        journey: async (page) => {
          await page.locator('#control').click();
          await page.locator('#done').waitFor();
        },
      }),
    );
    writeFileSync(
      path,
      `${JSON.stringify(
        {
          formatVersion: 1,
          library: { name: 'web-vitals', version: '6.2.1' },
          missingMetric,
          layoutShift,
          slowInput,
          recoveryLoss,
        },
        null,
        2,
      )}\n`,
    );
  } finally {
    await browser.close();
    await server.close();
  }
}

async function runJourneyControls(path) {
  const sourceRevision = process.env.GAMA_SOURCE_REVISION ?? '0000000000000000000000000000000000000000';
  const browserImage = process.env.GAMA_BROWSER_IMAGE_ID ?? `sha256:${'0'.repeat(64)}`;
  const serverImage = process.env.GAMA_SERVER_IMAGE_ID ?? browserImage;
  const server = await startStaticServer({ port: 0 });
  const controlBaseUrl = `http://127.0.0.1:${server.server.address().port}`;
  const browser = await launchChromium();
  try {
    const samples = [];
    for (const [index, adapter] of ['react', 'wordpress'].entries()) {
      samples.push(
        collectionResult(
          await collectPage({
            browser,
            target: 'control',
            route: `${adapter}-adapter`,
            url: `${controlBaseUrl}/adapter-${adapter}.html`,
            viewport: { name: 'control', width: 1280, height: 720 },
            sample: 1,
            order: index + 1,
            sourceRevision,
            browserImage,
            serverImage,
            server: {
              implementation: 'node:http',
              version: process.version.replace(/^v/, ''),
              compression: 'none',
              cacheControl: 'no-store',
            },
            journey: (page) => performContactJourney(page, adapter),
          }),
        ),
      );
    }
    writeFileSync(path, `${JSON.stringify({ formatVersion: 1, samples }, null, 2)}\n`);
  } finally {
    await browser.close();
    await server.close();
  }
}

try {
  if (command === 'measure' && input && output) {
    await runMeasurement(input, output, extra ?? 'all');
  } else if (command === 'merge' && input && output && extra) {
    mergeMeasurements(input, output, extra);
  } else if (command === 'plan' && output === undefined) {
    process.stdout.write(`${JSON.stringify(selectMeasurementPlan(input ?? 'all'), null, 2)}\n`);
  } else if (command === 'journey-controls' && input && output === undefined) {
    await runJourneyControls(input);
  } else if (command === 'controls' && input && output === undefined) {
    await runControls(input);
  } else if (command === 'validate' && input && output === undefined) {
    const document = readJson(input);
    const errors = validateDocument(document);
    if (errors.length > 0) {
      process.stderr.write(`${errors.join('\n')}\n`);
      process.exitCode = 2;
    } else {
      process.stdout.write(`Validated ${document.samples.length} sample(s).\n`);
    }
  } else if (command === 'summarize' && input && output) {
    writeFileSync(output, `${JSON.stringify(summarize(readJson(input)), null, 2)}\n`);
  } else {
    process.stderr.write(
      'Usage: runner.mjs <plan [PHASE] | measure CONFIG OUTPUT [PHASE] | merge HOME WORDPRESS OUTPUT | validate INPUT | summarize INPUT OUTPUT>\n',
    );
    process.exitCode = 64;
  }
} catch (error) {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = error.validationErrors ? 2 : 1;
}
