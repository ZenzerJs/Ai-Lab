"""
tests/unit/test_hardening_phase3_4.py - Regression Suite for Phase 3/4 Hardening Findings

Tests cover:
1. Campaign eligibility reuses ledger rules: fixtures and simulations never count as measured data.
2. Success-rate denominators: attempt-level success rate divides by executed attempts, reporting
   attempt_success_rate, evaluated_success_rate, and evaluation_coverage.
3. Cost per success: includes known failure/timeout spend, distinguishes complete vs partial
   observed cost, and discloses missing spend.
4. Manifest integrity: enforces manifest hash validation, rejects missing/corrupted hash in strict mode,
   matches explicit slot IDs, and flags duplicates / unscheduled attempts.
5. BENCH-006 mutation grading: requires clean collection and actual test failures; classifies
   collection errors and infrastructure timeouts separately; uses disposable workspaces.
6. Cache condition: distinguishes intended_cache_condition vs observed_cache_condition
   (defaulting to 'unknown' unless observed).
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import pytest
import sqlite3
import subprocess
import sys

import campaign
import ledger
import runner

WORKSPACE_ROOT = runner.WORKSPACE_ROOT


# ---------------------------------------------------------------------------
# Finding 1: Fixtures and simulations cannot satisfy measured-data eligibility
# ---------------------------------------------------------------------------

def test_campaign_fixtures_and_simulations_not_measured_data(tmp_path: Path):
    """
    Finding 1: Campaign eligibility must reuse ledger rules.
    Fixtures and simulations cannot satisfy has_measured_data=True even if completed with cost.
    Demo reports retain demo statistics, but has_measured_data remains False.
    """
    manifest = campaign.plan_campaign(
        tasks=["BENCH-001"],
        arms=["baseline", "icm"],
        repetitions=1,
        random_seed=42,
    )
    # Simulate completed executions as fixtures
    base_slot = next(s for s in manifest.slots if s.arm == "baseline")
    icm_slot = next(s for s in manifest.slots if s.arm == "icm")
    campaign.simulate_slot_execution(base_slot, outcome="completed", passed=True, cost_usd=0.05)
    campaign.simulate_slot_execution(icm_slot, outcome="completed", passed=True, cost_usd=0.03)

    assert base_slot.source_kind == "fixture"
    assert base_slot.is_simulation == 0

    report = campaign.generate_campaign_report(manifest=manifest)

    # 1. has_measured_data must be False for fixture/mock runs
    assert report["has_measured_data"] is False

    # 2. Demo stats are still computed so reports remain useful
    assert report["total_scheduled"] == 2
    assert report["total_executed"] == 2
    assert report["pooled_summary"]["arms"]["baseline"]["sample_count"] == 1
    assert report["pooled_summary"]["arms"]["baseline"]["mean_cost_usd"] == 0.05
    assert report["pooled_summary"]["arms"]["icm"]["mean_cost_usd"] == 0.03

    # 3. If a slot is live and verified with matching evidence hash, has_measured_data becomes True
    ev_file = tmp_path / "stdout.log"
    ev_file.write_text("live execution output", encoding="utf-8")
    ev_hash = hashlib.sha256(ev_file.read_bytes()).hexdigest()

    base_slot.source_kind = "live"
    base_slot.evidence_status = "verified"
    base_slot.evidence_ref = str(ev_file)
    base_slot.evidence_hash = ev_hash

    report_live = campaign.generate_campaign_report(manifest=manifest)
    assert report_live["has_measured_data"] is True


# ---------------------------------------------------------------------------
# Finding 2: Success-rate denominators omit attempts
# ---------------------------------------------------------------------------

def test_success_rate_denominators_include_all_executed_attempts():
    """
    Finding 2: _compute_arm_metrics() must divide successes by executed attempts,
    not merely evaluated slots.
    Reports: executed_attempts_count, attempt_success_rate, evaluated_success_rate, evaluation_coverage.
    """
    # Arm with 2 executed attempts:
    # Attempt 1: completed and passed evaluation
    # Attempt 2: timed out, verification_status="not_run" (unevaluated)
    slot1 = campaign.CampaignSlot(
        slot_id="s1", campaign_id="cmp_denom", task_id="BENCH-001",
        task_version="1.0.0", repetition_index=1, arm="baseline", planned_order=1,
        status="completed", verification_status="passed", input_tokens=1000, output_tokens=100, cost_usd=0.01,
    )
    slot2 = campaign.CampaignSlot(
        slot_id="s2", campaign_id="cmp_denom", task_id="BENCH-001",
        task_version="1.0.0", repetition_index=2, arm="baseline", planned_order=2,
        status="timed_out", verification_status="not_run", input_tokens=500, output_tokens=50, cost_usd=0.005,
    )

    report = campaign.generate_campaign_report(slots=[slot1, slot2])
    arm_stats = report["pooled_summary"]["arms"]["baseline"]

    # Executed attempts = 2 (completed + timed_out)
    assert arm_stats["executed_attempts_count"] == 2
    assert arm_stats["n_executed"] == 2
    assert arm_stats["passed_count"] == 1

    # Attempt-level success rate: 1 pass / 2 executed attempts = 0.50 (50%)
    assert arm_stats["attempt_success_rate"] == 0.5
    assert arm_stats["verified_success_rate"] == 0.5

    # Evaluated-only rate: 1 pass / 1 evaluated = 1.0 (100%)
    assert arm_stats["evaluated_success_rate"] == 1.0

    # Evaluation coverage: 1 evaluated / 2 executed = 0.50 (50%)
    assert arm_stats["evaluation_coverage"] == 0.5


# ---------------------------------------------------------------------------
# Finding 3: Cost per success must include failed-attempt spend & disclose missing spend
# ---------------------------------------------------------------------------

def test_cost_per_success_includes_failure_spend_and_discloses_missing():
    """
    Finding 3: Known failure/timeout spend must be included in cost per success.
    Distinguishes complete cost per success from partial observed cost.
    Discloses missing spend when successful runs lack cost data.
    """
    # Scenario A: 1 passed run ($0.06), 1 timed-out run ($0.04 with known token spend)
    # Total arm spend to achieve 1 success = $0.10. Cost per success must be $0.10.
    slot_pass = campaign.CampaignSlot(
        slot_id="sp", campaign_id="cmp_spend", task_id="BENCH-001",
        task_version="1.0.0", repetition_index=1, arm="baseline", planned_order=1,
        status="completed", verification_status="passed", input_tokens=6000, output_tokens=300,
        cost_usd=0.06, cost_status="usage_estimate",
    )
    slot_timeout = campaign.CampaignSlot(
        slot_id="st", campaign_id="cmp_spend", task_id="BENCH-001",
        task_version="1.0.0", repetition_index=2, arm="baseline", planned_order=2,
        status="timed_out", verification_status="failed", input_tokens=4000, output_tokens=100,
        cost_usd=0.04, cost_status="usage_estimate",
    )

    report_a = campaign.generate_campaign_report(slots=[slot_pass, slot_timeout])
    arm_a = report_a["pooled_summary"]["arms"]["baseline"]

    # Must include the $0.04 failure spend: (0.06 + 0.04) / 1 success = 0.10
    assert pytest.approx(arm_a["cost_per_success"], rel=1e-5) == 0.10
    assert arm_a["cost_per_success_type"] == "complete"
    assert arm_a["has_missing_spend"] is False

    # Scenario B: 2 passed runs, but 1 has missing telemetry (cost_usd=None)
    slot_pass2 = campaign.CampaignSlot(
        slot_id="sp2", campaign_id="cmp_spend", task_id="BENCH-001",
        task_version="1.0.0", repetition_index=2, arm="baseline", planned_order=2,
        status="completed", verification_status="passed", input_tokens=None, output_tokens=None,
        cost_usd=None, cost_status="unavailable", exclusion_reasons=["missing_usage_telemetry"],
    )
    report_b = campaign.generate_campaign_report(slots=[slot_pass, slot_pass2])
    arm_b = report_b["pooled_summary"]["arms"]["baseline"]

    # Must be marked partial_observed, disclosing missing spend
    assert arm_b["has_missing_spend"] is True
    assert arm_b["cost_per_success_type"] == "partial_observed"
    assert arm_b["missing_cost_sample_count"] == 1


# ---------------------------------------------------------------------------
# Finding 4: Manifest integrity and schedule reconciliation enforcement
# ---------------------------------------------------------------------------

def test_manifest_integrity_validation_and_reconciliation(tmp_path: Path):
    """
    Finding 4: Validate supplied manifest hash before reporting;
    reject missing/corrupted hashes in strict mode; match explicit slot IDs;
    flag duplicates and unscheduled attempts rather than silently incorporating them.
    """
    manifest = campaign.plan_campaign(
        tasks=["BENCH-001"],
        arms=["baseline", "icm"],
        repetitions=1,
        random_seed=42,
    )

    # 1. Corrupted manifest hash must fail verification
    corrupted_manifest = copy.deepcopy(manifest)
    corrupted_manifest.manifest_hash = "corrupted_hash_" + "0" * 49
    with pytest.raises(ValueError, match="integrity"):
        campaign.generate_campaign_report(manifest=corrupted_manifest, strict_manifest=True)

    # 2. Loading manifest from dict without hash does not auto-generate hash when loaded
    m_dict = manifest.to_dict()
    del m_dict["manifest_hash"]
    loaded_no_hash = campaign.CampaignManifest.from_dict(m_dict)
    assert loaded_no_hash.manifest_hash == ""
    assert loaded_no_hash.verify_integrity() is False

    with pytest.raises(ValueError, match="hash"):
        campaign.generate_campaign_report(manifest=loaded_no_hash, strict_manifest=True)

    # 3. Reconciliation flags duplicate runs and unscheduled runs
    slot0_id = manifest.slots[0].slot_id
    db_file = tmp_path / "recon_test.db"
    conn = ledger.get_connection(db_file)

    # Record 2 runs for slot0 (a duplicate!) and 1 unscheduled run
    run1 = manifest.slots[0].to_ledger_run()
    run1["cost_usd"] = 0.05
    run1["execution_status"] = "completed"
    ledger.record_run(**{k: v for k, v in run1.items() if k != "id"}, conn=conn)

    # Duplicate execution of same slot
    run1_dup = copy.deepcopy(run1)
    run1_dup["cost_usd"] = 0.06
    ledger.record_run(**{k: v for k, v in run1_dup.items() if k != "id"}, conn=conn)

    # Unscheduled run (different task)
    unscheduled = copy.deepcopy(run1)
    unscheduled["task_id"] = "BENCH-999"
    unscheduled["notes"] = json.dumps({"slot_id": "unscheduled_slot_xyz"})
    ledger.record_run(**{k: v for k, v in unscheduled.items() if k != "id"}, conn=conn)
    conn.close()

    report = campaign.generate_campaign_report(manifest=manifest, db_path=db_file)
    recon = report["reconciliation_issues"]
    assert recon["has_schedule_violations"] is True
    assert len(recon["duplicate_runs"]) == 1
    assert len(recon["unscheduled_runs"]) == 1


# ---------------------------------------------------------------------------
# Finding 5: Mutation grading accepts infrastructure errors in BENCH-006
# ---------------------------------------------------------------------------

def test_bench006_mutation_grading_rejects_collection_errors(tmp_path: Path):
    """
    Finding 5: BENCH-006 must require clean pytest collection (exit code 1 with test failures).
    Collection errors (SyntaxError, pytest usage error) must NOT count as detecting faulty variants;
    they must be classified as infrastructure errors.
    """
    evaluator_file = WORKSPACE_ROOT / "benchmarks" / "BENCH-006" / "evaluator" / "evaluator.py"
    workspace_dir = WORKSPACE_ROOT / "benchmarks" / "BENCH-006" / "workspace"

    # Prepare disposable workspace
    ws = runner.WorkspaceManager.prepare_arm_workspace(
        snapshot_dir=workspace_dir,
        arm="baseline",
        workspace_root=tmp_path / "workspaces",
        run_id="test_b06_infra",
    )

    try:
        # Create a test file with a SyntaxError (causing pytest collection error, not test assertion failure)
        syntax_err_test = ws.path / "tests" / "test_accounting.py"
        syntax_err_test.write_text("def test_broken(:\n    pass\n", encoding="utf-8")

        # Run evaluator directly
        res = subprocess.run(
            [sys.executable, str(evaluator_file)],
            cwd=str(ws.path),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Must fail evaluation!
        assert res.returncode != 0
        # Must NOT report that variants were detected due to syntax error!
        combined_err = res.stderr + "\n" + res.stdout
        assert "ALL CHECKS PASSED" not in combined_err
        # Check that it identifies the failure as genuine failure or infrastructure error
        assert ("tests_failed_against_genuine_implementation" in combined_err
                or "collection_error" in combined_err
                or "infrastructure_error" in combined_err)
    finally:
        ws.cleanup()


# ---------------------------------------------------------------------------
# Finding 7: Cache condition distinction (intended vs observed)
# ---------------------------------------------------------------------------

def test_cache_condition_distinguishes_intended_and_observed():
    """
    Finding 7: Distinguish intended_cache_condition and observed_cache_condition.
    observed_cache_condition must default to 'unknown' unless telemetry confirms it.
    """
    manifest = campaign.plan_campaign(
        tasks=["BENCH-001"],
        arms=["baseline", "icm"],
        repetitions=1,
        cache_conditions=["cold", "warm"],
    )

    warm_slots = [s for s in manifest.slots if s.cache_condition == "warm"]
    assert len(warm_slots) == 2

    for s in warm_slots:
        assert s.intended_cache_condition == "warm"
        # Prior to observation, observed condition must be unknown, NOT assumed warm/cold
        assert s.observed_cache_condition == "unknown"

    report = campaign.generate_campaign_report(manifest=manifest)
    strata = report["strata"]
    assert "warm" in strata
    assert "cold" in strata


# ---------------------------------------------------------------------------
# Additional Hardening Regression Tests: Macro Pooling, Empty Schema, Mismatches, Timeouts
# ---------------------------------------------------------------------------

def test_macro_average_pooling_updates_all_success_rates():
    """
    Verify that under macro_average pooling, attempt_success_rate, evaluated_success_rate,
    and evaluation_coverage are updated to the unweighted task average alongside verified_success_rate.
    """
    # Task 1: 1 attempt, 1 pass -> attempt_success_rate = 1.0
    slot_t1 = campaign.CampaignSlot(
        slot_id="s_t1", campaign_id="cmp_macro", task_id="BENCH-001",
        task_version="1.0.0", repetition_index=1, arm="baseline", planned_order=1,
        status="completed", verification_status="passed", input_tokens=1000, output_tokens=100, cost_usd=0.01,
    )
    # Task 2: 2 attempts, 0 pass -> attempt_success_rate = 0.0
    slot_t2_a = campaign.CampaignSlot(
        slot_id="s_t2_a", campaign_id="cmp_macro", task_id="BENCH-002",
        task_version="1.0.0", repetition_index=1, arm="baseline", planned_order=2,
        status="completed", verification_status="failed", input_tokens=1000, output_tokens=100, cost_usd=0.01,
    )
    slot_t2_b = campaign.CampaignSlot(
        slot_id="s_t2_b", campaign_id="cmp_macro", task_id="BENCH-002",
        task_version="1.0.0", repetition_index=2, arm="baseline", planned_order=3,
        status="completed", verification_status="failed", input_tokens=1000, output_tokens=100, cost_usd=0.01,
    )

    report = campaign.generate_campaign_report(slots=[slot_t1, slot_t2_a, slot_t2_b], pooling_method="macro_average")
    base_arm = report["pooled_summary"]["arms"]["baseline"]

    # Micro average would be 1/3 = 0.3333...
    # Macro average across the 2 tasks must be (1.0 + 0.0) / 2 = 0.50
    assert base_arm["verified_success_rate"] == 0.5
    assert base_arm["attempt_success_rate"] == 0.5
    assert base_arm["evaluated_success_rate"] == 0.5
    assert base_arm["evaluation_coverage"] == 1.0


def test_empty_campaign_report_schema_consistency():
    """
    Verify that an empty campaign report includes all schema keys:
    is_demo_report, measured_runs_count, measured_totals, and reconciliation_issues.
    """
    report = campaign.generate_campaign_report(slots=[])
    assert report["status"] == "empty"
    assert report["has_measured_data"] is False
    assert report["is_demo_report"] is False
    assert report["measured_runs_count"] == 0
    assert report["measured_totals"] is None
    assert "reconciliation_issues" in report
    assert report["reconciliation_issues"]["has_schedule_violations"] is False


def test_reconciliation_flags_configuration_mismatch_model_and_cache(tmp_path: Path):
    """
    Verify that reconciliation flags configuration mismatch when database runs
    have conflicting model or cache conditions for a scheduled slot.
    """
    manifest = campaign.plan_campaign(
        tasks=["BENCH-001"],
        arms=["baseline"],
        repetitions=1,
        model="gemini-2.5-pro",
        cache_conditions=["cold"],
    )
    target_slot = manifest.slots[0]
    db_file = tmp_path / "recon_mismatch.db"
    conn = ledger.get_connection(db_file)

    run = target_slot.to_ledger_run()
    # Conflict: model differs from scheduled matrix
    run["model"] = "gemini-1.5-flash"
    ledger.record_run(**{k: v for k, v in run.items() if k != "id"}, conn=conn)
    conn.close()

    report = campaign.generate_campaign_report(manifest=manifest, db_path=db_file)
    recon = report["reconciliation_issues"]
    assert recon["has_schedule_violations"] is True
    assert len(recon["mismatched_runs"]) == 1
    assert recon["mismatched_runs"][0]["reason"] == "configuration_mismatch"
    assert recon["mismatched_runs"][0]["slot_id"] == target_slot.slot_id


def test_measured_totals_unavailable_in_demo_reports():
    """
    Verify that measured_totals is None in demo reports and populated only when has_measured_data is True.
    """
    manifest = campaign.plan_campaign(tasks=["BENCH-001"], arms=["baseline"], repetitions=1)
    slot = manifest.slots[0]
    campaign.simulate_slot_execution(slot, outcome="completed", passed=True, cost_usd=0.05)

    # Demo report: measured_totals must be None
    report_demo = campaign.generate_campaign_report(manifest=manifest)
    assert report_demo["has_measured_data"] is False
    assert report_demo["is_demo_report"] is True
    assert report_demo["measured_totals"] is None

    # Live verified report: measured_totals must be populated
    slot.source_kind = "live"
    slot.evidence_status = "verified"
    slot.evidence_ref = str(runner.WORKSPACE_ROOT / "scripts" / "campaign.py")
    slot.evidence_hash = hashlib.sha256(Path(slot.evidence_ref).read_bytes()).hexdigest()

    report_live = campaign.generate_campaign_report(manifest=manifest)
    assert report_live["has_measured_data"] is True
    assert report_live["measured_totals"] is not None
    assert report_live["measured_totals"]["total_cost_usd"] == 0.05
    assert report_live["measured_totals"]["measured_runs_count"] == 1


def test_bench006_mutation_grading_rejects_timeouts(tmp_path: Path):
    """
    Finding 5: BENCH-006 must reject test timeouts as infrastructure errors (mutation_infrastructure_error)
    rather than treating them as detected mutants.
    """
    evaluator_file = WORKSPACE_ROOT / "benchmarks" / "BENCH-006" / "evaluator" / "evaluator.py"
    workspace_dir = WORKSPACE_ROOT / "benchmarks" / "BENCH-006" / "workspace"

    ws = runner.WorkspaceManager.prepare_arm_workspace(
        snapshot_dir=workspace_dir,
        arm="baseline",
        workspace_root=tmp_path / "workspaces",
        run_id="test_b06_timeout",
    )

    try:
        # Create a test that sleeps for 2s while setting BENCH006_MUTANT_TIMEOUT to 0.5s
        timeout_test = ws.path / "tests" / "test_accounting.py"
        timeout_test.write_text(
            "import time\n"
            "from accounting_validator import compute_token_bill\n"
            "def test_delay():\n"
            "    time.sleep(2.0)\n"
            "    rate = {'input_per_million': 1.0, 'output_per_million': 2.0, 'cache_per_million': 0.5}\n"
            "    compute_token_bill(100, 50, 20, rate)\n",
            encoding="utf-8",
        )

        test_env = dict(os.environ)
        test_env["BENCH006_MUTANT_TIMEOUT"] = "0.5"

        res = subprocess.run(
            [sys.executable, str(evaluator_file)],
            cwd=str(ws.path),
            env=test_env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        assert res.returncode != 0
        combined_err = res.stderr + "\n" + res.stdout
        assert "mutation_infrastructure_error" in combined_err
        assert "timeout_expired" in combined_err
    finally:
        ws.cleanup()


