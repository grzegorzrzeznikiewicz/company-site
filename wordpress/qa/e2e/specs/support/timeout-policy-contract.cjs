'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const {
  ALLOWED_SCOPED_TIMEOUTS,
  DEFAULT_TIMEOUT,
  loadPinnedAstTools,
  readSpecSources,
  validateResolvedPolicy,
  validateSpecSources,
} = require('./timeout-policy-reporter.cjs');
const {
  validatePlaywrightCliArguments,
} = require('./run-playwright.cjs');

const rootDirectory = path.resolve(__dirname, '../..');
const baselineSources = readSpecSources(rootDirectory);

function mutateSource(file, mutate) {
  let found = false;
  const result = baselineSources.map((entry) => {
    if (entry.file !== file) {
      return entry;
    }
    found = true;
    return { ...entry, source: mutate(entry.source) };
  });
  assert.equal(found, true, `Missing mutation target: ${file}`);
  return result;
}

function expectSourceMutationRejected(label, sources, messagePattern) {
  const errors = validateSpecSources(sources);
  assert.notEqual(errors.length, 0, `${label} unexpectedly passed`);
  assert.match(
    errors.join('\n'),
    messagePattern,
    `${label} failed ambiguously`,
  );
}

function withCopiedSpecTree(mutate, inspect) {
  const fixtureRoot = fs.mkdtempSync(
    path.join(os.tmpdir(), 'gama-timeout-policy-'),
  );
  try {
    fs.cpSync(path.join(rootDirectory, 'specs'), path.join(fixtureRoot, 'specs'), {
      recursive: true,
    });
    fs.copyFileSync(
      path.join(rootDirectory, 'playwright.config.ts'),
      path.join(fixtureRoot, 'playwright.config.ts'),
    );
    fs.copyFileSync(
      path.join(rootDirectory, 'timeout-policy.tsconfig.json'),
      path.join(fixtureRoot, 'timeout-policy.tsconfig.json'),
    );
    mutate(fixtureRoot);
    return inspect(fixtureRoot);
  } finally {
    fs.rmSync(fixtureRoot, { force: true, recursive: true });
  }
}

function withCopiedSpecMutation(mutate) {
  return withCopiedSpecTree(mutate, readSpecSources);
}

function expectFilesystemMutationRejected(label, mutate, messagePattern) {
  assert.throws(
    () => withCopiedSpecTree(mutate, readSpecSources),
    messagePattern,
    `${label} unexpectedly passed`,
  );
}

function importedHelperMutation(extension, helperSource) {
  return withCopiedSpecMutation((fixtureRoot) => {
    const specFile = path.join(fixtureRoot, 'specs/site-editor.spec.ts');
    fs.appendFileSync(
      specFile,
      `\nimport './support/runtime-timeout${extension}';\n`,
    );
    fs.writeFileSync(
      path.join(fixtureRoot, `specs/support/runtime-timeout${extension}`),
      helperSource,
    );
  });
}

function insertAfterHeaderTimeout(addition) {
  return (source) => {
    const needle = '  test.setTimeout(90_000);';
    assert.equal(source.split(needle).length - 1, 1);
    return source.replace(needle, `${needle} ${addition}`);
  };
}

function replaceHeaderNavigationCallback(source, callbackHead) {
  const needle = `test('lets the disposable Editor transform and save native header navigation through the Site Editor UI @navigation-save', async ({
  page,
}, testInfo) => {`;
  const replacement = `test('lets the disposable Editor transform and save native header navigation through the Site Editor UI @navigation-save', ${callbackHead} {`;
  assert.equal(source.split(needle).length - 1, 1);
  return source.replace(needle, replacement);
}

function replaceHeaderNavigationTestInfoParameter(source, parameter) {
  return replaceHeaderNavigationCallback(
    source,
    `async ({
  page,
}, ${parameter}) =>`,
  );
}

loadPinnedAstTools();
assert.deepEqual(validateSpecSources(baselineSources), []);

assert.deepEqual(
  validatePlaywrightCliArguments([
    '--list',
    '--grep',
    '@navigation-save',
    '--shard=1/2',
    '--last-failed',
    '--only-changed',
    '--update-snapshots',
  ]),
  [
    '--list',
    '--grep',
    '@navigation-save',
    '--shard=1/2',
    '--last-failed',
    '--only-changed',
    '--update-snapshots',
  ],
);
for (const unsafeArgument of [
  '--config=./unsafe.config.ts',
  '--debug',
  '--reporter=list',
  '--timeout=180000',
  '--tsconfig=./unsafe.tsconfig.json',
]) {
  assert.throws(
    () => validatePlaywrightCliArguments([unsafeArgument]),
    new RegExp(`Unsupported Playwright CLI argument: ${unsafeArgument}`),
    `${unsafeArgument} must not bypass the reviewed Playwright configuration`,
  );
}
assert.throws(
  () => validatePlaywrightCliArguments(['--grep']),
  /requires one non-option value/,
  'a selector without its value must not consume a later CLI override',
);

const safeTestInfoTitleRead = mutateSource(
  'specs/header-footer-navigation.spec.ts',
  insertAfterHeaderTimeout("void testInfo.title.includes('@navigation-save');"),
);
assert.deepEqual(validateSpecSources(safeTestInfoTitleRead), []);

expectFilesystemMutationRejected(
  'package metadata local import mutation',
  (fixtureRoot) => {
    const aliasDirectory = path.join(
      fixtureRoot,
      'specs/support/policy-alias',
    );
    fs.mkdirSync(aliasDirectory, { recursive: true });
    fs.writeFileSync(
      path.join(aliasDirectory, 'index.ts'),
      'export const inert = true;\n',
    );
    fs.writeFileSync(
      path.join(aliasDirectory, 'package.json'),
      JSON.stringify({ main: '../../../node_modules/@playwright/test' }),
    );
    fs.appendFileSync(
      path.join(fixtureRoot, 'specs/site-editor.spec.ts'),
      "\nimport * as runtimePlaywright from './support/policy-alias'; runtimePlaywright.test.setTimeout(180_000);\n",
    );
  },
  /package\.json is forbidden below the timeout-controlled specs directory/,
);

expectFilesystemMutationRejected(
  'TypeScript path mapping metadata mutation',
  (fixtureRoot) => {
    fs.writeFileSync(
      path.join(fixtureRoot, 'specs/tsconfig.json'),
      JSON.stringify({
        compilerOptions: {
          baseUrl: '.',
          paths: { '@playwright/test': ['./support/policy-alias'] },
        },
      }),
    );
  },
  /only source files and PNG snapshot assets may exist below the timeout-controlled specs directory/,
);

expectFilesystemMutationRejected(
  'trusted tsconfig path mapping mutation',
  (fixtureRoot) => {
    fs.writeFileSync(
      path.join(fixtureRoot, 'timeout-policy.tsconfig.json'),
      JSON.stringify({
        compilerOptions: {
          baseUrl: '.',
          paths: { '@playwright/test': ['./specs/support/policy-alias'] },
        },
      }),
    );
  },
  /trusted timeout policy tsconfig must contain exactly the reviewed empty compilerOptions object/,
);

expectFilesystemMutationRejected(
  'Playwright config symlink mutation',
  (fixtureRoot) => {
    const configFile = path.join(fixtureRoot, 'playwright.config.ts');
    const externalConfigFile = path.join(fixtureRoot, 'unsafe-config.ts');
    fs.renameSync(configFile, externalConfigFile);
    fs.symlinkSync('./unsafe-config.ts', configFile);
  },
  /requires playwright\.config\.ts to be a regular file/,
);

expectSourceMutationRejected(
  'environment-dependent config timeout mutation',
  mutateSource('playwright.config.ts', (source) =>
    source.replace(
      '  timeout: 60_000,',
      '  timeout: process.env.GAMA_PLAYWRIGHT_RUN ? 180_000 : 60_000,',
    ),
  ),
  /config timeout must be the literal 60000/,
);

expectSourceMutationRejected(
  'environment-dependent config reporter mutation',
  mutateSource('playwright.config.ts', (source) =>
    source.replace(
      "  reporter: [\n    ['list'],",
      "  reporter: process.env.GAMA_PLAYWRIGHT_RUN ? [['list']] : [\n    ['list'],",
    ),
  ),
  /reporter must be exactly list, html, then/,
);

expectSourceMutationRejected(
  'unknown environment read mutation',
  mutateSource(
    'playwright.config.ts',
    (source) => `${source}\nvoid process.env.PWDEBUG;\n`,
  ),
  /process\.env may only directly read allowlisted variables/,
);

expectSourceMutationRejected(
  'environment alias mutation',
  mutateSource(
    'playwright.config.ts',
    (source) => `${source}\nconst runtimeEnvironment = process.env;\n`,
  ),
  /process\.env may only directly read allowlisted variables/,
);

expectSourceMutationRejected(
  'allowlisted environment write mutation',
  mutateSource(
    'playwright.config.ts',
    (source) => `${source}\nprocess.env.WP_BASE_URL = 'http://unsafe';\n`,
  ),
  /environment state mutation is forbidden/,
);

expectSourceMutationRejected(
  'allowlisted environment delete mutation',
  mutateSource(
    'playwright.config.ts',
    (source) => `${source}\ndelete process.env.WP_BASE_URL;\n`,
  ),
  /environment state mutation is forbidden/,
);

expectSourceMutationRejected(
  'allowlisted environment update mutation',
  mutateSource(
    'playwright.config.ts',
    (source) => `${source}\nprocess.env.WP_BASE_URL++;\n`,
  ),
  /environment state mutation is forbidden/,
);

expectSourceMutationRejected(
  'bracketed environment write mutation',
  mutateSource(
    'playwright.config.ts',
    (source) => `${source}\nprocess['env'].PWDEBUG = '1';\n`,
  ),
  /environment state mutation is forbidden/,
);

expectSourceMutationRejected(
  'constant-key environment write mutation',
  mutateSource(
    'playwright.config.ts',
    (source) =>
      `${source}\nconst environmentKey = 'env';\nprocess[environmentKey].PW_TEST_SOURCE_TRANSFORM = './specs/support/evil.cjs';\n`,
  ),
  /environment state mutation is forbidden/,
);

expectSourceMutationRejected(
  'optional environment object passing mutation',
  mutateSource(
    'playwright.config.ts',
    (source) => `${source}\nObject.assign(process?.env, { PWDEBUG: '1' });\n`,
  ),
  /process\.env may only directly read allowlisted variables/,
);

expectSourceMutationRejected(
  'optional environment alias mutation',
  mutateSource(
    'playwright.config.ts',
    (source) =>
      `${source}\nconst runtimeEnvironment = process?.env;\nObject.assign(runtimeEnvironment, { PWDEBUG: '1' });\n`,
  ),
  /process\.env may only directly read allowlisted variables/,
);

expectSourceMutationRejected(
  'environment destructuring mutation',
  mutateSource(
    'playwright.config.ts',
    (source) => `${source}\nconst { WP_BASE_URL: unsafeBaseUrl } = process.env;\n`,
  ),
  /process\.env may only directly read allowlisted variables/,
);

expectSourceMutationRejected(
  'environment object passing mutation',
  mutateSource(
    'playwright.config.ts',
    (source) => `${source}\nObject.assign(process.env, { PWDEBUG: '1' });\n`,
  ),
  /process\.env may only directly read allowlisted variables/,
);

expectSourceMutationRejected(
  'Playwright source transform environment mutation',
  mutateSource(
    'playwright.config.ts',
    (source) =>
      `${source}\nprocess.env.PW_TEST_SOURCE_TRANSFORM = './specs/support/evil.cjs';\nprocess.env.PW_TEST_SOURCE_TRANSFORM_SCOPE = '/tests/specs';\n`,
  ),
  /process\.env may only directly read allowlisted variables/,
);

expectSourceMutationRejected(
  'indirect exported config mutation',
  mutateSource('playwright.config.ts', (source) => {
    assert.equal(source.split('export default defineConfig({').length - 1, 1);
    assert.equal(source.split('\n});\n').length - 1, 1);
    return source
      .replace('export default defineConfig({', 'const reviewed = defineConfig({')
      .replace(
        '\n});\n',
        "\n});\n\nexport default { ...reviewed, timeout: 180_000, reporter: [['list']] };\n",
      );
  }),
  /only defineConfig call must be the direct export default value/,
);

expectSourceMutationRejected(
  'extra reporter after policy mutation',
  mutateSource('playwright.config.ts', (source) =>
    source.replace(
      "    ['./specs/support/timeout-policy-reporter.cjs'],",
      "    ['./specs/support/timeout-policy-reporter.cjs'],\n    ['./specs/support/override-reporter.cjs'],",
    ),
  ),
  /reporter must be exactly list, html, then/,
);

expectSourceMutationRejected(
  'missing Playwright config mutation',
  baselineSources.filter(({ file }) => file !== 'playwright.config.ts'),
  /requires exactly one playwright\.config\.ts source entry/,
);

const harmlessLexicalLookalikes = mutateSource(
  'specs/site-editor.spec.ts',
  (source) =>
    `${source}\n// test['slow'](); is intentionally only a policy-test comment.\nconst timeoutPolicyDocumentation = "testInfo['setTimeout'](180_000)";\nconst unrelatedTimer = { slow() {}, setTimeout() {} };\nunrelatedTimer.slow();\nunrelatedTimer.setTimeout();\nconst { setTimeout: unrelatedSetTimeout } = unrelatedTimer;\nunrelatedSetTimeout();\nvoid timeoutPolicyDocumentation;\n`,
);
assert.deepEqual(validateSpecSources(harmlessLexicalLookalikes), []);

for (const [extension, helperSource] of [
  [
    '.ts',
    "import { test } from '@playwright/test';\ntest.setTimeout(180_000);\n",
  ],
  [
    '.js',
    "import { test } from '@playwright/test';\ntest.setTimeout(180_000);\n",
  ],
  [
    '.mjs',
    "import { test } from '@playwright/test';\ntest.setTimeout(180_000);\n",
  ],
  [
    '.cjs',
    "const { test } = require('@playwright/test');\ntest.setTimeout(180_000);\n",
  ],
]) {
  expectSourceMutationRejected(
    `imported ${extension} support timeout mutation`,
    importedHelperMutation(extension, helperSource),
    /only the three directly bound|CommonJS Playwright imports are forbidden/,
  );
}

expectSourceMutationRejected(
  'dynamic Playwright import mutation',
  mutateSource(
    'specs/site-editor.spec.ts',
    (source) =>
      `${source}\nconst { test: runtimeTest } = await import('@playwright/test'); runtimeTest.setTimeout(180_000);\n`,
  ),
  /dynamic import is forbidden/,
);

expectSourceMutationRejected(
  'TypeScript import assignment mutation',
  mutateSource(
    'specs/site-editor.spec.ts',
    (source) =>
      `import runtimePlaywright = require('@playwright/test');\n${source}\nruntimePlaywright.test.setTimeout(180_000);\n`,
  ),
  /TypeScript import assignments are forbidden/,
);

expectSourceMutationRejected(
  'direct eval mutation',
  mutateSource(
    'specs/site-editor.spec.ts',
    (source) => `${source}\neval("test.setTimeout(180_000)");\n`,
  ),
  /dynamic code execution is forbidden/,
);

expectSourceMutationRejected(
  'aliased eval mutation',
  mutateSource(
    'specs/site-editor.spec.ts',
    (source) =>
      `${source}\nconst executeTimeout = eval; executeTimeout("test.setTimeout(180_000)");\n`,
  ),
  /dynamic code execution is forbidden/,
);

expectSourceMutationRejected(
  'Function constructor mutation',
  mutateSource(
    'specs/site-editor.spec.ts',
    (source) => `${source}\nFunction("test.setTimeout(180_000)")();\n`,
  ),
  /dynamic code execution is forbidden/,
);

expectSourceMutationRejected(
  'aliased CommonJS loader mutation',
  mutateSource(
    'specs/site-editor.spec.ts',
    (source) =>
      `${source}\nconst loadPlaywright = require; const { test: runtimeTest } = loadPlaywright('@playwright/test'); runtimeTest.setTimeout(180_000);\n`,
  ),
  /indirect module loading is forbidden/,
);

expectSourceMutationRejected(
  'dynamic module loader mutation',
  mutateSource(
    'specs/site-editor.spec.ts',
    (source) =>
      `${source}\nconst loadPlaywright = module[process.env.GAMA_MODULE_LOADER].bind(module); const { test: runtimeTest } = loadPlaywright('@playwright/test'); runtimeTest.setTimeout(180_000);\n`,
  ),
  /Node module loader access is forbidden/,
);

expectSourceMutationRejected(
  'CommonJS wrapper arguments loader mutation',
  mutateSource(
    'specs/site-editor.spec.ts',
    (source) =>
      `${source}\nconst runtimeRequire = arguments[1]; const { test: runtimeTest } = runtimeRequire('@playwright/test'); runtimeTest.setTimeout(180_000);\n`,
  ),
  /implicit arguments is forbidden/,
);

expectSourceMutationRejected(
  'dynamic function constructor mutation',
  mutateSource(
    'specs/site-editor.spec.ts',
    (source) =>
      `${source}\nasync function widenAtRuntime() { let key; key = 'constructor'; const Compile = (async () => {})[key]; const runtimeModule = await Compile("return import('@playwright/test')")(); const { test: runtimeTest } = runtimeModule; runtimeTest.setTimeout(180_000); }\n`,
  ),
  /unknown computed property access|dynamic access to a function or class constructor is forbidden/,
);

expectSourceMutationRejected(
  'unknown computed property mutation',
  mutateSource(
    'specs/site-editor.spec.ts',
    (source) =>
      `${source}\nconst opaqueLookup = {}; let opaqueKey; opaqueKey = 'anything'; void opaqueLookup[opaqueKey];\n`,
  ),
  /unknown computed property access is forbidden/,
);

expectSourceMutationRejected(
  'prototype descriptor function constructor mutation',
  mutateSource(
    'specs/site-editor.spec.ts',
    (source) =>
      `${source}\nasync function widenAtRuntime() { const proto = Object.getPrototypeOf(async () => {}); const Compile = Object.getOwnPropertyDescriptor(proto, 'constructor').value; const runtimeModule = await Compile("return import('@playwright/test')")(); const { test: runtimeTest } = runtimeModule; runtimeTest.setTimeout(180_000); }\n`,
  ),
  /dynamic code execution or indirect module loading is forbidden/,
);

expectSourceMutationRejected(
  'computed slow mutation',
  mutateSource(
    'specs/site-editor.spec.ts',
    (source) => `${source}\ntest['slow']();\n`,
  ),
  /slow aliases and bracket forms are forbidden/,
);

expectSourceMutationRejected(
  'aliased test mutation',
  mutateSource(
    'specs/site-editor.spec.ts',
    (source) => `${source}\nconst aliasedTest = test; aliasedTest.slow();\n`,
  ),
  /aliasing or indirect access|slow aliases/,
);

expectSourceMutationRejected(
  'aliased timeout method mutation',
  mutateSource(
    'specs/site-editor.spec.ts',
    (source) =>
      `${source}\nconst changeTimeout = test.setTimeout; changeTimeout(90_000);\n`,
  ),
  /only the three directly bound|aliasing or indirect access/,
);

expectSourceMutationRejected(
  'namespace-imported test mutation',
  mutateSource(
    'specs/site-editor.spec.ts',
    (source) =>
      `import * as playwrightApi from '@playwright/test';\n${source}\nplaywrightApi.test.setTimeout(180_000);\n`,
  ),
  /namespace or default Playwright imports are forbidden/,
);

expectSourceMutationRejected(
  'CommonJS imported test mutation',
  mutateSource(
    'specs/site-editor.spec.ts',
    (source) =>
      `${source}\nconst playwrightApi = require('@playwright/test'); playwrightApi.test.setTimeout(180_000);\n`,
  ),
  /CommonJS Playwright imports are forbidden/,
);

expectSourceMutationRejected(
  'extended test alias mutation',
  mutateSource(
    'specs/site-editor.spec.ts',
    (source) =>
      `${source}\nconst extendedTest = test.extend({}); extendedTest.setTimeout(180_000);\n`,
  ),
  /test\.extend aliases are forbidden/,
);

expectSourceMutationRejected(
  'testInfo bracket mutation',
  mutateSource(
    'specs/header-footer-navigation.spec.ts',
    insertAfterHeaderTimeout("testInfo['setTimeout'](180_000);"),
  ),
  /only the three directly bound/,
);

expectSourceMutationRejected(
  'testInfo private timeout manager mutation',
  mutateSource(
    'specs/header-footer-navigation.spec.ts',
    insertAfterHeaderTimeout('testInfo._timeoutManager.setIgnoreTimeouts();'),
  ),
  /private Playwright timeout internals are forbidden/,
);

expectSourceMutationRejected(
  'indirect test.info invocation mutation',
  mutateSource(
    'specs/header-footer-navigation.spec.ts',
    insertAfterHeaderTimeout(
      'test.info.call(null)._timeoutManager.setIgnoreTimeouts();',
    ),
  ),
  /indirect invocation of a Playwright test API is forbidden/,
);

expectSourceMutationRejected(
  'destructured TestInfo callback parameter mutation',
  mutateSource('specs/header-footer-navigation.spec.ts', (source) =>
    insertAfterHeaderTimeout('_timeoutManager.setIgnoreTimeouts();')(
      replaceHeaderNavigationTestInfoParameter(source, '{ _timeoutManager }'),
    ),
  ),
  /second Playwright test or hook callback parameter must be a bare TestInfo identifier/,
);

expectSourceMutationRejected(
  'rest TestInfo callback parameter mutation',
  mutateSource('specs/header-footer-navigation.spec.ts', (source) =>
    insertAfterHeaderTimeout('args[0]._timeoutManager.setIgnoreTimeouts();')(
      replaceHeaderNavigationTestInfoParameter(source, '...args'),
    ),
  ),
  /second Playwright test or hook callback parameter must be a bare TestInfo identifier/,
);

expectSourceMutationRejected(
  'defaulted TestInfo callback parameter mutation',
  mutateSource('specs/header-footer-navigation.spec.ts', (source) =>
    insertAfterHeaderTimeout('testInfo._timeoutManager.setIgnoreTimeouts();')(
      replaceHeaderNavigationTestInfoParameter(source, 'testInfo = undefined'),
    ),
  ),
  /second Playwright test or hook callback parameter must be a bare TestInfo identifier/,
);

expectSourceMutationRejected(
  'third Playwright callback parameter mutation',
  mutateSource('specs/header-footer-navigation.spec.ts', (source) =>
    replaceHeaderNavigationTestInfoParameter(source, 'testInfo, unused'),
  ),
  /Playwright test and hook callbacks may declare at most two parameters/,
);

expectSourceMutationRejected(
  'rest fixture callback parameter mutation',
  mutateSource('specs/header-footer-navigation.spec.ts', (source) =>
    insertAfterHeaderTimeout('args[1]._timeoutManager.setIgnoreTimeouts();')(
      replaceHeaderNavigationCallback(source, 'async (...args) =>'),
    ),
  ),
  /first Playwright test or hook callback parameter must be a fixture identifier or object pattern/,
);

expectSourceMutationRejected(
  'function-expression callback arguments mutation',
  mutateSource('specs/header-footer-navigation.spec.ts', (source) =>
    insertAfterHeaderTimeout('arguments[1]._timeoutManager.setIgnoreTimeouts();')(
      replaceHeaderNavigationCallback(source, 'async function ()'),
    ),
  ),
  /Playwright test and hook callbacks must be inline ArrowFunctionExpression values/,
);

expectSourceMutationRejected(
  'named callback TestInfo arguments mutation',
  mutateSource(
    'specs/site-editor.spec.ts',
    (source) =>
      `${source}\nasync function timeoutBypass(...args) { args[1]._timeoutManager.setIgnoreTimeouts(); }\ntest('ordinary runtime bypass', timeoutBypass);\n`,
  ),
  /Playwright test and hook callbacks must be inline ArrowFunctionExpression values/,
);

expectSourceMutationRejected(
  'test only callback mutation',
  mutateSource(
    'specs/site-editor.spec.ts',
    (source) =>
      `${source}\ntest.only('ordinary runtime bypass', async (...args) => { args[1]._timeoutManager.setIgnoreTimeouts(); });\n`,
  ),
  /unsupported Playwright test API member only is forbidden by the timeout policy/,
);

for (const [label, mutation] of [
  [
    'TestInfo project assignment mutation',
    'testInfo.project.timeout = 180_000;',
  ],
  [
    'TestInfo project Object.assign mutation',
    'Object.assign(testInfo.project, { timeout: 180_000 });',
  ],
  [
    'TestInfo project nested configuration mutation',
    'testInfo.project.use.actionTimeout = 180_000;',
  ],
  ['TestInfo project delete mutation', 'delete testInfo.project.timeout;'],
  ['TestInfo project update mutation', 'testInfo.project.timeout++;'],
]) {
  expectSourceMutationRejected(
    label,
    mutateSource(
      'specs/header-footer-navigation.spec.ts',
      insertAfterHeaderTimeout(mutation),
    ),
    /unsupported TestInfo member project is forbidden by the timeout policy/,
  );
}

expectSourceMutationRejected(
  'test.info result mutation',
  mutateSource(
    'specs/header-footer-navigation.spec.ts',
    insertAfterHeaderTimeout("test.info()['setTimeout'](180_000);"),
  ),
  /only the three directly bound/,
);

expectSourceMutationRejected(
  'object-wrapped test.info result mutation',
  mutateSource(
    'specs/header-footer-navigation.spec.ts',
    insertAfterHeaderTimeout(
      "const timeoutBox = { info: test.info() }; timeoutBox.info['setTimeout'](180_000);",
    ),
  ),
  /TestInfo may only use direct properties or explicitly typed local helpers/,
);

expectSourceMutationRejected(
  'dynamic testInfo alias mutation',
  mutateSource(
    'specs/header-footer-navigation.spec.ts',
    insertAfterHeaderTimeout(
      'const infoAlias = testInfo; const timeoutMethod = process.env.TIMEOUT_METHOD; infoAlias[timeoutMethod]?.(180_000);',
    ),
  ),
  /dynamic Playwright timeout-capable member access is forbidden/,
);

expectSourceMutationRejected(
  'object-wrapped TestInfo mutation',
  mutateSource(
    'specs/header-footer-navigation.spec.ts',
    insertAfterHeaderTimeout(
      "const timeoutBox = { info: testInfo }; timeoutBox.info['setTimeout'](180_000);",
    ),
  ),
  /TestInfo may only use direct properties or explicitly typed local helpers/,
);

expectSourceMutationRejected(
  'array-wrapped TestInfo mutation',
  mutateSource(
    'specs/header-footer-navigation.spec.ts',
    insertAfterHeaderTimeout(
      "const timeoutBox = [testInfo]; timeoutBox[0]['setTimeout'](180_000);",
    ),
  ),
  /TestInfo may only use direct properties or explicitly typed local helpers/,
);

expectSourceMutationRejected(
  'returned TestInfo wrapper mutation',
  mutateSource(
    'specs/header-footer-navigation.spec.ts',
    insertAfterHeaderTimeout(
      "function wrapTimeoutInfo(info: TestInfo) { return { info }; } const timeoutBox = wrapTimeoutInfo(testInfo); timeoutBox.info['setTimeout'](180_000);",
    ),
  ),
  /TestInfo may only use direct properties or explicitly typed local helpers/,
);

expectSourceMutationRejected(
  'testInfo hook mutation',
  mutateSource('specs/site-editor.spec.ts', (source) =>
    source.replace(
      'test.beforeEach(async ({ page }, testInfo) => {',
      "test.beforeEach(async ({ page }, testInfo) => { testInfo['setTimeout'](180_000);",
    ),
  ),
  /only the three directly bound/,
);

expectSourceMutationRejected(
  'typed TestInfo helper mutation',
  mutateSource(
    'specs/header-footer-navigation.spec.ts',
    (source) =>
      `${source}\nfunction widenTyped(info: TestInfo) { info.setTimeout(180_000); }\n`,
  ),
  /only the three directly bound/,
);

expectSourceMutationRejected(
  'typed TestInfo helper arguments mutation',
  mutateSource('specs/header-footer-navigation.spec.ts', (source) => {
    const withCall = insertAfterHeaderTimeout('widenWithArguments(testInfo);')(
      source,
    );
    return `${withCall}\nfunction widenWithArguments(info: TestInfo) { arguments[0]._timeoutManager.setIgnoreTimeouts(); }\n`;
  }),
  /implicit arguments is forbidden/,
);

expectSourceMutationRejected(
  'untyped propagated TestInfo helper mutation',
  mutateSource('specs/header-footer-navigation.spec.ts', (source) => {
    const withCall = insertAfterHeaderTimeout('widenUntyped(testInfo);')(
      source,
    );
    return `${withCall}\nfunction widenUntyped(info) { info['setTimeout'](180_000); }\n`;
  }),
  /TestInfo may only use direct properties or explicitly typed local helpers|only the three directly bound/,
);

expectSourceMutationRejected(
  'constant-folded dynamic method mutation',
  mutateSource(
    'specs/site-editor.spec.ts',
    (source) =>
      `${source}\nconst timeoutMethod = 'set' + 'Timeout'; test[timeoutMethod](180_000);\n`,
  ),
  /only the three directly bound/,
);

expectSourceMutationRejected(
  'unknown dynamic test method mutation',
  mutateSource(
    'specs/site-editor.spec.ts',
    (source) =>
      `${source}\nconst timeoutMethod = process.env.TIMEOUT_METHOD; test[timeoutMethod]?.(180_000);\n`,
  ),
  /dynamic Playwright timeout-capable member access is forbidden/,
);

expectSourceMutationRejected(
  'describe configure mutation',
  mutateSource(
    'specs/site-editor.spec.ts',
    (source) => `${source}\ntest.describe.configure({ timeout: 180_000 });\n`,
  ),
  /test\.describe\.configure is forbidden/,
);

expectSourceMutationRejected(
  'Reflect test access mutation',
  mutateSource(
    'specs/site-editor.spec.ts',
    (source) => `${source}\nReflect.get(test, 'slow')();\n`,
  ),
  /Reflect access|aliasing or indirect access to Playwright test is forbidden/,
);

expectSourceMutationRejected(
  'Reflect TestInfo helper mutation',
  mutateSource(
    'specs/header-footer-navigation.spec.ts',
    (source) =>
      `${source}\nfunction reflectTimeout(info: TestInfo) { Reflect.get(info, 'setTimeout')(180_000); }\n`,
  ),
  /Reflect access to Playwright timeout controls is forbidden/,
);

expectSourceMutationRejected(
  'two timeout calls on one line mutation',
  mutateSource(
    'specs/header-footer-navigation.spec.ts',
    insertAfterHeaderTimeout('test.setTimeout(90_000);'),
  ),
  /must contain exactly one direct test\.setTimeout/,
);

expectSourceMutationRejected(
  'conditional allowlisted timeout mutation',
  mutateSource('specs/header-footer-navigation.spec.ts', (source) => {
    const needle = '  test.setTimeout(90_000);';
    assert.equal(source.split(needle).length - 1, 1);
    return source.replace(
      needle,
      '  if (process.env.WIDEN_TIMEOUT) { test.setTimeout(90_000); }',
    );
  }),
  /only the three directly bound|must contain exactly one direct test\.setTimeout/,
);

function resolvedTest(file, title, line = 1) {
  return {
    location: { file: path.join('/tests', file), line },
    retries: 0,
    timeout: DEFAULT_TIMEOUT,
    title,
  };
}

function validResolvedState() {
  const tests = [
    ...ALLOWED_SCOPED_TIMEOUTS.map(({ file, title }, index) =>
      resolvedTest(file, title, index + 1),
    ),
    resolvedTest('specs/site-editor.spec.ts', 'ordinary browser test', 20),
  ];
  return {
    config: {
      configFile: '/tests/playwright.config.ts',
      globalTimeout: 0,
      projects: [{ name: '', retries: 0, timeout: DEFAULT_TIMEOUT }],
      reporter: [
        ['list'],
        ['html', {}],
        [path.join('/tests', 'specs/support/timeout-policy-reporter.cjs')],
      ],
      rootDir: '/tests/specs',
    },
    suite: { allTests: () => tests },
    tests,
  };
}

function expectResolvedMutationRejected(label, mutate, messagePattern) {
  const state = validResolvedState();
  mutate(state);
  const errors = validateResolvedPolicy(state.config, state.suite);
  assert.notEqual(errors.length, 0, `${label} unexpectedly passed`);
  assert.match(
    errors.join('\n'),
    messagePattern,
    `${label} failed ambiguously`,
  );
}

{
  const state = validResolvedState();
  assert.deepEqual(validateResolvedPolicy(state.config, state.suite), []);
}

function withEnvironmentVariable(name, value, inspect) {
  const previous = process.env[name];
  try {
    process.env[name] = value;
    return inspect();
  } finally {
    if (previous === undefined) {
      delete process.env[name];
    } else {
      process.env[name] = previous;
    }
  }
}

for (const name of [
  'PWDEBUG',
  'PW_TEST_REPORTER',
  'PW_TEST_SOURCE_TRANSFORM',
  'PW_TEST_SOURCE_TRANSFORM_SCOPE',
]) {
  withEnvironmentVariable(name, 'unsafe-test-value', () => {
    const state = validResolvedState();
    const errors = validateResolvedPolicy(state.config, state.suite);
    assert.match(
      errors.join('\n'),
      new RegExp(`runtime environment variable ${name} is forbidden`),
      `${name} must be rejected before Playwright can execute tests`,
    );
  });
}

{
  const originalArguments = [...process.argv];
  try {
    process.argv.push('--debug');
    const state = validResolvedState();
    assert.match(
      validateResolvedPolicy(state.config, state.suite).join('\n'),
      /--debug mode is forbidden/,
    );
  } finally {
    process.argv.splice(0, process.argv.length, ...originalArguments);
  }
}

expectResolvedMutationRejected(
  'global timeout mutation',
  ({ config }) => {
    config.globalTimeout = 300_000;
  },
  /globalTimeout must be 0/,
);
expectResolvedMutationRejected(
  'missing timeout policy reporter mutation',
  ({ config }) => {
    config.reporter = [['list'], ['html', {}]];
  },
  /use only the timeout policy reporter or list, html and the final timeout policy reporter for every run/,
);
expectResolvedMutationRejected(
  'reporter after timeout policy mutation',
  ({ config }) => {
    config.reporter.push(['./override-reporter.cjs']);
  },
  /use only the timeout policy reporter or list, html and the final timeout policy reporter for every run/,
);
expectResolvedMutationRejected(
  'project retry mutation',
  ({ config }) => {
    config.projects[0].retries = 1;
  },
  /project retries must be 0/,
);
expectResolvedMutationRejected(
  'project timeout mutation',
  ({ config }) => {
    config.projects[0].timeout = 180_000;
  },
  /project timeout must be/,
);
expectResolvedMutationRejected(
  'describe-level timeout mutation exposed by resolved suite',
  ({ tests }) => {
    tests[3].timeout = 180_000;
  },
  /collection-time timeout must stay/,
);
expectResolvedMutationRejected(
  'test retry mutation',
  ({ tests }) => {
    tests[3].retries = 2;
  },
  /resolved test retries must be 0/,
);
expectResolvedMutationRejected(
  'second project mutation',
  ({ config }) => {
    config.projects.push({
      name: 'bypass',
      retries: 0,
      timeout: DEFAULT_TIMEOUT,
    });
  },
  /exactly one project/,
);
expectResolvedMutationRejected(
  'duplicate allowlisted test mutation',
  ({ tests }) => {
    tests.push({ ...tests[0] });
  },
  /resolved suite (may contain at most one|must contain exactly one) allowlisted test/,
);

console.log('Playwright semantic timeout mutation contract passed.');
