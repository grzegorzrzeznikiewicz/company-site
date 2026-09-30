import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import test from 'node:test';

const runner = fileURLToPath(new URL('./runner.mjs', import.meta.url));

test('measurement plan alternates paired home samples before WordPress-only routes', () => {
  const result = spawnSync(process.execPath, [runner, 'plan'], { encoding: 'utf8' });

  assert.equal(result.status, 0, result.stderr);
  const plan = JSON.parse(result.stdout);
  assert.equal(plan.length, 40);
  assert.deepEqual(
    plan.slice(0, 4).map(({ target, route, viewport, sample, order }) => ({
      target,
      route,
      viewport: viewport.name,
      sample,
      order,
    })),
    [
      { target: 'baseline', route: 'home', viewport: 'desktop', sample: 1, order: 1 },
      { target: 'wordpress', route: 'home', viewport: 'desktop', sample: 1, order: 2 },
      { target: 'baseline', route: 'home', viewport: 'desktop', sample: 2, order: 3 },
      { target: 'wordpress', route: 'home', viewport: 'desktop', sample: 2, order: 4 },
    ],
  );
  assert.equal(plan.slice(0, 20).every(({ route }) => route === 'home'), true);
  assert.equal(plan.slice(20).every(({ target }) => target === 'wordpress'), true);
  for (const route of ['blog-archive', 'representative-article']) {
    for (const viewport of ['desktop', 'phone']) {
      assert.equal(
        plan.filter((item) => item.route === route && item.viewport.name === viewport).length,
        5,
      );
    }
  }
});

test('measurement plan exposes independently runnable home and WordPress-only phases', () => {
  const home = spawnSync(process.execPath, [runner, 'plan', 'home'], { encoding: 'utf8' });
  const wordpressOnly = spawnSync(process.execPath, [runner, 'plan', 'wordpress-only'], {
    encoding: 'utf8',
  });

  assert.equal(home.status, 0, home.stderr);
  assert.equal(wordpressOnly.status, 0, wordpressOnly.stderr);
  assert.equal(JSON.parse(home.stdout).length, 20);
  assert.equal(JSON.parse(wordpressOnly.stdout).length, 20);
  assert.equal(JSON.parse(home.stdout).every(({ route }) => route === 'home'), true);
  assert.equal(
    JSON.parse(wordpressOnly.stdout).every(({ target, order }) => target === 'wordpress' && order > 20),
    true,
  );
});
