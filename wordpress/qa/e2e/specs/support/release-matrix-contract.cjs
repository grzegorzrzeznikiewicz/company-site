'use strict';

const assert = require('node:assert/strict');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const e2eRoot = path.resolve(__dirname, '../..');
const playwrightCli = path.join(
  e2eRoot,
  'node_modules',
  '@playwright',
  'test',
  'cli.js',
);
const releaseFile = 'release-regression.spec.ts';
const releaseTitle = (viewport) =>
  `@release-regression ${viewport} is functional, accessible and within budget`;

function collectSpecs(suites, collected = []) {
  for (const suite of suites ?? []) {
    for (const spec of suite.specs ?? []) {
      for (const test of spec.tests ?? []) {
        collected.push({
          file: spec.file,
          projectName: test.projectName,
          title: spec.title,
        });
      }
    }
    collectSpecs(suite.suites, collected);
  }
  return collected;
}

function inspectCollection() {
  const result = spawnSync(
    'node',
    [
      playwrightCli,
      'test',
      '--config=./playwright.config.ts',
      '--list',
      '--reporter=json',
    ],
    {
      cwd: e2eRoot,
      encoding: 'utf8',
      env: {
        ...process.env,
        PW_TEST_REPORTER: '',
        PW_TEST_SOURCE_TRANSFORM: '',
        PW_TEST_SOURCE_TRANSFORM_SCOPE: '',
        PWDEBUG: '',
      },
    },
  );
  assert.equal(
    result.status,
    0,
    `Playwright collection failed:\n${result.stderr || result.stdout}`,
  );
  const collection = JSON.parse(result.stdout);
  assert.deepEqual(
    collection.errors,
    [],
    'Playwright collection reported errors',
  );
  return collection;
}

function validateCollection(collection) {
  assert.equal(
    collection.config.version,
    '1.62.1',
    'release collection must use the pinned Playwright 1.62.1 runtime',
  );
  assert.deepEqual(
    collection.config.projects.map(({ name }) => name),
    ['', 'webkit'],
    'the existing unnamed Chromium project and one named WebKit project are required',
  );

  const collected = collectSpecs(collection.suites);
  const releaseCases = collected
    .filter(({ file }) => file === releaseFile)
    .map(({ projectName, title }) => `${projectName || 'chromium'}:${title}`)
    .sort();
  const expectedReleaseCases = ['', 'webkit']
    .flatMap((projectName) =>
      ['desktop', 'phone', 'tablet'].map(
        (viewport) => `${projectName || 'chromium'}:${releaseTitle(viewport)}`,
      ),
    )
    .sort();
  assert.deepEqual(
    releaseCases,
    expectedReleaseCases,
    'release collection must contain exactly six browser/viewport cases',
  );

  const nonReleaseCases = collected.filter(({ file }) => file !== releaseFile);
  assert.equal(
    nonReleaseCases.length,
    39,
    'the existing non-release test selection must remain unchanged',
  );
  assert.equal(
    nonReleaseCases.every(({ projectName }) => projectName === ''),
    true,
    'WebKit must not collect editor or other non-release tests',
  );

  const screenshotCases = nonReleaseCases.filter(
    ({ title }) =>
      title.includes('@global-styles-front-snapshots') ||
      title.includes('@global-styles-editor-snapshots'),
  );
  assert.equal(screenshotCases.length, 2);
  assert.equal(
    screenshotCases.every(({ projectName }) => projectName === ''),
    true,
    'existing screenshot identities must stay on the unnamed project',
  );
}

validateCollection(inspectCollection());
console.log(
  'Release matrix collection contract passed: Chromium and WebKit x desktop, tablet and phone; non-release selection unchanged.',
);

module.exports = { collectSpecs, validateCollection };
