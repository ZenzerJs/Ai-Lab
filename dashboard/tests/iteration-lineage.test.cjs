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

const { formatArm, formatDecimal, formatPercent } = require('../src/lib/formatters.ts');
const { selectGovernedArmName } = require('../src/lib/workspace.ts');
const {
  computeParetoFrontier,
  lineageEdges,
  resolveLineageModels,
} = require('../src/lib/lineage.ts');
const IterationLineage = require('../src/components/workspace/IterationLineage.tsx').default;
const AdaptiveICM = require('../src/components/workspace/AdaptiveICM.tsx').default;
const Evidence = require('../src/components/workspace/Evidence.tsx').default;
const { RawLedgerTable } = require('../src/components/RawLedgerTable.tsx');

const snapshot = JSON.parse(
  fs.readFileSync(path.join(__dirname, '../public/data.json'), 'utf8'),
);

const makeRun = (overrides) => ({
  id: 1,
  task_id: 'BENCH-001',
  arm: 'baseline',
  model: 'gemini-3.8-flash-low',
  run_index: 1,
  timestamp: '2026-11-22T00:00:00Z',
  input_tokens: 1000,
  output_tokens: 200,
  thinking_tokens: 0,
  cache_read_tokens: 4000,
  total_tokens: 1200,
  num_turns: 4,
  duration_seconds: 12,
  cost_usd: 0.05,
  cost_status: 'usage_estimate',
  source_kind: 'live',
  evidence_status: 'verified',
  is_simulation: 0,
  is_comparison_eligible: true,
  verification_status: 'passed',
  tool_calls_count: 8,
  ...overrides,
});

test('formatArm, formatPercent, formatDecimal, and governed arm selection support v2/v3/staged', () => {
  assert.equal(formatArm('icm_v1'), 'ICM v1');
  assert.equal(formatArm('icm_v2'), 'ICM v2');
  assert.equal(formatArm('icm_v3'), 'ICM v3');
  assert.equal(formatArm('icm_staged'), 'ICM Staged');
  assert.equal(formatPercent(85.24, 1), '85.2%');
  assert.equal(formatPercent(null), '—');
  assert.equal(formatPercent(Number.NaN), '—');
  assert.equal(formatDecimal(12.34, 1), '12.3');
  assert.equal(formatDecimal(undefined), '—');

  assert.equal(selectGovernedArmName({ baseline: {}, icm_v3: {}, icm_lite: {} }), 'icm_v3');
  assert.equal(selectGovernedArmName({ baseline: {}, icm_staged: {}, icm_lite: {} }), 'icm_staged');
  assert.equal(selectGovernedArmName({ baseline: {}, icm_v2: {}, icm_lite: {} }), 'icm_v2');
});

test('resolveLineageModels derives priced and unpriced model cohorts from the 790-run snapshot', () => {
  const cohorts = resolveLineageModels(snapshot);
  assert.ok(cohorts.length >= 7);

  const firstUnpricedIdx = cohorts.findIndex((c) => !c.hasPricing);
  assert.ok(firstUnpricedIdx > 0, 'priced cohorts must precede unpriced cohorts');
  assert.ok(cohorts.slice(0, firstUnpricedIdx).every((c) => c.hasPricing));
  assert.ok(cohorts.slice(firstUnpricedIdx).every((c) => !c.hasPricing));

  const neon = cohorts.find((c) => c.model === 'gemini-4-neon-devin');
  assert.ok(neon);
  assert.equal(neon.hasPricing, false);
  assert.deepEqual(
    neon.points.map((p) => p.version),
    ['baseline', 'icm_v1', 'icm_v2', 'icm_lite'],
  );
  for (const p of neon.points) {
    assert.equal(p.mean_cost_usd, null);
    assert.equal(p.cost_per_passing_patch_usd, null);
    assert.ok(p.mean_tools !== null && p.mean_tools > 0);
  }

  const flash = cohorts.find((c) => c.model === 'gemini-3.8-flash-low');
  assert.ok(flash);
  assert.equal(flash.hasPricing, true);
  assert.ok(
    flash.points.some((p) => p.version === 'icm_v3' && p.n_runs === 8),
    'gemini-3.8-flash-low must surface the 8 live icm_v3 runs',
  );
  assert.equal(
    flash.points.reduce((sum, p) => sum + p.n_runs, 0),
    58,
    'imported runs must be excluded from live lineage counts',
  );
});

test('REP-06: cost_per_passing_patch_usd is strictly null when zero priced runs pass', () => {
  const payload = {
    ...snapshot,
    iteration_lineage: undefined,
    runs: [
      makeRun({ id: 1, arm: 'baseline', cost_usd: 0.1, verification_status: 'failed' }),
      makeRun({ id: 2, arm: 'icm', cost_usd: 0.08, verification_status: 'passed' }),
    ],
  };
  const cohorts = resolveLineageModels(payload);
  assert.equal(cohorts.length, 1);
  const base = cohorts[0].points.find((p) => p.version === 'baseline');
  const v1 = cohorts[0].points.find((p) => p.version === 'icm_v1');
  assert.equal(base.passed_count, 0);
  assert.equal(base.mean_cost_usd, 0.1);
  assert.equal(base.cost_per_passing_patch_usd, null);
  assert.equal(v1.cost_per_passing_patch_usd, 0.08);
});

test('computeParetoFrontier and lineageEdges enforce non-domination and ordered transitions', () => {
  const points = [
    { version: 'baseline', pass_rate: 0.7, mean_cost_usd: 0.2 },
    { version: 'icm_v1', pass_rate: 0.7, mean_cost_usd: 0.25 }, // dominated by baseline
    { version: 'icm_v2', pass_rate: 0.85, mean_cost_usd: 0.18 }, // dominates baseline
    { version: 'icm_v3', pass_rate: 0.9, mean_cost_usd: 0.22 }, // higher cost, higher pass -> Pareto
    { version: 'icm_staged', pass_rate: 0.9, mean_cost_usd: null }, // null x -> ignored
    { version: 'icm_lite', pass_rate: 0.65, mean_cost_usd: 0.09 }, // cheaper -> Pareto
  ];
  const frontier = computeParetoFrontier(points, (p) => p.mean_cost_usd);
  assert.deepEqual(Array.from(frontier).sort(), ['icm_lite', 'icm_v2', 'icm_v3']);

  const edges = lineageEdges(points);
  assert.deepEqual(
    edges.map((e) => `${e.from}->${e.to}:${e.kind}`),
    [
      'baseline->icm_v1:spine',
      'icm_v1->icm_v2:spine',
      'icm_v2->icm_v3:spine',
      'icm_v3->icm_staged:spine',
      'icm_v1->icm_lite:branch',
    ],
  );
});

test('resolveLineageModels consumes populated iteration_lineage payload and enriches from runs', () => {
  const payload = {
    ...snapshot,
    runs: [
      makeRun({
        id: 101,
        arm: 'icm_v3',
        contract_version: 'icm_v3',
        llm_calls_count: 3,
        tools_per_llm_call: 2.5,
        cache_bust_count: 0,
        tool_calls_count: 7,
      }),
    ],
    iteration_lineage: {
      has_data: true,
      contracts: [
        {
          id: 'icm_v3',
          hypothesis: 'Batch-first 3-turn cadence.',
          changes_from_prev: ['Static AST prefix'],
          parent_version: 'icm_v2',
          execution_strategy: 'single_session',
        },
      ],
      versions: [
        {
          version: 'icm_v3',
          arm: 'icm_v3',
          model: 'gemini-3.8-flash-low',
          n_runs: 1,
          passed_count: 1,
          pass_rate: 1.0,
          priced_n_runs: 1,
          mean_cost_usd: 0.04,
          cost_per_passing_patch_usd: 0.04,
          mean_llm_calls: 3.0,
          mean_cache_hit_ratio: 0.8,
          mean_tools_per_call: 2.5,
          total_cache_busts: 0,
          cost_delta_vs_baseline_pct: -20.0,
        },
      ],
    },
  };
  const cohorts = resolveLineageModels(payload);
  assert.equal(cohorts.length, 1);
  assert.equal(cohorts[0].points[0].label, 'ICM v3');
  assert.equal(cohorts[0].points[0].hypothesis, 'Batch-first 3-turn cadence.');
  assert.equal(cohorts[0].points[0].mean_tools, 7);
});

test('IterationLineage SSR renders snapshot, unpriced tool fallback, and empty state cleanly', () => {
  const html = renderToStaticMarkup(React.createElement(IterationLineage, { data: snapshot }));
  assert.match(html, /ITERATION LINEAGE/);
  assert.match(html, /Pareto frontier/);
  assert.match(html, /gemini-3\.8-flash-low/);
  assert.match(html, /Cost \/ Verified Pass/);
  assert.doesNotMatch(html, />icm_lite</);

  const unpricedOnly = {
    ...snapshot,
    iteration_lineage: undefined,
    runs: snapshot.runs.filter((r) => r.model === 'gemini-4-neon-devin'),
  };
  const unpricedHtml = renderToStaticMarkup(
    React.createElement(IterationLineage, { data: unpricedOnly }),
  );
  assert.match(unpricedHtml, /Avg Tool Calls \(no USD rate\)/);
  assert.match(unpricedHtml, /ICM v2/);

  const emptyHtml = renderToStaticMarkup(
    React.createElement(IterationLineage, { data: { ...snapshot, iteration_lineage: undefined, runs: [] } }),
  );
  assert.match(emptyHtml, /Iteration lineage starts with verified runs/);
});

test('AdaptiveICM documents 3-tier routing and Evidence / RawLedgerTable include contract & cache columns', () => {
  const adaptiveHtml = renderToStaticMarkup(React.createElement(AdaptiveICM, { data: snapshot }));
  assert.match(adaptiveHtml, /ICM-Lite/);
  assert.match(adaptiveHtml, /ICM v3/);
  assert.match(adaptiveHtml, /ICM Staged/);
  assert.match(adaptiveHtml, /13–50 files/);
  assert.match(adaptiveHtml, /&gt;50 files/);

  const customRuns = [
    makeRun({
      id: 901,
      arm: 'icm_v3',
      contract_version: 'icm_v3',
      contract_hash: 'abcdef123456',
      llm_calls_count: 3,
      cache_bust_count: 1,
    }),
    makeRun({
      id: 902,
      arm: 'baseline',
      contract_version: null,
      llm_calls_count: null,
      cache_bust_count: null,
      input_tokens: 0,
      cache_read_tokens: 0,
    }),
  ];

  const evidenceHtml = renderToStaticMarkup(
    React.createElement(Evidence, { data: { ...snapshot, runs: customRuns } }),
  );
  assert.match(evidenceHtml, />Contract</);
  assert.match(evidenceHtml, />LLM Calls</);
  assert.match(evidenceHtml, />Cache Hit %</);
  assert.match(evidenceHtml, />Cache Busts</);
  assert.match(evidenceHtml, /ICM v3/);
  assert.match(evidenceHtml, /80\.0%/);

  const ledgerHtml = renderToStaticMarkup(
    React.createElement(RawLedgerTable, { runs: customRuns }),
  );
  assert.match(ledgerHtml, />Contract</);
  assert.match(ledgerHtml, />LLM Calls</);
  assert.match(ledgerHtml, />Cache Hit %</);
  assert.match(ledgerHtml, />Cache Busts</);
  assert.match(ledgerHtml, /ICM v3/);
});
