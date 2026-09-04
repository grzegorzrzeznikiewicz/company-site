'use strict';

const { spawnSync } = require('node:child_process');

const ALLOWED_FLAG_ARGUMENTS = new Set([
  '--last-failed',
  '--list',
  '--only-changed',
]);
const ALLOWED_VALUE_ARGUMENTS = new Set([
  '--grep',
  '--grep-invert',
  '--shard',
]);
const SANITIZED_PLAYWRIGHT_ENVIRONMENT = [
  'PW_TEST_SOURCE_TRANSFORM',
  'PW_TEST_SOURCE_TRANSFORM_SCOPE',
  'PW_TEST_REPORTER',
  'PWDEBUG',
];

function unsupportedArgument(argument) {
  return new Error(`Unsupported Playwright CLI argument: ${argument}`);
}

function validatePlaywrightCliArguments(argumentsToValidate) {
  const forwarded = [];
  for (let index = 0; index < argumentsToValidate.length; index += 1) {
    const argument = argumentsToValidate.at(index);
    if (typeof argument !== 'string') {
      throw unsupportedArgument(String(argument));
    }
    if (ALLOWED_FLAG_ARGUMENTS.has(argument)) {
      forwarded.push(argument);
      continue;
    }
    const equalsOption = [...ALLOWED_VALUE_ARGUMENTS].find((option) =>
      argument.startsWith(`${option}=`),
    );
    if (equalsOption !== undefined) {
      if (argument.length === equalsOption.length + 1) {
        throw new Error(`${equalsOption} requires one non-option value.`);
      }
      forwarded.push(argument);
      continue;
    }
    if (ALLOWED_VALUE_ARGUMENTS.has(argument)) {
      const value = argumentsToValidate.at(index + 1);
      if (typeof value !== 'string' || value.length === 0 || value.startsWith('--')) {
        throw new Error(`${argument} requires one non-option value.`);
      }
      forwarded.push(argument, value);
      index += 1;
      continue;
    }
    throw unsupportedArgument(argument);
  }
  return forwarded;
}

function runPlaywright() {
  let argumentsToForward;
  try {
    argumentsToForward = validatePlaywrightCliArguments(process.argv.slice(2));
  } catch (error) {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 64;
    return;
  }

  const result = spawnSync(
    'env',
    [
      ...SANITIZED_PLAYWRIGHT_ENVIRONMENT.flatMap((name) => ['-u', name]),
      'npx',
      'playwright',
      'test',
      '--tsconfig',
      './timeout-policy.tsconfig.json',
      ...argumentsToForward,
    ],
    { stdio: 'inherit' },
  );
  if (result.error !== undefined) {
    console.error(result.error.message);
    process.exitCode = 1;
    return;
  }
  process.exitCode = Number.isInteger(result.status) ? result.status : 1;
}

if (process.argv.at(1) === __filename) {
  runPlaywright();
}

module.exports = { validatePlaywrightCliArguments };
