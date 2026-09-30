import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import test from 'node:test';

const runtime = fileURLToPath(
  new URL('../../../tests/release-vitals-runtime.sh', import.meta.url),
);

test(
  'runtime refuses a non-commit candidate before touching Docker',
  { skip: !existsSync(runtime) },
  () => {
    const result = spawnSync('bash', [runtime], {
      encoding: 'utf8',
      env: { ...process.env, GAMA_CWV_CANDIDATE_REF: 'HEAD' },
    });

    assert.equal(result.status, 64);
    assert.match(result.stderr, /exact 40-character candidate commit/);
  },
);
