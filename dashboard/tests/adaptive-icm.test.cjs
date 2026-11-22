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

const { formatArm } = require('../src/lib/formatters.ts');
const { governedArm, governedArmName, selectGovernedArmName } = require('../src/lib/workspace.ts');
const { deriveDataForModel } = require('../src/lib/recalculate.ts');
const snapshot = JSON.parse(fs.readFileSync(path.join(__dirname, '../public/data.json'), 'utf8'));

test('labels are friendly while unknown arm IDs stay readable', () => {
  for (const [id, label] of Object.entries({
    baseline: 'Baseline', icm: 'ICM', icm_lite: 'ICM-Lite',
    'icm-subagents': 'ICM + subagents', delegation: 'Delegation', future_arm: 'future_arm',
  })) assert.equal(formatArm(id), label);
});

test('governed selection honors Lite explicitly and preserves legacy precedence', () => {
  const lite = { mean_cost_usd: 1 };
  const task = { governed_arm: 'icm_lite', arms: { baseline: {}, icm: {}, icm_lite: lite } };
  assert.equal(governedArmName(task), 'icm_lite');
  assert.equal(governedArm(task), lite);
  assert.equal(selectGovernedArmName(task.arms), 'icm');
  assert.equal(selectGovernedArmName({ baseline: {}, icm_lite: lite }), 'icm_lite');
  assert.equal(selectGovernedArmName({ baseline: {}, icm: undefined, icm_lite: lite }, 'missing'), 'icm_lite');
  assert.equal(selectGovernedArmName({ baseline: {} }, 'baseline'), undefined);
  assert.equal(selectGovernedArmName({ baseline: {}, custom: {} }), 'custom');
});

test('the published snapshot still resolves its original governed comparisons', () => {
  assert.equal(snapshot.runs.length, 722);
  assert.equal(snapshot.runs.filter((r) => r.arm === 'icm_lite').length, 52);
  assert.equal(snapshot.runs.filter((r) => r.arm === 'icm_v2').length, 30);
  for (const task of snapshot.tasks) {
    const arm = governedArmName(task);
    assert.ok(arm === 'icm' || arm === 'icm_lite' || arm === 'icm_v2');
    assert.equal(governedArm(task), task.arms[arm]);
  }
});

test('simulation uses the same explicitly selected Lite arm in savings and timeline', () => {
  const run = (arm, input) => ({
    id: input, task_id: 'TEST-001', run_index: 1, arm, model: 'original',
    input_tokens: input, output_tokens: 0, cache_read_tokens: 0,
    total_tokens: input, cost_usd: input, cost_status: 'complete', is_comparison_eligible: true,
  });
  const runs = [run('baseline', 100), run('icm', 80), run('icm_lite', 20)];
  const arms = Object.fromEntries(runs.map((r) => [r.arm, {
    mean_cost_usd: r.cost_usd, mean_total_tokens: r.total_tokens, runs: [r],
  }]));
  const data = {
    ...snapshot, runs,
    tasks: [{ task_id: 'TEST-001', governed_arm: 'icm_lite', arms, savings: {} }],
    pricing: [{ model: 'test-model', input_usd_per_mtok: 1000000, output_usd_per_mtok: 0, cache_read_usd_per_mtok: 0 }],
  };
  const simulated = deriveDataForModel(data, 'test-model');
  assert.equal(simulated.tasks[0].savings.mean_savings_percent, 80);
  assert.equal(simulated.timeline[0].governed_arm, 'icm_lite');
  assert.equal(simulated.timeline[0].icm_cost_usd, 20);
  assert.equal(data.runs[2].arm, 'icm_lite');
});

test('simulation honors mixed governed arms across tasks in one dataset', () => {
  const run = (task_id, arm, input) => ({
    id: `${task_id}-${arm}`, task_id, run_index: 1, arm, model: 'original',
    input_tokens: input, output_tokens: 0, cache_read_tokens: 0,
    total_tokens: input, cost_usd: input, cost_status: 'complete', is_comparison_eligible: true,
  });
  const runs = [
    run('HEAVY-001', 'baseline', 100), run('HEAVY-001', 'icm', 60),
    run('MICRO-001', 'baseline', 50), run('MICRO-001', 'icm_lite', 40),
  ];
  const task = (task_id, governed_arm, base, gov) => ({
    task_id, governed_arm, savings: {},
    arms: {
      baseline: { mean_cost_usd: base, mean_total_tokens: base, runs: [run(task_id, 'baseline', base)] },
      [governed_arm]: { mean_cost_usd: gov, mean_total_tokens: gov, runs: [run(task_id, governed_arm, gov)] },
    },
  });
  const data = {
    ...snapshot, runs,
    tasks: [task('HEAVY-001', 'icm', 100, 60), task('MICRO-001', 'icm_lite', 50, 40)],
    pricing: [{ model: 'test-model', input_usd_per_mtok: 1000000, output_usd_per_mtok: 0, cache_read_usd_per_mtok: 0 }],
  };
  const simulated = deriveDataForModel(data, 'test-model');
  assert.equal(simulated.tasks[0].savings.mean_savings_percent, 40);
  assert.equal(simulated.tasks[1].savings.mean_savings_percent, 20);
  assert.deepEqual(simulated.timeline.map((p) => p.governed_arm), ['icm', 'icm_lite']);
  assert.equal(simulated.cumulative.cumulative_savings_usd, 50);
});

test('routing callout describes policy boundaries as deterministic routing rules', () => {
  const AdaptiveICM = require('../src/components/workspace/AdaptiveICM.tsx').default;
  const markup = renderToStaticMarkup(React.createElement(AdaptiveICM));
  assert.match(markup, /ICM-Lite/);
  assert.match(markup, /&lt;150 LOC <strong>and<\/strong> exactly 1 target file/);
  assert.match(markup, /≥150 LOC <strong>or<\/strong> 2\+ target files/);
  assert.match(markup, /Unknown scope defaults here/);
  assert.match(markup, /not a guarantee of savings/);
});

test('all three workspace views render old and Lite payloads without changing raw IDs', () => {
  const lite = structuredClone(snapshot);
  for (const task of lite.tasks) {
    task.governed_arm = 'icm_lite';
    task.arms.icm_lite = task.arms.icm;
    delete task.arms.icm;
  }
  for (const run of lite.runs) if (run.arm === 'icm') run.arm = 'icm_lite';
  const original = JSON.stringify(lite);
  for (const name of ['Overview', 'Experiments', 'Evidence']) {
    const view = require(`../src/components/workspace/${name}.tsx`);
    const Component = view.default || view[name];
    assert.ok(renderToStaticMarkup(React.createElement(Component, { data: snapshot })).includes('Baseline'));
    const markup = renderToStaticMarkup(React.createElement(Component, { data: lite }));
    assert.match(markup, /ICM-Lite/);
    assert.doesNotMatch(markup, />icm_lite</);
    if (name === 'Overview') {
      // Keep badges out of the fixed-width numeric gutter at full-length bars.
      assert.match(markup, /chart-arm-badge/);
      assert.doesNotMatch(markup, /class="bar-value"><span class="badge/);
    }
  }
  assert.equal(JSON.stringify(lite), original);
});
