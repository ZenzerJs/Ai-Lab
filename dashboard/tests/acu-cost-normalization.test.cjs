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
  costSourceBreakdown,
  formatCostSourceLabel,
  getCostSource,
  isAcuDerivedRun,
  isDirectBilledRun,
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
  cost_source: 'billed_direct',
  source_kind: 'live',
  evidence_status: 'verified',
  verification_status: 'passed',
  is_comparison_eligible: true,
  ...overrides,
});

test('cost source classification separates Direct Billed, ACU Derived, and Unpriced runs', () => {
  const direct = makeRun({ id: 1, cost_source: 'billed_direct', cost_usd: 0.15 });
  const acu = makeRun({
    id: 2,
    model: 'devin-session-v3',
    input_tokens: null,
    output_tokens: null,
    total_tokens: null,
    acus_consumed: 0.8,
    acu_usd_rate: 2.25,
    cost_usd: 1.8,
    estimated_cost_usd: 1.8,
    cost_status: 'estimated_acu_derived',
    cost_source: 'estimated_acu_derived',
  });
  const unpriced = makeRun({
    id: 3,
    model: 'swe-2-max-lightning',
    cost_usd: null,
    cost_status: 'unavailable',
    cost_source: 'unavailable',
  });

  assert.equal(getCostSource(direct), 'billed_direct');
  assert.equal(isDirectBilledRun(direct), true);
  assert.equal(isAcuDerivedRun(direct), false);
  assert.equal(formatCostSourceLabel(getCostSource(direct)), 'Direct Billed');

  assert.equal(getCostSource(acu), 'estimated_acu_derived');
  assert.equal(isDirectBilledRun(acu), false);
  assert.equal(isAcuDerivedRun(acu), true);
  assert.equal(formatCostSourceLabel(getCostSource(acu)), 'ACU Derived');

  assert.equal(getCostSource(unpriced), 'unavailable');
  assert.equal(formatCostSourceLabel(getCostSource(unpriced)), 'Unpriced');

  const runs = [direct, acu, unpriced];
  assert.deepEqual(scopeRuns(runs, 'billed_direct').map((r) => r.id), [1]);
  assert.deepEqual(scopeRuns(runs, 'estimated_acu_derived').map((r) => r.id), [2]);
  assert.deepEqual(scopeRuns(runs, 'priced').map((r) => r.id), [1, 2]);
  assert.deepEqual(scopeRuns(runs, 'unpriced').map((r) => r.id), [3]);

  const breakdown = costSourceBreakdown(runs);
  assert.equal(breakdown.directBilled, 1);
  assert.equal(breakdown.acuDerived, 1);
  assert.equal(breakdown.unpriced, 1);
  assert.equal(breakdown.totalAcus, 0.8);
  assert.equal(breakdown.costBasisLabel, 'Direct Billed + ACU Derived');
});

test('modelFamilySummaries and Analytics UI explicitly label Direct Billed vs ACU Derived', () => {
  const runs = [
    makeRun({ id: 1, model: 'gemini-3.8-flash', arm: 'baseline', cost_usd: 0.2, cost_source: 'billed_direct' }),
    makeRun({ id: 2, model: 'gemini-3.8-flash', arm: 'icm', cost_usd: 0.15, cost_source: 'billed_direct' }),
    makeRun({
      id: 3,
      model: 'devin-session-v3',
      arm: 'baseline',
      input_tokens: null,
      output_tokens: null,
      total_tokens: null,
      acus_consumed: 1.0,
      cost_usd: 2.25,
      estimated_cost_usd: 2.25,
      cost_status: 'estimated_acu_derived',
      cost_source: 'estimated_acu_derived',
    }),
    makeRun({
      id: 4,
      model: 'devin-session-v3',
      arm: 'icm',
      input_tokens: null,
      output_tokens: null,
      total_tokens: null,
      acus_consumed: 0.75,
      cost_usd: 1.6875,
      estimated_cost_usd: 1.6875,
      cost_status: 'estimated_acu_derived',
      cost_source: 'estimated_acu_derived',
    }),
  ];

  const families = modelFamilySummaries(runs, 'all');
  const devin = families.find((f) => f.family === 'devin');
  const gemini = families.find((f) => f.family === 'gemini');
  assert.equal(devin.costBasis, 'ACU Derived');
  assert.equal(devin.acuDerivedRuns, 2);
  assert.equal(devin.totalAcus, 1.75);
  assert.equal(gemini.costBasis, 'Direct Billed');
  assert.equal(gemini.directBilledRuns, 2);

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
  assert.match(markup, /Direct Billed only/);
  assert.match(markup, /ACU Derived only/);
  assert.match(markup, /1\.75 ACU/);
});
