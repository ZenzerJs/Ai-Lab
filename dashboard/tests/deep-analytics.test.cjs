const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { test } = require('node:test');
const { buildSync } = require('esbuild');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');

// Exercise the production TypeScript directly without a second test dependency.
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
  isPricedRun,
  scopeRuns,
  pricedShare,
  modelFamily,
  modelFamilySummaries,
  suitePairs,
  pairedDiffStats,
  computeIdealZoneMetrics,
} = require('../src/lib/analytics.ts');
const snapshot = JSON.parse(fs.readFileSync(path.join(__dirname, '../public/data.json'), 'utf8'));

const run = (overrides) => ({
  id: 1,
  task_id: 'TEST-001',
  arm: 'baseline',
  model: 'claude-sonnet-5-5-low',
  run_index: 1,
  timestamp: '2026-01-01T00:00:00Z',
  input_tokens: 100,
  output_tokens: 10,
  thinking_tokens: 0,
  cache_read_tokens: 0,
  total_tokens: 110,
  num_turns: 3,
  duration_seconds: 12,
  cost_usd: 0.01,
  cost_status: 'usage_estimate',
  source_kind: 'live',
  is_comparison_eligible: true,
  verification_status: 'passed',
  ...overrides,
});

test('isPricedRun and scopeRuns split cost-complete runs from unpriced scale runs', () => {
  const runs = [
    run({ id: 1, cost_usd: 0.01 }),
    run({ id: 2, cost_usd: null, cost_status: 'unavailable' }),
    run({ id: 3, cost_usd: 0 }),
  ];
  assert.deepEqual(runs.map(isPricedRun), [true, false, true]);
  assert.deepEqual(scopeRuns(runs, 'all').length, 3);
  assert.deepEqual(scopeRuns(runs, 'priced').map((r) => r.id), [1, 3]);
  assert.deepEqual(scopeRuns(runs, 'unpriced').map((r) => r.id), [2]);
  assert.equal(pricedShare(runs), (2 / 3) * 100);
  assert.equal(pricedShare([]), null);
});

test('the published snapshot cleanly splits priced and unpriced runs', () => {
  const priced = scopeRuns(snapshot.runs, 'priced');
  const unpriced = scopeRuns(snapshot.runs, 'unpriced');
  // The snapshot grows as batches land, so assert the split contract rather
  // than absolute counts: every run is priced iff it reports a finite cost.
  assert.ok(priced.length > 0);
  assert.ok(unpriced.length > 0);
  assert.equal(priced.length + unpriced.length, snapshot.runs.length);
  assert.ok(priced.every((r) => Number.isFinite(r.cost_usd)));
  assert.ok(unpriced.every((r) => !Number.isFinite(r.cost_usd)));
  assert.equal(pricedShare(snapshot.runs), (priced.length / snapshot.runs.length) * 100);
});

test('modelFamily groups models by vendor prefix', () => {
  assert.equal(modelFamily('claude-sonnet-5-5-low'), 'claude');
  assert.equal(modelFamily('gemini-4-hydrogen-low'), 'gemini');
  assert.equal(modelFamily('swe-2-max-lightning'), 'swe');
  assert.equal(modelFamily('gpt-6.2-astra'), 'gpt');
  assert.equal(modelFamily(''), 'unknown');
  assert.equal(modelFamily(null), 'unknown');
});

test('modelFamilySummaries aggregates pass rates, tokens, and priced spend per family', () => {
  const runs = [
    run({ id: 1, model: 'alpha-1', arm: 'baseline', cost_usd: 0.1, total_tokens: 1000 }),
    run({ id: 2, model: 'alpha-1', arm: 'icm', cost_usd: 0.05, total_tokens: 800 }),
    run({ id: 3, model: 'beta-2', arm: 'baseline', cost_usd: null, cost_status: 'unavailable', total_tokens: 500 }),
    run({ id: 4, model: 'beta-2', arm: 'icm', cost_usd: null, cost_status: 'unavailable', total_tokens: 400 }),
    run({ id: 5, model: 'beta-2', arm: 'icm', source_kind: 'imported', cost_usd: null }),
  ];
  const all = modelFamilySummaries(runs, 'all');
  const alpha = all.find((f) => f.family === 'alpha');
  const beta = all.find((f) => f.family === 'beta');
  assert.equal(all.length, 2);
  assert.equal(alpha.pricedRuns, 2);
  assert.equal(alpha.savingsPct, 50);
  assert.equal(alpha.tokenDeltaPct, 20);
  assert.equal(beta.pricedRuns, 0);
  assert.equal(beta.runs, 2); // imported run excluded
  assert.equal(beta.savingsPct, null);
  assert.equal(beta.tokenDeltaPct, 20);
  const priced = modelFamilySummaries(runs, 'priced');
  assert.deepEqual(priced.map((f) => f.family), ['alpha']);
  const unpriced = modelFamilySummaries(runs, 'unpriced');
  assert.deepEqual(unpriced.map((f) => f.family), ['beta']);
});

test('suitePairs matches baseline and governed runs by run_index on a metric', () => {
  const task = {
    task_id: 'TEST-001',
    arms: {
      baseline: {
        runs: [
          run({ id: 1, run_index: 1, cost_usd: 0.1 }),
          run({ id: 2, run_index: 2, cost_usd: 0.2 }),
          run({ id: 3, run_index: 3, cost_usd: 0.3, is_comparison_eligible: false }),
        ],
      },
      icm: {
        runs: [
          run({ id: 4, arm: 'icm', run_index: 1, cost_usd: 0.05 }),
          run({ id: 5, arm: 'icm', run_index: 2, cost_usd: null, cost_status: 'unavailable' }),
          run({ id: 6, arm: 'icm', run_index: 3, cost_usd: 0.1 }),
          run({ id: 7, arm: 'icm', run_index: 4, cost_usd: 0.4 }), // no baseline pair
        ],
      },
    },
    // Unpriced scale runs and failed attempts live in excluded_runs.
    excluded_runs: [
      run({ id: 8, arm: 'baseline', run_index: 5, cost_usd: null, cost_status: 'unavailable', is_comparison_eligible: false }),
      run({ id: 9, arm: 'icm', run_index: 5, cost_usd: null, cost_status: 'unavailable', is_comparison_eligible: false }),
      run({ id: 10, arm: 'icm', run_index: 6, cost_usd: 0.9, verification_status: 'failed', is_comparison_eligible: false }),
      // Superseded imported attempts must never pair.
      run({ id: 11, arm: 'baseline', run_index: 7, cost_usd: 0.5, source_kind: 'imported', is_comparison_eligible: false }),
      run({ id: 12, arm: 'icm', run_index: 7, cost_usd: 0.1, source_kind: 'imported', is_comparison_eligible: false }),
    ],
  };
  assert.deepEqual(suitePairs(task, 'icm'), [[0.1, 0.05], [0.3, 0.1]]);
  // Token metric pairs runs with or without costs, including excluded_runs.
  const tokenPairs = suitePairs(task, 'icm', (r) => r.total_tokens);
  assert.deepEqual(tokenPairs, [[110, 110], [110, 110], [110, 110], [110, 110]]);
  // Scope isolates the pool: unpriced keeps only the excluded_runs pair.
  assert.deepEqual(
    suitePairs(task, 'icm', (r) => r.total_tokens, 'unpriced'),
    [[110, 110]],
  );
  // Priced scope picks up priced attempts even when excluded (failed).
  assert.deepEqual(suitePairs(task, 'icm', undefined, 'priced'), [
    [0.1, 0.05],
    [0.3, 0.1],
  ]);
  assert.equal(suitePairs(task, 'missing').length, 0);
});

test('pairedDiffStats reports CI, Cohen dz, effect size, and significance', () => {
  const stats = pairedDiffStats([[10, 8], [20, 15], [15, 11], [12, 9]]);
  assert.equal(stats.n, 4);
  assert.ok(stats.meanDeltaPct < 0); // governed cheaper → negative delta
  assert.ok(stats.ci95[0] <= stats.meanDeltaPct && stats.meanDeltaPct <= stats.ci95[1]);
  assert.ok(stats.cohensDz > 0.8); // consistent reductions → large effect
  assert.equal(stats.effectSize, 'large');
  assert.equal(stats.significant, true);

  const flat = pairedDiffStats([[10, 10], [10, 10]]);
  assert.equal(flat.cohensDz, null); // zero variance
  assert.equal(flat.effectSize, null);

  const mixed = pairedDiffStats([[10, 9], [10, 11]]);
  assert.ok(mixed.ci95[0] < 0 && mixed.ci95[1] > 0);
  assert.equal(mixed.significant, false);

  assert.equal(pairedDiffStats([]), null);
});

test('every governed arm of every published suite yields a stats object or nothing', () => {
  for (const task of snapshot.tasks) {
    for (const name of Object.keys(task.arms).filter((n) => n !== 'baseline')) {
      const stats = pairedDiffStats(suitePairs(task, name));
      if (stats) {
        assert.ok(stats.n >= 1);
        assert.ok(stats.meanBaseline >= 0);
        if (stats.meanBaseline === 0) {
          assert.equal(stats.meanDeltaPct, null);
        }
      }
    }
  }
});

test('Analytics page renders coverage, paired effects, and model families', () => {
  const Analytics = require('../src/components/workspace/Analytics.tsx').default;
  const markup = renderToStaticMarkup(React.createElement(Analytics, { data: snapshot }));
  assert.match(markup, /Cost coverage/);
  assert.match(markup, /Priced only/);
  assert.match(markup, /Unpriced only/);
  assert.match(markup, /Breakdown by model family/);
  assert.match(markup, /paired effect size/i);
  assert.match(markup, /gemini/);
  assert.match(markup, /swe/);
  assert.match(markup, /significant/);
});

test('Analytics page stays robust on empty and unpriced payloads', () => {
  const Analytics = require('../src/components/workspace/Analytics.tsx').default;
  const empty = renderToStaticMarkup(
    React.createElement(Analytics, {
      data: { ...snapshot, runs: [], tasks: [] },
    }),
  );
  assert.match(empty, /0 runs in scope|0 run in scope/);
  assert.match(empty, /No paired cost runs|No paired/);

  const unpricedOnly = renderToStaticMarkup(
    React.createElement(Analytics, {
      data: {
        ...snapshot,
        runs: snapshot.runs.filter((r) => r.cost_usd == null),
        tasks: snapshot.tasks.map((t) => ({
          ...t,
          excluded_runs: (t.excluded_runs || []).filter(
            (r) => r.cost_usd == null,
          ),
          arms: Object.fromEntries(
            Object.entries(t.arms).map(([n, a]) => [
              n,
              { ...a, runs: (a.runs || []).filter((r) => r.cost_usd == null) },
            ]),
          ),
        })),
      },
    }),
  );
  assert.match(unpricedOnly, /Unpriced only/);
  assert.match(unpricedOnly, /model family/i);
});

test('computeIdealZoneMetrics isolates each ICM tier strictly against matched baseline runs', () => {
  const zones = computeIdealZoneMetrics(snapshot.runs);
  for (const arm of ['icm_lite', 'icm_v3', 'icm_staged']) {
    const z = zones[arm];
    assert.ok(z.matchedSeries > 0, `${arm} has matched series`);
    assert.ok(z.baseRuns >= z.basePassed);
    assert.ok(z.govRuns >= z.govPassed);
    assert.ok(z.toolSavingsPct != null && Number.isFinite(z.toolSavingsPct));
    assert.ok(
      z.costPerPassSavingsPct != null && Number.isFinite(z.costPerPassSavingsPct),
    );
  }
  assert.ok(zones.icm_lite.toolSavingsPct > 0);
  assert.ok(zones.icm_v3.costPerPassSavingsPct > 0);
  assert.ok(zones.icm_staged.passDeltaPp > 0);

  const liteOnly = snapshot.runs.filter(
    (r) => r.arm === 'baseline' || r.arm === 'icm_lite',
  );
  const isolated = computeIdealZoneMetrics(liteOnly);
  assert.ok(isolated.icm_lite.matchedSeries > 0);
  assert.equal(isolated.icm_v3.matchedSeries, 0);
  assert.equal(isolated.icm_v3.govRuns, 0);
  assert.equal(isolated.icm_staged.matchedSeries, 0);
  assert.equal(isolated.icm_staged.govRuns, 0);
});
