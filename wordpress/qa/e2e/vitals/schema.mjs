const METRICS = {
  LCP: 'ms',
  CLS: 'score',
  INP: 'ms',
};

function sampleLabel(sample) {
  return `${sample.target ?? '?'}\/${sample.route ?? '?'}\/${sample.viewport?.name ?? '?'}\/${sample.sample ?? '?'}`;
}

function assert(condition, message, errors) {
  if (!condition) errors.push(message);
}

export function validateSample(sample) {
  const label = `sample ${sampleLabel(sample)}`;
  const errors = [];
  assert(sample.formatVersion === 1, `${label}: formatVersion must be 1`, errors);
  assert(
    ['baseline', 'wordpress', 'control'].includes(sample.target),
    `${label}: target is invalid`,
    errors,
  );
  assert(typeof sample.route === 'string' && sample.route !== '', `${label}: route is missing`, errors);
  assert(
    Number.isInteger(sample.sample) && sample.sample > 0,
    `${label}: sample must be a positive integer`,
    errors,
  );
  assert(
    Number.isInteger(sample.order) && sample.order > 0,
    `${label}: order must be a positive integer`,
    errors,
  );
  assert(
    /^[a-f0-9]{40}$/.test(sample.sourceRevision ?? ''),
    `${label}: sourceRevision must be a commit SHA`,
    errors,
  );
  for (const field of ['browserImage', 'serverImage']) {
    assert(
      /^sha256:[a-f0-9]{64}$/.test(sample[field] ?? ''),
      `${label}: ${field} must be an immutable image ID`,
      errors,
    );
  }
  if (sample.target === 'baseline') {
    assert(
      /^sha256:[a-f0-9]{64}$/.test(sample.buildImage ?? ''),
      `${label}: buildImage must be an immutable image ID`,
      errors,
    );
  }
  if (sample.target === 'wordpress') {
    assert(
      /^sha256:[a-f0-9]{64}$/.test(sample.candidateImage ?? ''),
      `${label}: candidateImage must be an immutable image ID`,
      errors,
    );
    assert(
      sample.candidateImage === sample.serverImage,
      `${label}: candidateImage must equal the measured serverImage`,
      errors,
    );
  }

  for (const [name, unit] of Object.entries(METRICS)) {
    const metric = sample.metrics?.[name];
    if (metric === undefined) {
      errors.push(`${label}: ${name} is missing`);
      continue;
    }
    assert(metric.name === name, `${label}: ${name} name is invalid`, errors);
    assert(metric.unit === unit, `${label}: ${name} unit must be ${unit}`, errors);
    assert(metric.reported === true, `${label}: ${name} was not reported`, errors);
    assert(metric.valid === true, `${label}: ${name} is invalid`, errors);
    assert(
      typeof metric.value === 'number' && Number.isFinite(metric.value),
      `${label}: ${name} must be finite`,
      errors,
    );
    assert(metric.value >= 0, `${label}: ${name} must not be negative`, errors);
  }

  const support = sample.support ?? {};
  for (const field of [
    'secureContext',
    'performanceObserver',
    'largestContentfulPaint',
    'layoutShift',
    'event',
  ]) {
    assert(support[field] === true, `${label}: ${field} support is required`, errors);
  }

  const interactions = sample.interactions ?? {};
  const interactionParts = [
    interactions.trustedClicks,
    interactions.trustedKeydowns,
    interactions.trustedInputs,
  ];
  assert(
    interactionParts.every((value) => Number.isInteger(value) && value >= 0),
    `${label}: trusted interaction counts must be non-negative integers`,
    errors,
  );
  assert(
    Number.isInteger(interactions.total) && interactions.total > 0,
    `${label}: at least one trusted interaction is required`,
    errors,
  );
  assert(
    interactions.total === interactionParts.reduce((sum, value) => sum + (value ?? 0), 0),
    `${label}: trusted interaction total is inconsistent`,
    errors,
  );

  const finalization = sample.finalization ?? {};
  assert(
    finalization.mechanism === 'same-origin-navigation',
    `${label}: finalization mechanism is invalid`,
    errors,
  );
  assert(
    typeof finalization.visibilityHidden === 'boolean',
    `${label}: visibility finalization evidence is missing`,
    errors,
  );
  assert(finalization.pagehide === true, `${label}: pagehide finalization is missing`, errors);
  for (const name of Object.keys(METRICS)) {
    assert(
      finalization.retainedMetrics?.includes(name) === true,
      `${label}: ${name} was not retained across finalization`,
      errors,
    );
  }

  assert(Array.isArray(sample.httpFailures), `${label}: httpFailures must be an array`, errors);
  assert(Array.isArray(sample.consoleFailures), `${label}: consoleFailures must be an array`, errors);
  assert(sample.httpFailures?.length === 0, `${label}: HTTP failures were recorded`, errors);
  assert(sample.consoleFailures?.length === 0, `${label}: console failures were recorded`, errors);
  return errors;
}

export function validateDocument(document) {
  if (!Array.isArray(document?.samples) || document.samples.length === 0) {
    return ['document: samples must be a non-empty array'];
  }
  return document.samples.flatMap(validateSample);
}

function distribution(values, unit) {
  const sorted = [...values].sort((left, right) => left - right);
  return {
    unit,
    median: sorted[Math.floor(sorted.length / 2)],
    min: sorted[0],
    max: sorted.at(-1),
  };
}

export function summarize(document) {
  const errors = validateDocument(document);
  if (errors.length > 0) {
    const error = new Error(errors.join('\n'));
    error.validationErrors = errors;
    throw error;
  }
  const groups = new Map();
  for (const sample of document.samples) {
    const key = `${sample.target}\u0000${sample.route}\u0000${sample.viewport.name}`;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(sample);
  }
  return {
    formatVersion: 1,
    generatedAt: new Date().toISOString(),
    groups: [...groups.values()].map((samples) => ({
      target: samples[0].target,
      route: samples[0].route,
      viewport: samples[0].viewport,
      sampleCount: samples.length,
      sampleOrder: samples.map(({ sample, order }) => ({ sample, order })),
      interactionCount: samples.reduce((sum, item) => sum + item.interactions.total, 0),
      metrics: Object.fromEntries(
        Object.entries(METRICS).map(([name, unit]) => [
          name,
          distribution(samples.map((item) => item.metrics[name].value), unit),
        ]),
      ),
    })),
  };
}
