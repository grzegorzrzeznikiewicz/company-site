import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import test from 'node:test';

const runner = fileURLToPath(new URL('./runner.mjs', import.meta.url));

test('React button and WordPress link adapters complete trusted contact typing without submit', () => {
  const fixture = mkdtempSync(join(tmpdir(), 'gama-vitals-journeys.'));
  try {
    const output = join(fixture, 'journeys.json');
    const result = spawnSync(process.execPath, [runner, 'journey-controls', output], {
      encoding: 'utf8',
      timeout: 120_000,
    });

    assert.equal(result.status, 0, `${result.stdout}\n${result.stderr}`);
    const evidence = JSON.parse(readFileSync(output, 'utf8'));
    assert.deepEqual(
      evidence.samples.map(({ route, valid }) => ({ route, valid })),
      [
        { route: 'react-adapter', valid: true },
        { route: 'wordpress-adapter', valid: true },
      ],
    );
    for (const sample of evidence.samples) {
      assert.ok(sample.interactions.trustedClicks >= 5);
      assert.ok(sample.interactions.trustedKeydowns >= 20);
      assert.ok(sample.interactions.trustedInputs >= 20);
      assert.equal(sample.formSubmitted, false);
      assert.equal(sample.metrics.INP.reported, true);
    }
  } finally {
    rmSync(fixture, { recursive: true, force: true });
  }
});
