const assert = require('node:assert/strict');
const { test } = require('node:test');
const { buildSync } = require('esbuild');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');

for (const extension of ['.ts', '.tsx']) {
  require.extensions[extension] = (module, filename) => {
    const { outputFiles } = buildSync({
      entryPoints: [filename],
      bundle: true,
      write: false,
      platform: 'node',
      format: 'cjs',
      jsx: 'automatic',
      define: { 'import.meta.env.BASE_URL': JSON.stringify('/Ai-Lab/') },
      external: ['react', 'react-dom', 'react/jsx-runtime'],
    });
    module._compile(outputFiles[0].text, `${filename}.cjs`);
  };
}

const {
  acuTelemetrySummary,
  hasAcuTelemetry,
  isPricedRun,
  modelFamilySummaries,
  scopeRuns,
} = require('../src/lib/analytics.ts');
const Analytics = require('../src/components/workspace/Analytics.tsx').default;

const makeRun = (overrides) => ({
  id: 1,
  task_id: 'BENCH-001',
  arm: 'baseline',
  model: 'gemini-3.8-flash',
  run_index: 1,
  timestamp: '2026-11-22T00:00:00Z',
  input_tokens: 1000,
  output_tokens: 200,
  thinking_tokens: 0,
  cache_read_tokens: 0,
  total_tokens: 1200,
  num_turns: 4,
  duration_seconds: 10,
  cost_usd: 0.12,
  cost_status: 'usage_estimate',
  source_kind: 'live',
  evidence_status: 'verified',
  verification_status: 'passed',
  is_comparison_eligible: true,
  ...overrides,
});

test('ACU metadata stays separate from priced cost_usd scope', () => {
  const direct = makeRun({ id: 1, cost_usd: 0.15 });
  const devinAcu = makeRun({
    id: 2,
    model: 'devin-session-v3',
    input_tokens: null,
    output_tokens: null,
    total_tokens: null,
    acus_consumed: 0.8,
    cost_usd: null,
    cost_status: 'unavailable',
  });

  const zeroAcu = makeRun({
    id: 3,
    model: 'devin-session-v3',
    acus_consumed: 0,
    cost_usd: null,
    cost_status: 'unavailable',
  });

  assert.equal(isPricedRun(direct), true);
  assert.equal(hasAcuTelemetry(direct), false);

  assert.equal(isPricedRun(devinAcu), false);
  assert.equal(hasAcuTelemetry(devinAcu), true);
  assert.equal(isPricedRun(zeroAcu), false);
  assert.equal(hasAcuTelemetry(zeroAcu), false);

  const runs = [direct, devinAcu, zeroAcu];
  assert.deepEqual(scopeRuns(runs, 'priced').map((r) => r.id), [1]);
  assert.deepEqual(scopeRuns(runs, 'unpriced').map((r) => r.id), [2, 3]);

  const summary = acuTelemetrySummary(runs);
  assert.equal(summary.runsWithAcus, 1);
  assert.equal(summary.totalAcus, 0.8);
});

test('modelFamilySummaries and Analytics UI surface ACU metadata while keeping Devin runs Unpriced', () => {
  const runs = [
    makeRun({ id: 1, model: 'gemini-3.8-flash', arm: 'baseline', cost_usd: 0.2 }),
    makeRun({ id: 2, model: 'gemini-3.8-flash', arm: 'icm', cost_usd: 0.15 }),
    makeRun({
      id: 3,
      model: 'devin-session-v3',
      arm: 'baseline',
      input_tokens: null,
      output_tokens: null,
      total_tokens: null,
      acus_consumed: 1.0,
      cost_usd: null,
      cost_status: 'unavailable',
    }),
    makeRun({
      id: 4,
      model: 'devin-session-v3',
      arm: 'icm',
      input_tokens: null,
      output_tokens: null,
      total_tokens: null,
      acus_consumed: 0.75,
      cost_usd: null,
      cost_status: 'unavailable',
    }),
  ];

  const families = modelFamilySummaries(runs, 'all');
  const devin = families.find((f) => f.family === 'devin');
  const gemini = families.find((f) => f.family === 'gemini');
  assert.equal(devin.pricedRuns, 0);
  assert.equal(devin.baselineCostUsd, null);
  assert.equal(devin.governedCostUsd, null);
  assert.equal(devin.acuRuns, 2);
  assert.equal(devin.totalAcus, 1.75);
  assert.equal(gemini.pricedRuns, 2);
  assert.equal(gemini.acuRuns, 0);

  const markup = renderToStaticMarkup(
    React.createElement(Analytics, {
      data: {
        generated_at: '2026-11-22T00:00:00Z',
        has_data: true,
        cumulative: { tasks_evaluated: 0, total_runs: runs.length, tasks: [] },
        tasks: [],
        runs,
        timeline: [],
        pricing: [],
      },
    }),
  );
  assert.match(markup, /ACU telemetry \(metadata\)/);
  assert.match(markup, /1\.75 ACU/);
  assert.match(markup, /Unpriced/);
});
