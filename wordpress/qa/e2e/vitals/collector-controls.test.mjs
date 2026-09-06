import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import test from 'node:test';

const runner = fileURLToPath(new URL('./runner.mjs', import.meta.url));

test('actual collector rejects missing INP and detects layout shift and slow trusted input', () => {
  const fixture = mkdtempSync(join(tmpdir(), 'gama-vitals-controls.'));
  try {
    const output = join(fixture, 'controls.json');
    const result = spawnSync(process.execPath, [runner, 'controls', output], {
      encoding: 'utf8',
      timeout: 120_000,
    });

    assert.equal(result.status, 0, `${result.stdout}\n${result.stderr}`);
    const controls = JSON.parse(readFileSync(output, 'utf8'));
    assert.equal(controls.library.name, 'web-vitals');
    assert.equal(controls.library.version, '6.2.1');
    assert.equal(controls.missingMetric.valid, false);
    assert.match(controls.missingMetric.errors.join('\n'), /INP is missing/);
    assert.equal(controls.layoutShift.valid, true);
    assert.ok(controls.layoutShift.metrics.CLS.value > 0.1);
    assert.equal(controls.slowInput.valid, true);
    assert.ok(controls.slowInput.metrics.INP.value >= 200);
    assert.ok(controls.slowInput.interactions.trustedClicks >= 1);
    for (const sample of [controls.layoutShift, controls.slowInput]) {
      assert.equal(sample.support.secureContext, true);
      assert.equal(sample.finalization.pagehide, true);
      assert.equal(typeof sample.finalization.visibilityHidden, 'boolean');
      assert.deepEqual(sample.finalization.retainedMetrics.sort(), [
        'CLS',
        'INP',
        'LCP',
      ]);
    }
  } finally {
    rmSync(fixture, { recursive: true, force: true });
  }
});
