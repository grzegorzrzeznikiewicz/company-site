import assert from 'node:assert/strict';
import { mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import test from 'node:test';

const runner = fileURLToPath(new URL('./runner.mjs', import.meta.url));

test('measurement command rejects incomplete immutable provenance before launching a browser', () => {
  const fixture = mkdtempSync(join(tmpdir(), 'gama-vitals-measure.'));
  try {
    const config = join(fixture, 'config.json');
    const output = join(fixture, 'raw.json');
    writeFileSync(config, JSON.stringify({ formatVersion: 1 }));

    const result = spawnSync(process.execPath, [runner, 'measure', config, output], {
      encoding: 'utf8',
    });

    assert.equal(result.status, 2);
    assert.match(result.stderr, /baselineRoot must be an existing absolute directory/);
    assert.match(result.stderr, /candidateImage must be an immutable image ID/);
    assert.match(result.stderr, /browserImage must be an immutable image ID/);
  } finally {
    rmSync(fixture, { recursive: true, force: true });
  }
});
