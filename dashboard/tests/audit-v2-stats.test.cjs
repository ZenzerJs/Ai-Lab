const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
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
  MIN_PAIRS_FOR_EFFECT,
  applyFdrToRows,
  benjaminiHochberg,
  crossCheckBenchmarks,
  formatSignedCostChange,
  matchedArmComparison,
  pairedDiffStats,
  primaryEffectMetric,
  suitePairsDetailed,
} = require('../src/lib/analytics.ts');

const snapshot = JSON.parse(
  fs.readFileSync(path.join(__dirname, '../public/data.json'), 'utf8'),
);

const makeRun = (overrides) => ({
  id: 1,
  task_id: 'BENCH-001',
  arm: 'baseline',
  model: 'claude-sonnet-5-5-low',
  run_index: 1,
  timestamp: '2026-11-22T00:00:00Z',
  input_tokens: 1000,
  output_tokens: 200,
  thinking_tokens: 0,
  cache_read_tokens: 0,
  total_tokens: 1200,
  num_turns: 4,
  duration_seconds: 15,
  cost_usd: 0.1,
  cost_status: 'usage_estimate',
  source_kind: 'live',
  evaluator_hash: 'hash-aaa',
  is_comparison_eligible: true,
  verification_status: 'passed',
  ...overrides,
});

test('suitePairsDetailed enforces (task_id, model, run_index, evaluator_hash) and reports dropped/hash-mismatched counts', () => {
  const task = {
    task_id: 'BENCH-001',
    model: 'claude-sonnet-5-5-low',
    arms: {
      baseline: {
        runs: [
          makeRun({ id: 1, run_index: 1, evaluator_hash: 'hash-aaa', cost_usd: 0.2 }),
          makeRun({ id: 2, run_index: 2, evaluator_hash: 'hash-aaa', cost_usd: 0.3 }),
          makeRun({ id: 3, run_index: 3, model: 'claude-sonnet-5-5-low', evaluator_hash: 'hash-aaa', cost_usd: 0.4 }),
        ],
      },
      icm: {
        runs: [
          // Exact 4-tuple match
          makeRun({ id: 4, arm: 'icm', run_index: 1, evaluator_hash: 'hash-aaa', cost_usd: 0.1 }),
          // Evaluator hash mismatch on same (task_id, model, run_index)
          makeRun({ id: 5, arm: 'icm', run_index: 2, evaluator_hash: 'hash-bbb', cost_usd: 0.15 }),
          // Model mismatch on same (task_id, run_index)
          makeRun({ id: 6, arm: 'icm', run_index: 3, model: 'other-model', evaluator_hash: 'hash-aaa', cost_usd: 0.2 }),
          // Unmatched run_index
          makeRun({ id: 7, arm: 'icm', run_index: 4, evaluator_hash: 'hash-aaa', cost_usd: 0.25 }),
        ],
      },
    },
  };

  const result = suitePairsDetailed(task, 'icm');
  assert.deepEqual(result.pairs, [[0.2, 0.1]]);
  assert.equal(result.hashMismatchedCount, 1);
  assert.equal(result.modelMismatchedCount, 1);
  assert.equal(result.unmatchedCount, 1);
  assert.equal(result.droppedCount, 3);
});

test('pairedDiffStats requires n >= 5 pairs before showing Cohen dz and marks n < 5 preliminary', () => {
  assert.equal(MIN_PAIRS_FOR_EFFECT, 5);
  const small = pairedDiffStats([
    [10, 7],
    [12, 8],
    [11, 7],
    [13, 9],
  ]);
  assert.equal(small.n, 4);
  assert.equal(small.preliminary, true);
  assert.equal(small.displayCohensDz, null);
  assert.equal(small.displayEffectSize, null);

  const sufficient = pairedDiffStats([
    [10, 7],
    [12, 8],
    [11, 7],
    [13, 9],
    [14, 9],
  ]);
  assert.equal(sufficient.n, 5);
  assert.equal(sufficient.preliminary, false);
  assert.ok(sufficient.displayCohensDz > 0.8);
  assert.equal(sufficient.displayEffectSize, 'large');
  assert.equal(sufficient.ciExploratory, true);
  assert.ok(sufficient.pValue != null && sufficient.pValue < 0.05);
});

test('benjaminiHochberg adjusts p-values across suites monotonically', () => {
  const { qValues, significant } = benjaminiHochberg([0.001, 0.02, 0.04, 0.5, null], 0.05);
  assert.equal(qValues[4], null);
  assert.equal(significant[4], null);
  // m = 4 valid tests:
  // rank 1: 0.001 * 4 / 1 = 0.004
  // rank 2: 0.02 * 4 / 2 = 0.04
  // rank 3: 0.04 * 4 / 3 = 0.0533...
  // rank 4: 0.5 * 4 / 4 = 0.5
  assert.ok(Math.abs(qValues[0] - 0.004) < 1e-9);
  assert.ok(Math.abs(qValues[1] - 0.04) < 1e-9);
  assert.ok(Math.abs(qValues[2] - 0.04 * 4 / 3) < 1e-9);
  assert.ok(Math.abs(qValues[3] - 0.5) < 1e-9);
  assert.deepEqual(significant.slice(0, 4), [true, true, false, false]);

  const rows = applyFdrToRows([
    { id: 'a', stats: { ...pairedDiffStats([[10, 5], [10, 5.1], [10, 4.9], [10, 5.05], [10, 4.95]]) } },
    { id: 'b', stats: { ...pairedDiffStats([[10, 9.9], [10, 10.1], [10, 9.8], [10, 10.2], [10, 10.0]]) } },
  ]);
  assert.equal(rows[0].stats.fdrSignificant, true);
  assert.equal(rows[1].stats.fdrSignificant, false);
});

test('matchedArmComparison compares icm_lite against baseline ONLY on shared tasks', () => {
  const sharedTask = {
    task_id: 'BENCH-001',
    model: 'swe-2',
    arms: {
      baseline: {
        runs: [
          makeRun({ id: 1, task_id: 'BENCH-001', model: 'swe-2', run_index: 1, total_tokens: 1000, cost_usd: null }),
          makeRun({ id: 2, task_id: 'BENCH-001', model: 'swe-2', run_index: 2, total_tokens: 1200, cost_usd: null }),
        ],
      },
      icm_lite: {
        runs: [
          makeRun({ id: 3, task_id: 'BENCH-001', arm: 'icm_lite', model: 'swe-2', run_index: 1, total_tokens: 800, cost_usd: null }),
          makeRun({ id: 4, task_id: 'BENCH-001', arm: 'icm_lite', model: 'swe-2', run_index: 2, total_tokens: 900, cost_usd: null }),
        ],
      },
    },
  };
  const harderUnsharedTask = {
    task_id: 'BENCH-020',
    model: 'swe-2',
    arms: {
      baseline: {
        runs: [
          makeRun({ id: 5, task_id: 'BENCH-020', model: 'swe-2', run_index: 1, total_tokens: 50000, cost_usd: null }),
        ],
      },
      icm: {
        runs: [
          makeRun({ id: 6, task_id: 'BENCH-020', arm: 'icm', model: 'swe-2', run_index: 1, total_tokens: 45000, cost_usd: null }),
        ],
      },
    },
  };

  const cmp = matchedArmComparison([sharedTask, harderUnsharedTask], 'icm_lite', 'baseline');
  assert.deepEqual(cmp.sharedTaskIds, ['BENCH-001']);
  assert.equal(cmp.excludedUnsharedTaskCount, 1);
  assert.equal(cmp.tokenStats.n, 2);
  assert.equal(cmp.tokenStats.meanBaseline, 1100);
  assert.equal(cmp.tokenStats.meanGoverned, 850);
});

test('primaryEffectMetric selects Tokens when priced coverage < 100% and Cost at 100%', () => {
  assert.equal(primaryEffectMetric(null), 'Tokens');
  assert.equal(primaryEffectMetric(0), 'Tokens');
  assert.equal(primaryEffectMetric(15.5), 'Tokens');
  assert.equal(primaryEffectMetric(99.9), 'Tokens');
  assert.equal(primaryEffectMetric(100), 'Cost');
});

test('formatSignedCostChange produces unambiguous +X% cost vs -X% savings labels', () => {
  assert.equal(formatSignedCostChange(-10.5), '+10.5% cost');
  assert.equal(formatSignedCostChange(12.34), '-12.3% savings');
  assert.equal(formatSignedCostChange(0), '0.0% cost');
  assert.equal(formatSignedCostChange(null), '—');
});

test('crossCheckBenchmarks labels 0-run and fixture-only suites as suite present, unmeasured', () => {
  const checked = crossCheckBenchmarks(
    ['BENCH-001', 'BENCH-033', 'BENCH-034'],
    [
      { task_id: 'BENCH-001', total_runs: 6, has_measured_data: true, arms: {} },
      { task_id: 'BENCH-033', total_runs: 4, has_measured_data: false, is_simulation: true, arms: {} },
    ],
    [
      makeRun({ task_id: 'BENCH-001', source_kind: 'live', evidence_status: 'verified' }),
      makeRun({ task_id: 'BENCH-033', source_kind: 'fixture', evidence_status: 'verified' }),
    ],
  );
  assert.deepEqual(checked, [
    { task_id: 'BENCH-001', measured_runs: 1, status: 'measured' },
    { task_id: 'BENCH-033', measured_runs: 0, status: 'suite present, unmeasured' },
    { task_id: 'BENCH-034', measured_runs: 0, status: 'suite present, unmeasured' },
  ]);
});

test('UI components surface preliminary badges, n=, BH FDR, matched ICM-Lite, tokens-primary, and unmeasured suites', () => {
  const Analytics = require('../src/components/workspace/Analytics.tsx').default;
  const { Overview } = require('../src/components/workspace/Overview.tsx');
  const Experiments = require('../src/components/workspace/Experiments.tsx').default;

  const enriched = {
    ...snapshot,
    declared_benchmarks: [
      { task_id: 'BENCH-001', measured_runs: 10, status: 'measured' },
      { task_id: 'BENCH-034', measured_runs: 0, status: 'suite present, unmeasured' },
    ],
  };

  const analyticsHtml = renderToStaticMarkup(React.createElement(Analytics, { data: enriched }));
  assert.match(analyticsHtml, /evaluator_hash/);
  assert.match(analyticsHtml, /Benjamini-Hochberg FDR/);
  assert.match(analyticsHtml, /exploratory/);
  assert.match(analyticsHtml, /preliminary \(n=/);
  assert.match(analyticsHtml, /Tokens/);
  assert.match(analyticsHtml, /ICM-Lite vs Baseline \(matched shared tasks only\)/);

  const overviewHtml = renderToStaticMarkup(React.createElement(Overview, { data: enriched }));
  assert.match(overviewHtml, /-1\.5% savings/);
  assert.match(overviewHtml, /macro_average/);
  assert.match(overviewHtml, /suite present, unmeasured/);

  const experimentsHtml = renderToStaticMarkup(React.createElement(Experiments, { data: enriched }));
  assert.match(experimentsHtml, /BENCH-034/);
  assert.match(experimentsHtml, /suite present, unmeasured/);
});
