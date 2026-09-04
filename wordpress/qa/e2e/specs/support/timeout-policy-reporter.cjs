'use strict';

const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');

const PLAYWRIGHT_VERSION = '1.54.2';
const BABEL_BUNDLE_HASH =
  'c4db9d9a327ec8021e2e8de7c7a7d80aa0e938f6492d353f8e01e6ffe4626169';
const BABEL_IMPLEMENTATION_HASH =
  '9f33f7e938337c43bd73d5240c129e47a5e6d05f3043fa455859aa76779aebd5';
const DEFAULT_TIMEOUT = 60_000;
const SCOPED_TIMEOUT = 90_000;
const SOURCE_EXTENSIONS = Object.freeze([
  '.ts',
  '.tsx',
  '.js',
  '.jsx',
  '.cts',
  '.mts',
  '.cjs',
  '.mjs',
]);
const POLICY_INFRASTRUCTURE_FILES = new Set([
  'specs/support/timeout-policy-contract.cjs',
  'specs/support/timeout-policy-reporter.cjs',
]);
const PLAYWRIGHT_CONFIG_FILE = 'playwright.config.ts';
const TRUSTED_TSCONFIG_FILE = 'timeout-policy.tsconfig.json';
const TRUSTED_TSCONFIG_SOURCE = '{\n  "compilerOptions": {}\n}\n';
const POLICY_REPORTER_CONFIG_PATH =
  './specs/support/timeout-policy-reporter.cjs';
const REQUIRED_CONFIG_PROPERTIES = new Set([
  'testDir',
  'fullyParallel',
  'workers',
  'timeout',
  'globalTimeout',
  'retries',
  'tsconfig',
  'expect',
  'use',
  'outputDir',
  'reporter',
]);
const ALLOWED_USE_PROPERTIES = new Set([
  'baseURL',
  'browserName',
  'reducedMotion',
  'trace',
  'screenshot',
]);
const ALLOWED_EXPECT_PROPERTIES = new Set(['timeout', 'toHaveScreenshot']);
const ALLOWED_PLAYWRIGHT_TEST_MEMBERS = new Set([
  'afterAll',
  'afterEach',
  'beforeAll',
  'beforeEach',
  'describe',
  'info',
  'setTimeout',
]);
const ALLOWED_TEST_INFO_MEMBERS = new Set([
  'attach',
  'outputPath',
  'setTimeout',
  'title',
]);
const ALLOWED_ENVIRONMENT_VARIABLES = new Set([
  'GAMA_PLAYWRIGHT_RUN',
  'WP_ADMIN_PASSWORD',
  'WP_ADMIN_USER',
  'WP_BASE_URL',
  'WP_EDITOR_PASSWORD',
  'WP_EDITOR_USER',
]);
const FORBIDDEN_PLAYWRIGHT_ENVIRONMENT_VARIABLES = new Set([
  'PWDEBUG',
  'PW_TEST_REPORTER',
  'PW_TEST_SOURCE_TRANSFORM',
  'PW_TEST_SOURCE_TRANSFORM_SCOPE',
]);
const GLOBAL_FUNCTION_CONSTRUCTORS = new Set([
  'Array',
  'ArrayBuffer',
  'AsyncFunction',
  'BigInt',
  'Boolean',
  'DataView',
  'Date',
  'Error',
  'EvalError',
  'Function',
  'Map',
  'Number',
  'Object',
  'Promise',
  'Proxy',
  'RangeError',
  'ReferenceError',
  'RegExp',
  'Set',
  'SharedArrayBuffer',
  'String',
  'Symbol',
  'SyntaxError',
  'TypeError',
  'URIError',
  'WeakMap',
  'WeakSet',
]);
const FORBIDDEN_REFLECTION_PROPERTIES = new Set([
  '__defineGetter__',
  '__defineSetter__',
  '__lookupGetter__',
  '__lookupSetter__',
  '__proto__',
  'callee',
  'caller',
  'constructor',
  'defineProperties',
  'defineProperty',
  'getOwnPropertyDescriptor',
  'getOwnPropertyDescriptors',
  'getOwnPropertyNames',
  'getOwnPropertySymbols',
  'getPrototypeOf',
  'prototype',
  'setPrototypeOf',
]);
const POLICY_NODE_MODULES = new Map([
  [
    'specs/support/timeout-policy-contract.cjs',
    new Set([
      'node:assert/strict',
      'node:child_process',
      'node:fs',
      'node:os',
      'node:path',
    ]),
  ],
  [
    'specs/support/timeout-policy-reporter.cjs',
    new Set(['node:crypto', 'node:fs', 'node:path']),
  ],
  [
    'specs/support/run-playwright.cjs',
    new Set(['node:child_process']),
  ],
]);

const ALLOWED_SCOPED_TIMEOUTS = Object.freeze([
  Object.freeze({
    file: 'specs/global-styles.spec.ts',
    title:
      'keeps the same primitive styles in the editor canvas @global-styles @global-styles-editor-snapshots',
  }),
  Object.freeze({
    file: 'specs/global-styles.spec.ts',
    title:
      'persists an Administrator Global Styles change and reflects it publicly @global-styles @global-styles-admin-persistence',
  }),
  Object.freeze({
    file: 'specs/header-footer-navigation.spec.ts',
    title:
      'lets the disposable Editor transform and save native header navigation through the Site Editor UI @navigation-save',
  }),
]);

let pinnedAstTools;

function sha256(file) {
  return crypto
    .createHash('sha256')
    .update(fs.readFileSync(file))
    .digest('hex');
}

function loadPinnedAstTools() {
  if (pinnedAstTools !== undefined) {
    return pinnedAstTools;
  }

  const packageFile = require.resolve('playwright/package.json');
  const packageRoot = path.dirname(packageFile);
  const packageVersion = JSON.parse(
    fs.readFileSync(packageFile, 'utf8'),
  ).version;
  if (packageVersion !== PLAYWRIGHT_VERSION) {
    throw new Error(
      `Timeout policy requires Playwright ${PLAYWRIGHT_VERSION}; resolved ${String(packageVersion)}.`,
    );
  }

  const bundleFile = path.join(packageRoot, 'lib/transform/babelBundle.js');
  const implementationFile = path.join(
    packageRoot,
    'lib/transform/babelBundleImpl.js',
  );
  if (
    sha256(bundleFile) !== BABEL_BUNDLE_HASH ||
    sha256(implementationFile) !== BABEL_IMPLEMENTATION_HASH
  ) {
    throw new Error(
      'Pinned Playwright AST implementation hash differs; refusing an unreviewed parser.',
    );
  }

  const astTools = require(bundleFile);
  if (
    typeof astTools.babelParse !== 'function' ||
    typeof astTools.traverse !== 'function' ||
    typeof astTools.types?.isCallExpression !== 'function'
  ) {
    throw new Error(
      'Pinned Playwright AST exports differ; timeout policy cannot fail safely.',
    );
  }

  pinnedAstTools = astTools;
  return pinnedAstTools;
}

function normalizePath(file) {
  return file.split(path.sep).join('/');
}

function validateTrustedTsconfig(rootDirectory) {
  const tsconfigFile = path.join(rootDirectory, TRUSTED_TSCONFIG_FILE);
  let metadata;
  try {
    metadata = fs.lstatSync(tsconfigFile);
  } catch {
    throw new Error(
      `Timeout policy requires ${TRUSTED_TSCONFIG_FILE} at the E2E package root.`,
    );
  }
  if (!metadata.isFile() || metadata.isSymbolicLink()) {
    throw new Error(
      `Timeout policy requires ${TRUSTED_TSCONFIG_FILE} to be a regular file.`,
    );
  }
  if (fs.readFileSync(tsconfigFile, 'utf8') !== TRUSTED_TSCONFIG_SOURCE) {
    throw new Error(
      'Timeout policy trusted timeout policy tsconfig must contain exactly the reviewed empty compilerOptions object.',
    );
  }
}

function validatePlaywrightConfigFile(rootDirectory) {
  const configFile = path.join(rootDirectory, PLAYWRIGHT_CONFIG_FILE);
  let metadata;
  try {
    metadata = fs.lstatSync(configFile);
  } catch {
    throw new Error(
      `Timeout policy requires ${PLAYWRIGHT_CONFIG_FILE} at the E2E package root.`,
    );
  }
  if (!metadata.isFile() || metadata.isSymbolicLink()) {
    throw new Error(
      `Timeout policy requires ${PLAYWRIGHT_CONFIG_FILE} to be a regular file.`,
    );
  }
  return configFile;
}

function readSpecSources(rootDirectory) {
  validateTrustedTsconfig(rootDirectory);
  const configFile = validatePlaywrightConfigFile(rootDirectory);
  const specRoot = path.join(rootDirectory, 'specs');
  const entries = [];

  function addSource(absolute) {
    entries.push({
      file: normalizePath(path.relative(rootDirectory, absolute)),
      source: fs.readFileSync(absolute, 'utf8'),
    });
  }

  function visit(directory) {
    for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
      const absolute = path.join(directory, entry.name);
      if (entry.isDirectory()) {
        visit(absolute);
      } else if (entry.isSymbolicLink()) {
        throw new Error(
          `Timeout policy refuses symbolic links below ${specRoot}: ${absolute}.`,
        );
      } else if (
        entry.isFile() &&
        entry.name.toLowerCase() === 'package.json'
      ) {
        throw new Error(
          `Timeout policy: package.json is forbidden below the timeout-controlled specs directory: ${absolute}.`,
        );
      } else if (
        entry.isFile() &&
        SOURCE_EXTENSIONS.includes(path.extname(entry.name).toLowerCase())
      ) {
        addSource(absolute);
      } else if (
        entry.isFile() &&
        path.extname(entry.name).toLowerCase() === '.png'
      ) {
        continue;
      } else {
        throw new Error(
          `Timeout policy: only source files and PNG snapshot assets may exist below the timeout-controlled specs directory: ${absolute}.`,
        );
      }
    }
  }

  addSource(configFile);
  visit(specRoot);
  return entries.sort((left, right) => left.file.localeCompare(right.file));
}

function isSpecFile(file) {
  return /\.spec\.(?:[cm]?[jt]sx?)$/.test(file);
}

function isPolicyInfrastructure(file) {
  return POLICY_INFRASTRUCTURE_FILES.has(file);
}

function localModuleCandidates(importingFile, specifier) {
  const base = path.posix.normalize(
    path.posix.join(path.posix.dirname(importingFile), specifier),
  );
  const candidates = [base];
  if (!SOURCE_EXTENSIONS.includes(path.posix.extname(base).toLowerCase())) {
    for (const extension of SOURCE_EXTENSIONS) {
      candidates.push(`${base}${extension}`);
      candidates.push(path.posix.join(base, `index${extension}`));
    }
  }
  return candidates;
}

function location(file, node) {
  const start = node.loc?.start;
  return start === undefined
    ? file
    : `${file}:${start.line}:${start.column + 1}`;
}

function unwrapExpression(expressionPath) {
  let current = expressionPath;
  while (
    current?.isTSAsExpression?.() ||
    current?.isTSTypeAssertion?.() ||
    current?.isTSNonNullExpression?.() ||
    current?.isParenthesizedExpression?.()
  ) {
    current = current.get('expression');
  }
  return current;
}

function constantString(expressionPath, seenBindings = new Set()) {
  const current = unwrapExpression(expressionPath);
  if (current?.isStringLiteral?.()) {
    return current.node.value;
  }
  if (current?.isTemplateLiteral?.() && current.node.expressions.length === 0) {
    return current.node.quasis[0].value.cooked;
  }
  if (current?.isBinaryExpression?.({ operator: '+' })) {
    const left = constantString(current.get('left'), seenBindings);
    const right = constantString(current.get('right'), seenBindings);
    return left === undefined || right === undefined ? undefined : left + right;
  }
  if (current?.isIdentifier?.()) {
    const binding = current.scope.getBinding(current.node.name);
    if (
      binding === undefined ||
      seenBindings.has(binding) ||
      !binding.constant ||
      !binding.path.isVariableDeclarator()
    ) {
      return undefined;
    }
    const init = binding.path.get('init');
    if (!init?.node) {
      return undefined;
    }
    const nextSeen = new Set(seenBindings);
    nextSeen.add(binding);
    return constantString(init, nextSeen);
  }
  return undefined;
}

function objectPropertyName(propertyPath) {
  if (!propertyPath?.isObjectProperty?.() || propertyPath.node.computed) {
    return undefined;
  }
  const key = propertyPath.get('key');
  if (key.isIdentifier()) {
    return key.node.name;
  }
  if (key.isStringLiteral()) {
    return key.node.value;
  }
  return undefined;
}

function validateClosedObjectProperties(
  file,
  label,
  objectPath,
  allowedProperties,
  requiredProperties,
  errors,
) {
  if (!objectPath?.isObjectExpression?.()) {
    errors.push(`${file}: ${label} must be a direct object literal.`);
    return new Map();
  }

  const properties = new Map();
  for (const property of objectPath.get('properties')) {
    const name = objectPropertyName(property);
    if (name === undefined) {
      errors.push(
        `${location(file, property.node)}: ${label} may not use spreads, computed keys or methods.`,
      );
      continue;
    }
    if (!allowedProperties.has(name)) {
      errors.push(
        `${location(file, property.node)}: ${label} may not configure ${name}.`,
      );
      continue;
    }
    if (properties.has(name)) {
      errors.push(
        `${location(file, property.node)}: ${label} may not define ${name} more than once.`,
      );
      continue;
    }
    properties.set(name, property.get('value'));
  }
  for (const name of requiredProperties) {
    if (!properties.has(name)) {
      errors.push(`${file}: ${label} must define ${name}.`);
    }
  }
  return properties;
}

function hasNumericValue(propertyPath, expected) {
  const value = unwrapExpression(propertyPath);
  return value?.isNumericLiteral?.() && value.node.value === expected;
}

function hasBooleanValue(propertyPath, expected) {
  const value = unwrapExpression(propertyPath);
  return value?.isBooleanLiteral?.() && value.node.value === expected;
}

function hasStringValue(propertyPath, expected) {
  const value = unwrapExpression(propertyPath);
  return value?.isStringLiteral?.({ value: expected });
}

function hasReporterTuple(entryPath, reporterName, argumentCount) {
  if (!entryPath?.isArrayExpression?.()) {
    return false;
  }
  const values = entryPath.get('elements');
  return (
    values.length === argumentCount && hasStringValue(values[0], reporterName)
  );
}

function expressionCanYieldFunction(expressionPath, seenBindings = new Set()) {
  const current = unwrapExpression(expressionPath);
  if (!current?.node) {
    return false;
  }
  if (
    current.isArrowFunctionExpression?.() ||
    current.isFunctionExpression?.() ||
    current.isClassExpression?.()
  ) {
    return true;
  }
  if (current.isIdentifier?.()) {
    const binding = current.scope.getBinding(current.node.name);
    if (binding === undefined) {
      return GLOBAL_FUNCTION_CONSTRUCTORS.has(current.node.name);
    }
    if (seenBindings.has(binding)) {
      return false;
    }
    if (binding.path.isFunctionDeclaration?.() || binding.path.isClassDeclaration?.()) {
      return true;
    }
    if (!binding.constant || !binding.path.isVariableDeclarator?.()) {
      return false;
    }
    const init = binding.path.get('init');
    if (!init?.node) {
      return false;
    }
    const nextSeen = new Set(seenBindings);
    nextSeen.add(binding);
    return expressionCanYieldFunction(init, nextSeen);
  }
  if (current.isAwaitExpression?.()) {
    return expressionCanYieldFunction(current.get('argument'), seenBindings);
  }
  if (current.isCallExpression?.() || current.isOptionalCallExpression?.()) {
    const callee = unwrapExpression(current.get('callee'));
    if (
      (callee?.isMemberExpression?.() ||
        callee?.isOptionalMemberExpression?.()) &&
      memberPropertyName(callee) === 'bind' &&
      expressionCanYieldFunction(callee.get('object'), seenBindings)
    ) {
      return true;
    }
    return false;
  }
  if (current.isMemberExpression?.() || current.isOptionalMemberExpression?.()) {
    const objectPath = current.get('object');
    const propertyName = memberPropertyName(current);
    if (
      propertyName === 'bind' &&
      expressionCanYieldFunction(objectPath, seenBindings)
    ) {
      return true;
    }
    if (
      current.node.computed &&
      current.get('property').isNumericLiteral?.() &&
      objectPath.isArrayExpression?.()
    ) {
      const member = objectPath.get('elements')[
        current.get('property').node.value
      ];
      return expressionCanYieldFunction(member, seenBindings);
    }
    if (
      propertyName !== undefined &&
      objectPath.isObjectExpression?.()
    ) {
      const property = objectPath
        .get('properties')
        .find((candidate) => objectPropertyName(candidate) === propertyName);
      return property === undefined
        ? false
        : expressionCanYieldFunction(property.get('value'), seenBindings);
    }
  }
  return false;
}

function validatePlaywrightConfigShape(file, programPath, errors) {
  if (file !== PLAYWRIGHT_CONFIG_FILE) {
    return;
  }

  let defineConfigBinding;
  for (const statement of programPath.get('body')) {
    if (
      !statement.isImportDeclaration() ||
      statement.node.source.value !== '@playwright/test'
    ) {
      continue;
    }
    for (const specifier of statement.get('specifiers')) {
      if (
        specifier.isImportSpecifier() &&
        (specifier.node.imported.name ?? specifier.node.imported.value) ===
          'defineConfig'
      ) {
        defineConfigBinding = programPath.scope.getBinding(
          specifier.node.local.name,
        );
      }
    }
  }
  if (defineConfigBinding === undefined) {
    errors.push(`${file}: must directly import defineConfig from @playwright/test.`);
    return;
  }

  const configCalls = [];
  programPath.traverse({
    CallExpression(callPath) {
      const callee = unwrapExpression(callPath.get('callee'));
      if (
        callee?.isIdentifier?.() &&
        callee.scope.getBinding(callee.node.name) === defineConfigBinding
      ) {
        configCalls.push(callPath);
      }
    },
  });
  if (configCalls.length !== 1) {
    errors.push(`${file}: must call defineConfig exactly once.`);
    return;
  }

  const configCall = configCalls[0];
  const exportDeclaration = configCall.parentPath;
  if (
    !exportDeclaration?.isExportDefaultDeclaration?.() ||
    exportDeclaration.get('declaration').node !== configCall.node
  ) {
    errors.push(
      `${file}: the only defineConfig call must be the direct export default value.`,
    );
    return;
  }

  const argumentsPaths = configCall.get('arguments');
  if (argumentsPaths.length !== 1) {
    errors.push(`${file}: defineConfig must receive exactly one configuration object.`);
    return;
  }
  const configProperties = validateClosedObjectProperties(
    file,
    'Playwright config',
    argumentsPaths[0],
    REQUIRED_CONFIG_PROPERTIES,
    REQUIRED_CONFIG_PROPERTIES,
    errors,
  );

  const requiredValues = [
    ['testDir', './specs', hasStringValue],
    ['fullyParallel', false, hasBooleanValue],
    ['workers', 1, hasNumericValue],
    ['timeout', DEFAULT_TIMEOUT, hasNumericValue],
    ['globalTimeout', 0, hasNumericValue],
    ['retries', 0, hasNumericValue],
    ['tsconfig', `./${TRUSTED_TSCONFIG_FILE}`, hasStringValue],
  ];
  for (const [name, expected, validator] of requiredValues) {
    const property = configProperties.get(name);
    if (property !== undefined && !validator(property, expected)) {
      errors.push(
        `${file}: Playwright config ${name} must be the literal ${String(expected)}.`,
      );
    }
  }

  const expectProperties = validateClosedObjectProperties(
    file,
    'Playwright expect config',
    configProperties.get('expect'),
    ALLOWED_EXPECT_PROPERTIES,
    ALLOWED_EXPECT_PROPERTIES,
    errors,
  );
  if (
    expectProperties.has('timeout') &&
    !hasNumericValue(expectProperties.get('timeout'), 15_000)
  ) {
    errors.push(`${file}: Playwright expect timeout must be the literal 15000.`);
  }

  const useProperties = validateClosedObjectProperties(
    file,
    'Playwright use config',
    configProperties.get('use'),
    ALLOWED_USE_PROPERTIES,
    ALLOWED_USE_PROPERTIES,
    errors,
  );
  for (const [name, expected] of [
    ['browserName', 'chromium'],
    ['reducedMotion', 'reduce'],
    ['trace', 'retain-on-failure'],
    ['screenshot', 'only-on-failure'],
  ]) {
    if (
      useProperties.has(name) &&
      !hasStringValue(useProperties.get(name), expected)
    ) {
      errors.push(
        `${file}: Playwright use ${name} must be the literal ${expected}.`,
      );
    }
  }

  const reporter = configProperties.get('reporter');
  const reporterEntries = reporter?.isArrayExpression?.()
    ? reporter.get('elements')
    : [];
  if (
    !reporter?.isArrayExpression?.() ||
    reporterEntries.length !== 3 ||
    !hasReporterTuple(reporterEntries[0], 'list', 1) ||
    !hasReporterTuple(reporterEntries[1], 'html', 2) ||
    !hasReporterTuple(reporterEntries[2], POLICY_REPORTER_CONFIG_PATH, 1)
  ) {
    errors.push(
      `${file}: Playwright config reporter must be exactly list, html, then ${POLICY_REPORTER_CONFIG_PATH} so the policy result is final.`,
    );
  }
}

function memberPropertyName(memberPath) {
  if (!memberPath.node.computed && memberPath.get('property').isIdentifier()) {
    return memberPath.node.property.name;
  }
  if (memberPath.node.computed && memberPath.get('property').isNumericLiteral()) {
    return memberPath.node.property.value;
  }
  return constantString(memberPath.get('property'));
}

function isDirectBindingReference(expressionPath, binding) {
  const current = unwrapExpression(expressionPath);
  return (
    current?.isIdentifier?.() &&
    current.scope.getBinding(current.node.name) === binding
  );
}

function expressionDerivesFromBinding(
  expressionPath,
  targetBindings,
  seenBindings = new Set(),
) {
  const current = unwrapExpression(expressionPath);
  if (!current?.node) {
    return false;
  }
  if (current.isIdentifier()) {
    const binding = current.scope.getBinding(current.node.name);
    if (binding === undefined) {
      return false;
    }
    if (targetBindings.has(binding)) {
      return true;
    }
    if (
      seenBindings.has(binding) ||
      !binding.constant ||
      !binding.path.isVariableDeclarator()
    ) {
      return false;
    }
    const init = binding.path.get('init');
    if (!init?.node) {
      return false;
    }
    const nextSeen = new Set(seenBindings);
    nextSeen.add(binding);
    return expressionDerivesFromBinding(init, targetBindings, nextSeen);
  }
  if (current.isMemberExpression() || current.isOptionalMemberExpression()) {
    return expressionDerivesFromBinding(
      current.get('object'),
      targetBindings,
      seenBindings,
    );
  }
  return false;
}

function expressionDerivesFromTestInfo(
  expressionPath,
  testBindings,
  testInfoBindings,
  seenBindings = new Set(),
) {
  const current = unwrapExpression(expressionPath);
  if (!current?.node) {
    return false;
  }
  if (expressionDerivesFromBinding(current, testInfoBindings)) {
    return true;
  }
  if (current.isIdentifier()) {
    const binding = current.scope.getBinding(current.node.name);
    if (
      binding === undefined ||
      seenBindings.has(binding) ||
      !binding.constant ||
      !binding.path.isVariableDeclarator()
    ) {
      return false;
    }
    const init = binding.path.get('init');
    if (!init?.node) {
      return false;
    }
    const nextSeen = new Set(seenBindings);
    nextSeen.add(binding);
    return expressionDerivesFromTestInfo(
      init,
      testBindings,
      testInfoBindings,
      nextSeen,
    );
  }
  if (current.isMemberExpression() || current.isOptionalMemberExpression()) {
    return expressionDerivesFromTestInfo(
      current.get('object'),
      testBindings,
      testInfoBindings,
      seenBindings,
    );
  }
  if (current.isCallExpression() || current.isOptionalCallExpression()) {
    const callee = unwrapExpression(current.get('callee'));
    return (
      (callee?.isMemberExpression?.() ||
        callee?.isOptionalMemberExpression?.()) &&
      memberPropertyName(callee) === 'info' &&
      expressionDerivesFromBinding(callee.get('object'), testBindings)
    );
  }
  return false;
}

function testKey(file, title) {
  return `${file}\u0000${title}`;
}

function validateSpecSources(sourceEntries) {
  const { babelParse, traverse } = loadPinnedAstTools();
  const errors = [];
  const sourceFiles = new Set();
  for (const { file } of sourceEntries) {
    if (sourceFiles.has(file)) {
      errors.push(`${file}: duplicate executable source entry.`);
    }
    sourceFiles.add(file);
  }
  if (
    sourceEntries.filter(({ file }) => file === PLAYWRIGHT_CONFIG_FILE).length !==
    1
  ) {
    errors.push(
      `Timeout policy requires exactly one ${PLAYWRIGHT_CONFIG_FILE} source entry.`,
    );
  }
  const scopedCallCounts = new Map(
    ALLOWED_SCOPED_TIMEOUTS.map(({ file, title }) => [testKey(file, title), 0]),
  );
  const definitionCounts = new Map(
    ALLOWED_SCOPED_TIMEOUTS.map(({ file, title }) => [testKey(file, title), 0]),
  );

  function validateModuleSpecifier(file, node, specifier, kind) {
    if (specifier.startsWith('./') || specifier.startsWith('../')) {
      if (
        !localModuleCandidates(file, specifier).some((candidate) =>
          sourceFiles.has(candidate),
        )
      ) {
        errors.push(
          `${location(file, node)}: local ${kind} does not resolve to a scanned executable module: ${specifier}.`,
        );
      }
      return;
    }
    if (specifier === '@playwright/test' && kind === 'import') {
      return;
    }
    if (POLICY_NODE_MODULES.get(file)?.has(specifier)) {
      return;
    }
    errors.push(
      `${location(file, node)}: external ${kind} is forbidden in timeout-controlled modules: ${specifier}.`,
    );
  }

  for (const { file, source } of sourceEntries) {
    let ast;
    try {
      ast = babelParse(source, file);
    } catch (error) {
      errors.push(`${file}: TypeScript parse failed: ${error.message}`);
      continue;
    }

    let programPath;
    traverse(ast, {
      Program(candidate) {
        programPath = candidate;
        candidate.stop();
      },
    });
    if (programPath === undefined) {
      errors.push(`${file}: AST did not contain a Program node.`);
      continue;
    }

    validatePlaywrightConfigShape(file, programPath, errors);

    const testImports = [];
    const testInfoTypeNames = new Set();
    for (const statement of programPath.get('body')) {
      if (statement.isExportNamedDeclaration() || statement.isExportAllDeclaration()) {
        if (statement.node.source != null) {
          const specifier = statement.node.source.value;
          validateModuleSpecifier(file, statement.node.source, specifier, 're-export');
          if (specifier === '@playwright/test') {
            errors.push(
              `${location(file, statement.node)}: re-exporting Playwright is forbidden.`,
            );
          }
        }
      }
      if (!statement.isImportDeclaration()) {
        continue;
      }
      const importedModule = statement.node.source.value;
      validateModuleSpecifier(file, statement.node.source, importedModule, 'import');
      if (importedModule !== '@playwright/test') {
        continue;
      }
      for (const specifier of statement.get('specifiers')) {
        if (
          specifier.isImportDefaultSpecifier() ||
          specifier.isImportNamespaceSpecifier()
        ) {
          errors.push(
            `${location(file, specifier.node)}: namespace or default Playwright imports are forbidden.`,
          );
          continue;
        }
        if (
          specifier.isImportSpecifier() &&
          (specifier.node.imported.name ?? specifier.node.imported.value) ===
            'test'
        ) {
          testImports.push(specifier);
        } else if (
          specifier.isImportSpecifier() &&
          (specifier.node.imported.name ?? specifier.node.imported.value) ===
            'TestInfo'
        ) {
          testInfoTypeNames.add(specifier.node.local.name);
        }
      }
    }

    function isGlobalIdentifier(identifierPath, name) {
      return (
        identifierPath?.isIdentifier?.({ name }) &&
        identifierPath.scope.getBinding(name) === undefined
      );
    }

    function isDirectProcessEnvironment(expressionPath) {
      const current = unwrapExpression(expressionPath);
      return (
        (current?.isMemberExpression?.() ||
          current?.isOptionalMemberExpression?.()) &&
        memberPropertyName(current) === 'env' &&
        isGlobalIdentifier(current.get('object'), 'process')
      );
    }

    function isApprovedEnvironmentRead(environmentPath) {
      const parent = environmentPath.parentPath;
      return (
        (parent?.isMemberExpression?.() ||
          parent?.isOptionalMemberExpression?.()) &&
        parent.get('object').node === environmentPath.node &&
        !environmentPath.node.computed &&
        !environmentPath.node.optional &&
        !parent.node.computed &&
        !parent.node.optional &&
        ALLOWED_ENVIRONMENT_VARIABLES.has(memberPropertyName(parent))
      );
    }

    function expressionDerivesFromProcessEnvironment(
      expressionPath,
      seenBindings = new Set(),
    ) {
      const current = unwrapExpression(expressionPath);
      if (!current?.node) {
        return false;
      }
      if (isDirectProcessEnvironment(current)) {
        return true;
      }
      if (
        current.isMemberExpression?.() ||
        current.isOptionalMemberExpression?.()
      ) {
        return expressionDerivesFromProcessEnvironment(
          current.get('object'),
          seenBindings,
        );
      }
      if (!current.isIdentifier?.()) {
        return false;
      }
      const binding = current.scope.getBinding(current.node.name);
      if (
        binding === undefined ||
        seenBindings.has(binding) ||
        !binding.constant ||
        !binding.path.isVariableDeclarator()
      ) {
        return false;
      }
      const init = binding.path.get('init');
      if (!init?.node) {
        return false;
      }
      const nextSeen = new Set(seenBindings);
      nextSeen.add(binding);
      return expressionDerivesFromProcessEnvironment(init, nextSeen);
    }

    function assignmentTargetDerivesFromProcessEnvironment(targetPath) {
      const current = unwrapExpression(targetPath);
      if (!current?.node) {
        return false;
      }
      if (expressionDerivesFromProcessEnvironment(current)) {
        return true;
      }
      if (current.isObjectPattern?.() || current.isObjectExpression?.()) {
        return current.get('properties').some((propertyPath) => {
          if (propertyPath.isRestElement?.()) {
            return assignmentTargetDerivesFromProcessEnvironment(
              propertyPath.get('argument'),
            );
          }
          return (
            propertyPath.isObjectProperty?.() &&
            assignmentTargetDerivesFromProcessEnvironment(
              propertyPath.get('value'),
            )
          );
        });
      }
      if (current.isArrayPattern?.() || current.isArrayExpression?.()) {
        return current
          .get('elements')
          .some((elementPath) =>
            assignmentTargetDerivesFromProcessEnvironment(elementPath),
          );
      }
      if (current.isAssignmentPattern?.() || current.isRestElement?.()) {
        return assignmentTargetDerivesFromProcessEnvironment(
          current.get(current.isAssignmentPattern() ? 'left' : 'argument'),
        );
      }
      return false;
    }

    function isPinnedAstBundleLoad(callPath) {
      if (file !== 'specs/support/timeout-policy-reporter.cjs') {
        return false;
      }
      const args = callPath.get('arguments');
      if (args.length !== 1 || !args[0].isIdentifier({ name: 'bundleFile' })) {
        return false;
      }
      const binding = args[0].scope.getBinding('bundleFile');
      if (!binding?.constant || !binding.path.isVariableDeclarator()) {
        return false;
      }
      const init = binding.path.get('init');
      if (!init?.isCallExpression?.()) {
        return false;
      }
      const callee = init.get('callee');
      const initArgs = init.get('arguments');
      return (
        callee.isMemberExpression() &&
        !callee.node.computed &&
        callee.get('object').isIdentifier({ name: 'path' }) &&
        callee.get('property').isIdentifier({ name: 'join' }) &&
        initArgs.length === 2 &&
        initArgs[0].isIdentifier({ name: 'packageRoot' }) &&
        initArgs[1].isStringLiteral({
          value: 'lib/transform/babelBundle.js',
        })
      );
    }

    function inspectModuleLoad(callPath) {
      const callee = unwrapExpression(callPath.get('callee'));
      const args = callPath.get('arguments');
      if (callee?.node?.type === 'Import') {
        errors.push(
          `${location(file, callPath.node)}: dynamic import is forbidden in timeout-controlled modules.`,
        );
        return;
      }
      if (isGlobalIdentifier(callee, 'eval') || isGlobalIdentifier(callee, 'Function')) {
        errors.push(
          `${location(file, callPath.node)}: dynamic code execution is forbidden in timeout-controlled modules.`,
        );
        return;
      }
      if (isGlobalIdentifier(callee, 'require')) {
        if (args.length !== 1) {
          errors.push(
            `${location(file, callPath.node)}: indirect module loading is forbidden.`,
          );
          return;
        }
        const specifier = constantString(args[0]);
        if (specifier === undefined) {
          if (!isPinnedAstBundleLoad(callPath)) {
            errors.push(
              `${location(file, callPath.node)}: indirect module loading is forbidden.`,
            );
          }
          return;
        }
        if (specifier === '@playwright/test') {
          errors.push(
            `${location(file, callPath.node)}: CommonJS Playwright imports are forbidden.`,
          );
          return;
        }
        validateModuleSpecifier(file, callPath.node, specifier, 'require');
        return;
      }
      if (
        !(
          callee?.isMemberExpression?.() ||
          callee?.isOptionalMemberExpression?.()
        ) ||
        memberPropertyName(callee) !== 'resolve' ||
        !isGlobalIdentifier(callee.get('object'), 'require')
      ) {
        return;
      }
      const specifier = args.length === 1 ? constantString(args[0]) : undefined;
      if (
        file !== 'specs/support/timeout-policy-reporter.cjs' ||
        specifier !== 'playwright/package.json'
      ) {
        errors.push(
          `${location(file, callPath.node)}: indirect module loading is forbidden.`,
        );
      }
    }

    function inspectDangerousMember(memberPath) {
      const propertyName = memberPropertyName(memberPath);
      const objectPath = memberPath.get('object');
      if (!isPolicyInfrastructure(file) && propertyName === undefined) {
        errors.push(
          `${location(file, memberPath.node)}: unknown computed property access is forbidden in timeout-controlled modules.`,
        );
        return;
      }
      if (
        !isPolicyInfrastructure(file) &&
        isDirectProcessEnvironment(memberPath) &&
        !isApprovedEnvironmentRead(memberPath)
      ) {
        errors.push(
          `${location(file, memberPath.node)}: process.env may only directly read allowlisted variables.`,
        );
        return;
      }
      if (
        isGlobalIdentifier(objectPath, 'module') &&
        propertyName !== 'exports'
      ) {
        errors.push(
          `${location(file, memberPath.node)}: Node module loader access is forbidden.`,
        );
        return;
      }
      if (
        isGlobalIdentifier(objectPath, 'process') &&
        (memberPath.node.computed ||
          memberPath.node.optional ||
          !['env', 'argv', 'exitCode'].includes(propertyName))
      ) {
        errors.push(
          `${location(file, memberPath.node)}: indirect module loading is forbidden.`,
        );
        return;
      }
      if (
        propertyName === undefined &&
        expressionCanYieldFunction(objectPath)
      ) {
        errors.push(
          `${location(file, memberPath.node)}: dynamic access to a function or class constructor is forbidden.`,
        );
        return;
      }
      if (
        FORBIDDEN_REFLECTION_PROPERTIES.has(propertyName) ||
        ['eval', 'Function', 'require'].includes(propertyName)
      ) {
        errors.push(
          `${location(file, memberPath.node)}: dynamic code execution or indirect module loading is forbidden.`,
        );
        return;
      }
      if (
        ['binding', 'getBuiltinModule', 'mainModule'].includes(propertyName) &&
        memberPath.get('object').isIdentifier({ name: 'process' })
      ) {
        errors.push(
          `${location(file, memberPath.node)}: indirect module loading is forbidden.`,
        );
      }
    }

    programPath.traverse({
      enter(candidate) {
        if (candidate.node.type === 'Import') {
          errors.push(
            `${location(file, candidate.node)}: dynamic import is forbidden in timeout-controlled modules.`,
          );
        }
        if (candidate.node.type === 'TSImportEqualsDeclaration') {
          errors.push(
            `${location(file, candidate.node)}: TypeScript import assignments are forbidden in timeout-controlled modules.`,
          );
        }
      },
      CallExpression: inspectModuleLoad,
      OptionalCallExpression: inspectModuleLoad,
      NewExpression(callPath) {
        const callee = unwrapExpression(callPath.get('callee'));
        if (isGlobalIdentifier(callee, 'Function')) {
          errors.push(
            `${location(file, callPath.node)}: dynamic code execution is forbidden in timeout-controlled modules.`,
          );
        }
      },
      AssignmentExpression(assignmentPath) {
        if (
          !isPolicyInfrastructure(file) &&
          assignmentTargetDerivesFromProcessEnvironment(
            assignmentPath.get('left'),
          )
        ) {
          errors.push(
            `${location(file, assignmentPath.node)}: environment state mutation is forbidden.`,
          );
        }
      },
      UpdateExpression(updatePath) {
        if (
          !isPolicyInfrastructure(file) &&
          assignmentTargetDerivesFromProcessEnvironment(
            updatePath.get('argument'),
          )
        ) {
          errors.push(
            `${location(file, updatePath.node)}: environment state mutation is forbidden.`,
          );
        }
      },
      UnaryExpression(unaryPath) {
        if (
          !isPolicyInfrastructure(file) &&
          unaryPath.node.operator === 'delete' &&
          assignmentTargetDerivesFromProcessEnvironment(
            unaryPath.get('argument'),
          )
        ) {
          errors.push(
            `${location(file, unaryPath.node)}: environment state mutation is forbidden.`,
          );
        }
      },
      MemberExpression: inspectDangerousMember,
      OptionalMemberExpression: inspectDangerousMember,
      ReferencedIdentifier(identifierPath) {
        const name = identifierPath.node.name;
        const parent = identifierPath.parentPath;
        if (name === 'arguments') {
          errors.push(
            `${location(file, identifierPath.node)}: implicit arguments is forbidden in timeout-controlled modules.`,
          );
          return;
        }
        if (
          name === 'module' &&
          identifierPath.scope.getBinding(name) === undefined
        ) {
          const isStaticModuleExports =
            (parent?.isMemberExpression?.() ||
              parent?.isOptionalMemberExpression?.()) &&
            parent.get('object').node === identifierPath.node &&
            memberPropertyName(parent) === 'exports';
          if (!isStaticModuleExports) {
            errors.push(
              `${location(file, identifierPath.node)}: Node module loader access is forbidden.`,
            );
          }
          return;
        }
        if (
          ['global', 'globalThis', 'Reflect'].includes(name) &&
          identifierPath.scope.getBinding(name) === undefined
        ) {
          errors.push(
            `${location(file, identifierPath.node)}: dynamic code execution or indirect module loading is forbidden.`,
          );
          return;
        }
        if (
          name === 'process' &&
          identifierPath.scope.getBinding(name) === undefined
        ) {
        const isApprovedProcessProperty =
          (parent?.isMemberExpression?.() ||
            parent?.isOptionalMemberExpression?.()) &&
            parent.get('object').node === identifierPath.node &&
            !parent.node.computed &&
            !parent.node.optional &&
            ['env', 'argv', 'exitCode'].includes(memberPropertyName(parent));
          if (!isApprovedProcessProperty) {
            errors.push(
              `${location(file, identifierPath.node)}: indirect module loading is forbidden.`,
            );
          }
          return;
        }
        if (
          !['eval', 'Function', 'require'].includes(name) ||
          identifierPath.scope.getBinding(name) !== undefined
        ) {
          return;
        }
        const isDirectCall =
          (parent?.isCallExpression?.() || parent?.isOptionalCallExpression?.()) &&
          parent.get('callee').node === identifierPath.node;
        const isDirectResolve =
          parent?.isMemberExpression?.() &&
          parent.get('object').node === identifierPath.node &&
          memberPropertyName(parent) === 'resolve' &&
          parent.parentPath?.isCallExpression?.() &&
          parent.parentPath.get('callee').node === parent.node;
        if (name === 'require' && (isDirectCall || isDirectResolve)) {
          return;
        }
        errors.push(
          `${location(file, identifierPath.node)}: ${
            name === 'require'
              ? 'indirect module loading'
              : 'dynamic code execution'
          } is forbidden.`,
        );
      },
    });

    if (testImports.length > 1 || (isSpecFile(file) && testImports.length !== 1)) {
      errors.push(
        `${file}: expected exactly one named Playwright test import.`,
      );
      continue;
    }
    if (testImports.length === 0) {
      continue;
    }
    const testImport = testImports[0];
    if (testImport.node.local.name !== 'test') {
      errors.push(`${file}: aliasing the Playwright test import is forbidden.`);
    }
    const testBinding = programPath.scope.getBinding(
      testImport.node.local.name,
    );
    if (testBinding === undefined) {
      errors.push(`${file}: Playwright test import has no lexical binding.`);
      continue;
    }
    const testBindings = new Set([testBinding]);
    const testInfoBindings = new Set();
    const definitions = [];
    const callPaths = [];

    function isExplicitlyTypedTestInfoParameter(parameter) {
      if (
        !parameter?.isIdentifier?.() ||
        parameter.node.typeAnnotation == null
      ) {
        return false;
      }
      const annotation = parameter.node.typeAnnotation.typeAnnotation;
      return (
        annotation?.type === 'TSTypeReference' &&
        annotation.typeName?.type === 'Identifier' &&
        testInfoTypeNames.has(annotation.typeName.name)
      );
    }

    function localFunctionForCall(callPath) {
      const calleePath = unwrapExpression(callPath.get('callee'));
      if (!calleePath?.isIdentifier?.()) {
        return undefined;
      }
      const calleeBinding = calleePath.scope.getBinding(calleePath.node.name);
      if (calleeBinding?.path.isFunctionDeclaration()) {
        return calleeBinding.path;
      }
      if (calleeBinding?.path.isVariableDeclarator()) {
        const init = calleeBinding.path.get('init');
        if (
          init?.isFunctionExpression?.() ||
          init?.isArrowFunctionExpression?.()
        ) {
          return init;
        }
      }
      return undefined;
    }

    function isDirectTestInfoCall(callPath) {
      const calleePath = unwrapExpression(callPath.get('callee'));
      return (
        (calleePath?.isMemberExpression?.() ||
          calleePath?.isOptionalMemberExpression?.()) &&
        memberPropertyName(calleePath) === 'info' &&
        isDirectBindingReference(calleePath.get('object'), testBinding)
      );
    }

    function isDirectTestInfoSource(expressionPath) {
      const current = unwrapExpression(expressionPath);
      if (current?.isIdentifier?.()) {
        const binding = current.scope.getBinding(current.node.name);
        return binding !== undefined && testInfoBindings.has(binding);
      }
      return (
        (current?.isCallExpression?.() ||
          current?.isOptionalCallExpression?.()) &&
        isDirectTestInfoCall(current)
      );
    }

    function registerTestInfoParameter(callbackPath) {
      const parameters = callbackPath.get('params');
      if (parameters.length > 2) {
        errors.push(
          `${location(file, callbackPath.node)}: Playwright test and hook callbacks may declare at most two parameters.`,
        );
        return;
      }
      const firstParameter = parameters[0];
      if (
        firstParameter !== undefined &&
        !firstParameter.isIdentifier?.() &&
        !firstParameter.isObjectPattern?.()
      ) {
        errors.push(
          `${location(file, firstParameter.node)}: the first Playwright test or hook callback parameter must be a fixture identifier or object pattern.`,
        );
        return;
      }
      const secondParameter = parameters[1];
      if (secondParameter === undefined) {
        return;
      }
      if (!secondParameter.isIdentifier?.()) {
        errors.push(
          `${location(file, secondParameter.node)}: the second Playwright test or hook callback parameter must be a bare TestInfo identifier.`,
        );
        return;
      }
      const binding = callbackPath.scope.getBinding(secondParameter.node.name);
      if (binding !== undefined) {
        testInfoBindings.add(binding);
      }
    }

    programPath.traverse({
      CallExpression(callPath) {
        callPaths.push(callPath);
        const calleePath = unwrapExpression(callPath.get('callee'));
        const callArguments = callPath.get('arguments');
        if (
          calleePath?.isIdentifier?.({ name: 'require' }) &&
          calleePath.scope.getBinding('require') === undefined &&
          callArguments.length === 1 &&
          constantString(callArguments[0]) === '@playwright/test'
        ) {
          errors.push(
            `${location(file, callPath.node)}: CommonJS Playwright imports are forbidden.`,
          );
        }
        const directTestCall = isDirectBindingReference(
          calleePath,
          testBinding,
        );
        const testHookCall =
          (calleePath?.isMemberExpression?.() ||
            calleePath?.isOptionalMemberExpression?.()) &&
          isDirectBindingReference(calleePath.get('object'), testBinding) &&
          ['beforeEach', 'afterEach', 'beforeAll', 'afterAll'].includes(
            memberPropertyName(calleePath),
        );
        const argumentsPaths = callPath.get('arguments');
        const callbackPath = argumentsPaths.at(-1);
        if (directTestCall || testHookCall) {
          if (!callbackPath?.isArrowFunctionExpression?.()) {
            errors.push(
              `${location(file, callPath.node)}: Playwright test and hook callbacks must be inline ArrowFunctionExpression values.`,
            );
            return;
          }
          registerTestInfoParameter(callbackPath);
        }
        if (!directTestCall) {
          return;
        }
        const titlePath = argumentsPaths[0];
        if (
          !titlePath?.isStringLiteral?.() ||
          !callbackPath?.isArrowFunctionExpression?.()
        ) {
          return;
        }
        const definition = {
          callbackPath,
          file,
          title: titlePath.node.value,
        };
        definitions.push(definition);
        const key = testKey(file, definition.title);
        if (definitionCounts.has(key)) {
          definitionCounts.set(key, definitionCounts.get(key) + 1);
        }
      },
      Function(functionPath) {
        for (const parameter of functionPath.get('params')) {
          if (!isExplicitlyTypedTestInfoParameter(parameter)) {
            continue;
          }
          const binding = functionPath.scope.getBinding(parameter.node.name);
          if (binding !== undefined) {
            testInfoBindings.add(binding);
          }
        }
      },
    });

    let discoveredBinding = true;
    while (discoveredBinding) {
      discoveredBinding = false;
      for (const callPath of callPaths) {
        const functionPath = localFunctionForCall(callPath);
        if (functionPath === undefined) {
          continue;
        }
        const argumentsPaths = callPath.get('arguments');
        const parameters = functionPath.get('params');
        for (let index = 0; index < argumentsPaths.length; index += 1) {
          if (
            !expressionDerivesFromTestInfo(
              argumentsPaths[index],
              testBindings,
              testInfoBindings,
            )
          ) {
            continue;
          }
          const parameter = parameters[index];
          if (!parameter?.isIdentifier?.()) {
            continue;
          }
          const parameterBinding = functionPath.scope.getBinding(
            parameter.node.name,
          );
          if (
            parameterBinding !== undefined &&
            !testInfoBindings.has(parameterBinding)
          ) {
            testInfoBindings.add(parameterBinding);
            discoveredBinding = true;
          }
        }
      }
    }

    function enclosingTest(memberPath) {
      let current = memberPath.parentPath;
      while (current?.node != null) {
        const definition = definitions.find(
          (candidate) => candidate.callbackPath?.node === current.node,
        );
        if (definition !== undefined) {
          return definition;
        }
        current = current.parentPath;
      }
      return undefined;
    }

    function inspectMember(memberPath) {
      const propertyName = memberPropertyName(memberPath);
      const objectPath = memberPath.get('object');
      const derivesFromTest = expressionDerivesFromBinding(
        objectPath,
        testBindings,
      );
      const derivesFromTestInfo = expressionDerivesFromTestInfo(
        objectPath,
        testBindings,
        testInfoBindings,
      );
      const directlyAccessesTestInfo = isDirectTestInfoSource(objectPath);
      if (
        (derivesFromTest || derivesFromTestInfo) &&
        propertyName === undefined
      ) {
        errors.push(
          `${location(file, memberPath.node)}: dynamic Playwright timeout-capable member access is forbidden.`,
        );
        return;
      }
      if (
        (derivesFromTest || derivesFromTestInfo) &&
        typeof propertyName === 'string' &&
        propertyName.startsWith('_')
      ) {
        errors.push(
          `${location(file, memberPath.node)}: private Playwright timeout internals are forbidden.`,
        );
        return;
      }
      if (
        derivesFromTest &&
        ['call', 'apply', 'bind'].includes(propertyName)
      ) {
        errors.push(
          `${location(file, memberPath.node)}: indirect invocation of a Playwright test API is forbidden.`,
        );
        return;
      }
      if (propertyName === 'slow' && (derivesFromTest || derivesFromTestInfo)) {
        errors.push(
          `${location(file, memberPath.node)}: test.slow aliases and bracket forms are forbidden.`,
        );
        return;
      }
      if (propertyName === 'extend' && derivesFromTest) {
        errors.push(
          `${location(file, memberPath.node)}: test.extend aliases are forbidden in timeout-controlled specs.`,
        );
        return;
      }
      if (
        propertyName === 'configure' &&
        expressionDerivesFromBinding(objectPath, testBindings)
      ) {
        errors.push(
          `${location(file, memberPath.node)}: test.describe.configure is forbidden.`,
        );
        return;
      }
      if (
        derivesFromTest &&
        typeof propertyName === 'string' &&
        !ALLOWED_PLAYWRIGHT_TEST_MEMBERS.has(propertyName)
      ) {
        errors.push(
          `${location(file, memberPath.node)}: unsupported Playwright test API member ${propertyName} is forbidden by the timeout policy.`,
        );
        return;
      }
      if (
        directlyAccessesTestInfo &&
        typeof propertyName === 'string' &&
        !ALLOWED_TEST_INFO_MEMBERS.has(propertyName)
      ) {
        errors.push(
          `${location(file, memberPath.node)}: unsupported TestInfo member ${propertyName} is forbidden by the timeout policy.`,
        );
        return;
      }
      if (
        propertyName !== 'setTimeout' ||
        (!derivesFromTest && !derivesFromTestInfo)
      ) {
        return;
      }

      const parent = memberPath.parentPath;
      const isDirectCall =
        parent?.isCallExpression?.() &&
        parent.get('callee').node === memberPath.node;
      const isCanonicalTestMember =
        !memberPath.node.computed &&
        memberPath.get('property').isIdentifier({ name: 'setTimeout' }) &&
        isDirectBindingReference(objectPath, testBinding);
      const args = isDirectCall ? parent.get('arguments') : [];
      const validArgument =
        args.length === 1 &&
        args[0].isNumericLiteral() &&
        args[0].node.value === SCOPED_TIMEOUT;
      const definition = enclosingTest(memberPath);
      const key =
        definition === undefined
          ? undefined
          : testKey(definition.file, definition.title);
      const callbackBody = definition?.callbackPath.get('body');
      const isDirectCallbackStatement =
        parent?.parentPath?.isExpressionStatement?.() &&
        callbackBody?.isBlockStatement?.() &&
        parent.parentPath.parentPath?.node === callbackBody.node;

      if (
        !isCanonicalTestMember ||
        !validArgument ||
        !isDirectCallbackStatement ||
        key === undefined ||
        !scopedCallCounts.has(key)
      ) {
        errors.push(
          `${location(file, memberPath.node)}: only the three directly bound test.setTimeout(${SCOPED_TIMEOUT}) calls are allowed.`,
        );
        return;
      }
      scopedCallCounts.set(key, scopedCallCounts.get(key) + 1);
    }

    programPath.traverse({
      MemberExpression: inspectMember,
      OptionalMemberExpression: inspectMember,
      ObjectProperty(propertyPath) {
        const generalPropertyName = propertyPath.node.computed
          ? constantString(propertyPath.get('key'))
          : (propertyPath.node.key.name ?? propertyPath.node.key.value);
        if (FORBIDDEN_REFLECTION_PROPERTIES.has(generalPropertyName)) {
          errors.push(
            `${location(file, propertyPath.node)}: reflective capability destructuring is forbidden.`,
          );
          return;
        }
        const patternPath = propertyPath.parentPath;
        if (!patternPath?.isObjectPattern?.()) {
          return;
        }
        const declaratorPath = patternPath.parentPath;
        const destructuresTimeoutSource =
          declaratorPath?.isVariableDeclarator?.() &&
            declaratorPath.get('init')?.node != null &&
            (expressionDerivesFromBinding(
              declaratorPath.get('init'),
              testBindings,
            ) ||
              expressionDerivesFromTestInfo(
                declaratorPath.get('init'),
                testBindings,
                testInfoBindings,
              ));
        if (destructuresTimeoutSource) {
          errors.push(
            `${location(file, propertyPath.node)}: destructuring Playwright test or TestInfo is forbidden.`,
          );
        }
      },
      CallExpression(callPath) {
        if (isDirectTestInfoCall(callPath)) {
          let usagePath = callPath;
          while (
            (usagePath.parentPath?.isTSAsExpression?.() ||
              usagePath.parentPath?.isTSTypeAssertion?.() ||
              usagePath.parentPath?.isTSNonNullExpression?.() ||
              usagePath.parentPath?.isParenthesizedExpression?.()) &&
            usagePath.parentPath.get('expression').node === usagePath.node
          ) {
            usagePath = usagePath.parentPath;
          }
          const parent = usagePath.parentPath;
          const usesDirectProperty =
            (parent?.isMemberExpression?.() ||
              parent?.isOptionalMemberExpression?.()) &&
            parent.get('object').node === usagePath.node;
          if (!usesDirectProperty) {
            errors.push(
              `${location(file, callPath.node)}: TestInfo may only use direct properties or explicitly typed local helpers; wrapping, returning or passing it elsewhere is forbidden.`,
            );
          }
        }

        const calleePath = unwrapExpression(callPath.get('callee'));
        if (
          !(
            calleePath?.isMemberExpression?.() ||
            calleePath?.isOptionalMemberExpression?.()
          ) ||
          memberPropertyName(calleePath) !== 'get' ||
          !calleePath.get('object').isIdentifier({ name: 'Reflect' })
        ) {
          return;
        }
        const targetPath = callPath.get('arguments')[0];
        if (
          targetPath?.node != null &&
          (expressionDerivesFromBinding(targetPath, testBindings) ||
            expressionDerivesFromTestInfo(
              targetPath,
              testBindings,
              testInfoBindings,
            ))
        ) {
          errors.push(
            `${location(file, callPath.node)}: Reflect access to Playwright timeout controls is forbidden.`,
          );
        }
      },
    });

    for (const binding of testInfoBindings) {
      for (const reference of binding.referencePaths) {
        let usagePath = reference;
        while (
          (usagePath.parentPath?.isTSAsExpression?.() ||
            usagePath.parentPath?.isTSTypeAssertion?.() ||
            usagePath.parentPath?.isTSNonNullExpression?.() ||
            usagePath.parentPath?.isParenthesizedExpression?.()) &&
          usagePath.parentPath.get('expression').node === usagePath.node
        ) {
          usagePath = usagePath.parentPath;
        }

        const parent = usagePath.parentPath;
        const usesDirectProperty =
          (parent?.isMemberExpression?.() ||
            parent?.isOptionalMemberExpression?.()) &&
          parent.get('object').node === usagePath.node;
        if (usesDirectProperty) {
          continue;
        }

        if (parent?.isCallExpression?.()) {
          const argumentIndex = parent
            .get('arguments')
            .findIndex((argument) => argument.node === usagePath.node);
          const helper = localFunctionForCall(parent);
          if (
            argumentIndex >= 0 &&
            helper !== undefined &&
            isExplicitlyTypedTestInfoParameter(
              helper.get('params')[argumentIndex],
            )
          ) {
            continue;
          }
        }

        errors.push(
          `${location(file, reference.node)}: TestInfo may only use direct properties or explicitly typed local helpers; wrapping, returning or passing it elsewhere is forbidden.`,
        );
      }
    }

    for (const reference of testBinding.referencePaths) {
      let outer = reference;
      while (
        (outer.parentPath?.isMemberExpression?.() ||
          outer.parentPath?.isOptionalMemberExpression?.()) &&
        outer.parentPath.get('object').node === outer.node
      ) {
        outer = outer.parentPath;
      }
      const parent = outer.parentPath;
      if (
        !parent?.isCallExpression?.() ||
        parent.get('callee').node !== outer.node
      ) {
        errors.push(
          `${location(file, reference.node)}: aliasing or indirect access to Playwright test is forbidden.`,
        );
      }
    }
  }

  for (const { file, title } of ALLOWED_SCOPED_TIMEOUTS) {
    const key = testKey(file, title);
    if (definitionCounts.get(key) !== 1) {
      errors.push(
        `${file}: expected exactly one allowlisted test named "${title}".`,
      );
    }
    if (scopedCallCounts.get(key) !== 1) {
      errors.push(
        `${file}: test "${title}" must contain exactly one direct test.setTimeout(${SCOPED_TIMEOUT}) call.`,
      );
    }
  }

  return errors;
}

function configHasApprovedReporters(config, configDirectory) {
  const expectedReporter = path.join(
    configDirectory,
    'specs/support/timeout-policy-reporter.cjs',
  );
  if (!Array.isArray(config.reporter) || config.reporter.length !== 3) {
    if (!Array.isArray(config.reporter) || config.reporter.length !== 1) {
      return false;
    }
    const onlyReporter = Array.isArray(config.reporter[0])
      ? config.reporter[0][0]
      : config.reporter[0];
    return (
      typeof onlyReporter === 'string' &&
      (path.resolve(onlyReporter) === expectedReporter ||
        path.resolve(configDirectory, onlyReporter) === expectedReporter)
    );
  }
  const reporterName = (entry) => (Array.isArray(entry) ? entry[0] : entry);
  const [listReporter, htmlReporter, policyReporter] = config.reporter;
  const policyReporterPath = reporterName(policyReporter);
  return (
    reporterName(listReporter) === 'list' &&
    reporterName(htmlReporter) === 'html' &&
    typeof policyReporterPath === 'string' &&
    (path.resolve(policyReporterPath) === expectedReporter ||
      path.resolve(configDirectory, policyReporterPath) === expectedReporter)
  );
}

function hasExplicitCliSelection() {
  return process.argv.some(
    (argument) =>
      argument === '--grep' ||
      argument.startsWith('--grep=') ||
      argument === '--grep-invert' ||
      argument.startsWith('--grep-invert=') ||
      argument === '--shard' ||
      argument.startsWith('--shard=') ||
      argument === '--last-failed' ||
      argument === '--only-changed',
  );
}

function hasDebugCliFlag() {
  return process.argv.some(
    (argument) => argument === '--debug' || argument.startsWith('--debug='),
  );
}

function validatePlaywrightRuntimeEnvironment(errors) {
  for (const name of FORBIDDEN_PLAYWRIGHT_ENVIRONMENT_VARIABLES) {
    if (process.env[name] !== undefined && process.env[name] !== '') {
      errors.push(
        `Playwright runtime environment variable ${name} is forbidden by the timeout policy.`,
      );
    }
  }
  if (hasDebugCliFlag()) {
    errors.push(
      'Playwright --debug mode is forbidden by the timeout policy.',
    );
  }
}

function validateResolvedPolicy(
  config,
  suite,
  { requireAllAllowlisted = true } = {},
) {
  const errors = [];
  validatePlaywrightRuntimeEnvironment(errors);
  if (typeof config.configFile !== 'string' || config.configFile.length === 0) {
    errors.push('resolved Playwright config must expose its configFile.');
    return errors;
  }
  const configDirectory = path.dirname(config.configFile);
  const expectedRoot = path.join(configDirectory, 'specs');
  if (path.resolve(config.rootDir) !== path.resolve(expectedRoot)) {
    errors.push(
      `resolved rootDir must be ${expectedRoot}, got ${config.rootDir}.`,
    );
  }
  if (config.globalTimeout !== 0) {
    errors.push(
      `resolved globalTimeout must be 0, got ${config.globalTimeout}.`,
    );
  }
  if (!Array.isArray(config.projects) || config.projects.length !== 1) {
    errors.push('resolved Playwright config must contain exactly one project.');
  }
  if (!configHasApprovedReporters(config, configDirectory)) {
    errors.push(
      'resolved Playwright config must use only the timeout policy reporter or list, html and the final timeout policy reporter for every run.',
    );
  }
  for (const project of config.projects ?? []) {
    if (project.timeout !== DEFAULT_TIMEOUT) {
      errors.push(
        `resolved project timeout must be ${DEFAULT_TIMEOUT}, got ${project.timeout}.`,
      );
    }
    if (project.retries !== 0) {
      errors.push(
        `resolved project retries must be 0, got ${project.retries}.`,
      );
    }
  }

  const tests = suite.allTests();
  if (tests.length === 0) {
    errors.push('resolved Playwright suite must not be empty.');
  }
  const resolvedAllowlistCounts = new Map(
    ALLOWED_SCOPED_TIMEOUTS.map(({ file, title }) => [testKey(file, title), 0]),
  );
  for (const test of tests) {
    const relativeFile = normalizePath(
      path.relative(configDirectory, test.location.file),
    );
    if (test.timeout !== DEFAULT_TIMEOUT) {
      errors.push(
        `${relativeFile}:${test.location.line}: collection-time timeout must stay ${DEFAULT_TIMEOUT}, got ${test.timeout}.`,
      );
    }
    if (test.retries !== 0) {
      errors.push(
        `${relativeFile}:${test.location.line}: resolved test retries must be 0, got ${test.retries}.`,
      );
    }
    const key = testKey(relativeFile, test.title);
    if (resolvedAllowlistCounts.has(key)) {
      resolvedAllowlistCounts.set(key, resolvedAllowlistCounts.get(key) + 1);
    }
  }
  for (const { file, title } of ALLOWED_SCOPED_TIMEOUTS) {
    const count = resolvedAllowlistCounts.get(testKey(file, title));
    if (count > 1) {
      errors.push(
        `${file}: resolved suite may contain at most one allowlisted test named "${title}".`,
      );
    } else if (requireAllAllowlisted && count !== 1) {
      errors.push(
        `${file}: resolved suite must contain exactly one allowlisted test named "${title}".`,
      );
    }
  }
  return errors;
}

class TimeoutPolicyReporter {
  constructor() {
    this.errors = [];
  }

  onBegin(config, suite) {
    try {
      const configDirectory = path.dirname(config.configFile);
      this.errors = [
        ...validateSpecSources(readSpecSources(configDirectory)),
        ...validateResolvedPolicy(config, suite, {
          requireAllAllowlisted: !hasExplicitCliSelection(),
        }),
      ];
    } catch (error) {
      this.errors = [error instanceof Error ? error.message : String(error)];
    }

    if (this.errors.length === 0) {
      console.log(
        `Semantic timeout policy passed: ${suite.allTests().length} tests, default ${DEFAULT_TIMEOUT} ms, three scoped ${SCOPED_TIMEOUT} ms callbacks.`,
      );
      return;
    }
    console.error('Semantic timeout policy failed:');
    for (const error of this.errors) {
      console.error(`- ${error}`);
    }
    process.exitCode = 1;
  }

  onEnd() {
    if (this.errors.length > 0) {
      return { status: 'failed' };
    }
    return undefined;
  }

  printsToStdio() {
    return true;
  }
}

module.exports = TimeoutPolicyReporter;
module.exports.ALLOWED_SCOPED_TIMEOUTS = ALLOWED_SCOPED_TIMEOUTS;
module.exports.DEFAULT_TIMEOUT = DEFAULT_TIMEOUT;
module.exports.SCOPED_TIMEOUT = SCOPED_TIMEOUT;
module.exports.loadPinnedAstTools = loadPinnedAstTools;
module.exports.readSpecSources = readSpecSources;
module.exports.validateResolvedPolicy = validateResolvedPolicy;
module.exports.validateSpecSources = validateSpecSources;
