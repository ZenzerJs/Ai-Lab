import copy
import json
from pathlib import Path
import pytest
import sqlite3

import campaign
import ledger


# ---------------------------------------------------------------------------
# REP-01: Generate a 2-task, 2-arm, 2-repeat fixture campaign
# ---------------------------------------------------------------------------

def test_rep_01_matrix_planner_generation():
    """
    REP-01: Generate a 2-task, 2-arm, 2-repeat fixture campaign.
    Expected: Eight unique scheduled attempts; stable manifest; predeclared randomized arm order.
    """
    tasks = ["BENCH-01", "BENCH-02"]
    arms = ["baseline", "icm"]
    repetitions = 2
    seed = 12345

    manifest = campaign.plan_campaign(
        tasks=tasks,
        arms=arms,
        repetitions=repetitions,
        random_seed=seed,
    )

    # 1. Total scheduled attempts: 2 tasks × 2 arms × 2 repetitions = 8 unique attempts
    assert len(manifest.slots) == 8
    slot_ids = [s.slot_id for s in manifest.slots]
    assert len(set(slot_ids)) == 8, "All slot IDs must be unique"

    # 2. Planned order is contiguous 1..8
    planned_orders = [s.planned_order for s in manifest.slots]
    assert planned_orders == list(range(1, 9))

    # 3. Arms distributed equally across scheduled attempts
    baseline_slots = [s for s in manifest.slots if s.arm == "baseline"]
    icm_slots = [s for s in manifest.slots if s.arm == "icm"]
    assert len(baseline_slots) == 4
    assert len(icm_slots) == 4

    # 4. Manifest integrity and deterministic reproducibility
    assert manifest.verify_integrity()
    manifest2 = campaign.plan_campaign(
        tasks=tasks,
        arms=arms,
        repetitions=repetitions,
        random_seed=seed,
    )
    assert manifest.manifest_hash == manifest2.manifest_hash
    assert [s.arm for s in manifest.slots] == [s.arm for s in manifest2.slots]

    # 5. Three-arm support (Arm A: Baseline, Arm B: ICM, Arm C: Delegation)
    manifest_3arms = campaign.plan_campaign(
        tasks=tasks,
        arms=["baseline", "icm", "delegation"],
        repetitions=repetitions,
        random_seed=seed,
    )
    # 2 tasks × 3 arms × 2 repetitions = 12 unique attempts
    assert len(manifest_3arms.slots) == 12
    arm_counts = {a: sum(1 for s in manifest_3arms.slots if s.arm == a) for a in ["baseline", "icm", "delegation"]}
    assert arm_counts == {"baseline": 4, "icm": 4, "delegation": 4}


# ---------------------------------------------------------------------------
# REP-02: Include failed, timed-out, and unexecuted attempts
# ---------------------------------------------------------------------------

def test_rep_02_retain_all_attempt_statuses_and_coverage():
    """
    REP-02: Include failed, timed-out, and unexecuted attempts.
    Expected: Every attempt retained with separate status and execution coverage.
    """
    tasks = ["BENCH-01"]
    arms = ["baseline", "icm"]
    repetitions = 2  # Total 4 slots

    manifest = campaign.plan_campaign(tasks=tasks, arms=arms, repetitions=repetitions, random_seed=42)

    # Simulate mixed outcomes: 2 completed, 1 timed out, 1 unexecuted
    slots = manifest.slots
    campaign.simulate_slot_execution(slots[0], outcome="completed", passed=True, cost_usd=0.05)
    campaign.simulate_slot_execution(slots[1], outcome="completed", passed=False, cost_usd=0.04)
    campaign.simulate_slot_execution(slots[2], outcome="timed_out", passed=False, cost_usd=0.01)
    campaign.simulate_slot_execution(slots[3], outcome="unexecuted")

    report = campaign.generate_campaign_report(manifest=manifest)

    # 1. Total scheduled retained
    assert report["total_scheduled"] == 4
    # 2. Total executed: completed (2) + timed_out (1) = 3
    assert report["total_executed"] == 3
    # 3. Execution coverage: 3 / 4 = 75.0%
    assert report["execution_coverage_pct"] == 75.0

    # 4. Status counts separate and preserved
    status_counts = report["status_counts"]
    assert status_counts["completed"] == 2
    assert status_counts["timed_out"] == 1
    assert status_counts["unexecuted"] == 1
    assert status_counts["failed"] == 0

    # 5. All attempts retained in report
    assert len(report["all_attempts"]) == 4


# ---------------------------------------------------------------------------
# REP-03: Supply uneven sample counts
# ---------------------------------------------------------------------------

def test_rep_03_uneven_sample_counts_not_masquerading_as_balanced():
    """
    REP-03: Supply uneven sample counts.
    Expected: Per-arm counts visible; no appearance of a balanced experiment.
    """
    # 5 baseline runs, 2 icm runs
    slots = []
    for i in range(1, 6):
        s = campaign.CampaignSlot(
            slot_id=f"slot_b_{i}", campaign_id="cmp_uneven", task_id="BENCH-01",
            task_version="1.0.0", repetition_index=i, arm="baseline", planned_order=i,
            status="completed", verification_status="passed", input_tokens=1000, output_tokens=100, cost_usd=0.01
        )
        slots.append(s)

    for i in range(1, 3):
        s = campaign.CampaignSlot(
            slot_id=f"slot_i_{i}", campaign_id="cmp_uneven", task_id="BENCH-01",
            task_version="1.0.0", repetition_index=i, arm="icm", planned_order=5 + i,
            status="completed", verification_status="passed", input_tokens=800, output_tokens=80, cost_usd=0.008
        )
        slots.append(s)

    report = campaign.generate_campaign_report(slots=slots)

    # 1. Exact per-arm counts visible
    sample_counts = report["sample_counts"]
    assert sample_counts["baseline"] == 5
    assert sample_counts["icm"] == 2

    # 2. Honest imbalance flag
    assert report["is_balanced"] is False
    assert report["balance_status"] == "uneven"


# ---------------------------------------------------------------------------
# REP-04: No eligible measured runs exist
# ---------------------------------------------------------------------------

def test_rep_04_honest_empty_state_no_synthetic_substitute():
    """
    REP-04: No eligible measured runs exist.
    Expected: Honest empty state; no synthetic substitute.
    """
    # Case A: Totally empty manifest/slots
    report_empty = campaign.generate_campaign_report(slots=[])
    assert report_empty["status"] == "empty"
    assert report_empty["has_measured_data"] is False
    assert report_empty["total_scheduled"] == 0
    assert report_empty["savings"] is None
    assert report_empty["arms"] == {}

    # Case B: Scheduled slots exist, but all are unexecuted
    manifest = campaign.plan_campaign(tasks=["BENCH-01"], arms=["baseline", "icm"], repetitions=1)
    for s in manifest.slots:
        campaign.simulate_slot_execution(s, outcome="unexecuted")

    report_unexecuted = campaign.generate_campaign_report(manifest=manifest)
    assert report_unexecuted["status"] == "no_eligible_measured_runs"
    assert report_unexecuted["has_measured_data"] is False
    assert report_unexecuted["pooled_summary"]["savings"] is None
    assert report_unexecuted["pooled_summary"]["arms"]["baseline"]["mean_cost_usd"] is None
    assert report_unexecuted["pooled_summary"]["arms"]["icm"]["mean_cost_usd"] is None


# ---------------------------------------------------------------------------
# REP-05: Baseline estimated cost is zero
# ---------------------------------------------------------------------------

def test_rep_05_baseline_cost_zero_savings_percentage_undefined():
    """
    REP-05: Baseline estimated cost is zero.
    Expected: Savings percentage undefined (None); absolute values still reported.
    """
    slots = [
        campaign.CampaignSlot(
            slot_id="s1", campaign_id="cmp_zero_base", task_id="BENCH-01",
            task_version="1.0.0", repetition_index=1, arm="baseline", planned_order=1,
            status="completed", verification_status="passed", input_tokens=0, output_tokens=0,
            cost_usd=0.0, cost_status="usage_estimate"
        ),
        campaign.CampaignSlot(
            slot_id="s2", campaign_id="cmp_zero_base", task_id="BENCH-01",
            task_version="1.0.0", repetition_index=1, arm="icm", planned_order=2,
            status="completed", verification_status="passed", input_tokens=1000, output_tokens=100,
            cost_usd=0.02, cost_status="usage_estimate"
        ),
    ]

    report = campaign.generate_campaign_report(slots=slots)
    savings = report["pooled_summary"]["savings"]
    assert savings is not None

    # Absolute cost difference is reported: 0.0 - 0.02 = -0.02
    assert savings["absolute_savings_usd"] == pytest.approx(-0.02)
    # Savings percentage is undefined (None) due to zero division
    assert savings["savings_percentage"] is None
    assert savings["savings_percentage_reason"] == "zero_baseline_cost"


# ---------------------------------------------------------------------------
# REP-06: All verified outcomes fail
# ---------------------------------------------------------------------------

def test_rep_06_all_verified_outcomes_fail_cost_per_success_undefined():
    """
    REP-06: All verified outcomes fail.
    Expected: Cost per success undefined (None), not zero.
    """
    slots = [
        campaign.CampaignSlot(
            slot_id="s1", campaign_id="cmp_fail", task_id="BENCH-01",
            task_version="1.0.0", repetition_index=1, arm="baseline", planned_order=1,
            status="completed", verification_status="failed", input_tokens=10000, output_tokens=500,
            cost_usd=0.10, cost_status="usage_estimate"
        ),
        campaign.CampaignSlot(
            slot_id="s2", campaign_id="cmp_fail", task_id="BENCH-01",
            task_version="1.0.0", repetition_index=1, arm="icm", planned_order=2,
            status="completed", verification_status="failed", input_tokens=6000, output_tokens=300,
            cost_usd=0.05, cost_status="usage_estimate"
        ),
    ]

    report = campaign.generate_campaign_report(slots=slots)
    arms = report["pooled_summary"]["arms"]

    # Both arms failed all attempts
    assert arms["baseline"]["passed_count"] == 0
    assert arms["baseline"]["verified_success_rate"] == 0.0
    assert arms["baseline"]["cost_per_success"] is None
    assert arms["baseline"]["cost_per_success_reason"] == "no_successful_runs"

    assert arms["icm"]["passed_count"] == 0
    assert arms["icm"]["verified_success_rate"] == 0.0
    assert arms["icm"]["cost_per_success"] is None
    assert arms["icm"]["cost_per_success_reason"] == "no_successful_runs"


# ---------------------------------------------------------------------------
# REP-07: A correct run lacks token telemetry
# ---------------------------------------------------------------------------

def test_rep_07_decoupled_correctness_and_telemetry():
    """
    REP-07: A correct run lacks token telemetry.
    Expected: Included in correctness count; excluded from cost sample with reason.
    """
    # Arm with 2 runs:
    # Run 1 passed and has complete token telemetry ($0.05)
    # Run 2 passed but has missing token telemetry (cost_status="unavailable", tokens=None)
    slots = [
        campaign.CampaignSlot(
            slot_id="s1", campaign_id="cmp_rep07", task_id="BENCH-01",
            task_version="1.0.0", repetition_index=1, arm="baseline", planned_order=1,
            status="completed", verification_status="passed", input_tokens=5000, output_tokens=500,
            cost_usd=0.05, cost_status="usage_estimate"
        ),
        campaign.CampaignSlot(
            slot_id="s2", campaign_id="cmp_rep07", task_id="BENCH-01",
            task_version="1.0.0", repetition_index=2, arm="baseline", planned_order=2,
            status="completed", verification_status="passed", input_tokens=None, output_tokens=None,
            cost_usd=None, cost_status="unavailable", exclusion_reasons=["missing_usage_telemetry"]
        ),
    ]

    report = campaign.generate_campaign_report(slots=slots)
    arm_b = report["pooled_summary"]["arms"]["baseline"]

    # 1. Correctness: both runs evaluated and passed (100% verified success rate)
    assert arm_b["sample_count"] == 2
    assert arm_b["passed_count"] == 2
    assert arm_b["verified_success_rate"] == 1.0

    # 2. Cost: only 1 run is cost-eligible; 1 run is excluded
    assert arm_b["cost_eligible_sample_count"] == 1
    assert arm_b["cost_excluded_sample_count"] == 1
    assert "missing_usage_telemetry" in arm_b["cost_exclusion_reasons"]
    assert arm_b["mean_cost_usd"] == 0.05


# ---------------------------------------------------------------------------
# REP-08: One member of a pair lacks complete cost
# ---------------------------------------------------------------------------

def test_rep_08_paired_cost_difference_excludes_incomplete_pairs():
    """
    REP-08: One member of a pair lacks complete cost.
    Expected: Pair excluded from paired cost difference; missing-pair count reported.
    """
    # Pair 1 (rep 1): both baseline and icm have complete cost
    # Pair 2 (rep 2): baseline has complete cost, but icm has unavailable cost
    slots = [
        # Pair 1
        campaign.CampaignSlot(
            slot_id="s1_b", campaign_id="cmp_rep08", task_id="BENCH-01",
            task_version="1.0.0", repetition_index=1, arm="baseline", planned_order=1,
            status="completed", verification_status="passed", input_tokens=10000, output_tokens=500,
            cost_usd=0.10, cost_status="usage_estimate"
        ),
        campaign.CampaignSlot(
            slot_id="s1_i", campaign_id="cmp_rep08", task_id="BENCH-01",
            task_version="1.0.0", repetition_index=1, arm="icm", planned_order=2,
            status="completed", verification_status="passed", input_tokens=5000, output_tokens=300,
            cost_usd=0.04, cost_status="usage_estimate"
        ),
        # Pair 2
        campaign.CampaignSlot(
            slot_id="s2_b", campaign_id="cmp_rep08", task_id="BENCH-01",
            task_version="1.0.0", repetition_index=2, arm="baseline", planned_order=3,
            status="completed", verification_status="passed", input_tokens=10000, output_tokens=500,
            cost_usd=0.10, cost_status="usage_estimate"
        ),
        campaign.CampaignSlot(
            slot_id="s2_i", campaign_id="cmp_rep08", task_id="BENCH-01",
            task_version="1.0.0", repetition_index=2, arm="icm", planned_order=4,
            status="completed", verification_status="passed", input_tokens=None, output_tokens=None,
            cost_usd=None, cost_status="unavailable"
        ),
    ]

    report = campaign.generate_campaign_report(slots=slots)
    paired = report["pooled_summary"]["paired_differences"]

    assert paired["total_planned_pairs"] == 2
    assert paired["complete_pairs_count"] == 1
    assert paired["missing_or_incomplete_pairs_count"] == 1

    # Only pair 1 is in paired differences: 0.10 - 0.04 = 0.06
    assert len(paired["paired_cost_differences"]) == 1
    assert paired["paired_cost_differences"][0]["cost_difference_usd"] == pytest.approx(0.06)
    assert paired["mean_paired_cost_difference_usd"] == pytest.approx(0.06)


# ---------------------------------------------------------------------------
# REP-09: Cold and warm cache conditions coexist
# ---------------------------------------------------------------------------

def test_rep_09_cold_and_warm_cache_stratified_separately():
    """
    REP-09: Cold and warm cache conditions coexist.
    Expected: Separate strata; no silent combined headline.
    """
    slots = [
        # Cold stratum: 0 cache read tokens, higher cost
        campaign.CampaignSlot(
            slot_id="c_b", campaign_id="cmp_rep09", task_id="BENCH-01",
            task_version="1.0.0", repetition_index=1, arm="baseline", planned_order=1,
            cache_condition="cold", status="completed", verification_status="passed",
            input_tokens=20000, output_tokens=500, cache_read_tokens=0,
            cost_usd=0.10, cost_status="usage_estimate"
        ),
        campaign.CampaignSlot(
            slot_id="c_i", campaign_id="cmp_rep09", task_id="BENCH-01",
            task_version="1.0.0", repetition_index=1, arm="icm", planned_order=2,
            cache_condition="cold", status="completed", verification_status="passed",
            input_tokens=10000, output_tokens=300, cache_read_tokens=0,
            cost_usd=0.05, cost_status="usage_estimate"
        ),
        # Warm stratum: high cache read tokens, lower cost
        campaign.CampaignSlot(
            slot_id="w_b", campaign_id="cmp_rep09", task_id="BENCH-01",
            task_version="1.0.0", repetition_index=2, arm="baseline", planned_order=3,
            cache_condition="warm", status="completed", verification_status="passed",
            input_tokens=20000, output_tokens=500, cache_read_tokens=18000,
            cost_usd=0.03, cost_status="usage_estimate"
        ),
        campaign.CampaignSlot(
            slot_id="w_i", campaign_id="cmp_rep09", task_id="BENCH-01",
            task_version="1.0.0", repetition_index=2, arm="icm", planned_order=4,
            cache_condition="warm", status="completed", verification_status="passed",
            input_tokens=10000, output_tokens=300, cache_read_tokens=9000,
            cost_usd=0.015, cost_status="usage_estimate"
        ),
    ]

    report = campaign.generate_campaign_report(slots=slots)

    # 1. Flag multi-strata existence and disclose warning
    assert report["has_multiple_strata"] is True
    assert set(report["cache_conditions_present"]) == {"cold", "warm"}
    assert report["stratification_warning"] is not None

    # 2. Both strata separately accessible with distinct costs
    assert "cold" in report["strata"]
    assert "warm" in report["strata"]

    cold_arms = report["strata"]["cold"]["arms"]
    warm_arms = report["strata"]["warm"]["arms"]

    assert cold_arms["baseline"]["mean_cost_usd"] == 0.10
    assert cold_arms["icm"]["mean_cost_usd"] == 0.05
    assert warm_arms["baseline"]["mean_cost_usd"] == 0.03
    assert warm_arms["icm"]["mean_cost_usd"] == 0.015


# ---------------------------------------------------------------------------
# REP-10: Large and small tasks coexist
# ---------------------------------------------------------------------------

def test_rep_10_large_and_small_tasks_retained_with_explicit_pooling():
    """
    REP-10: Large and small tasks coexist.
    Expected: Task-level results retained; pooling method explicit.
    """
    # Task 1: Large task (100k tokens, $1.00 base, $0.50 icm -> 50% savings)
    # Task 2: Small task (1k tokens, $0.02 base, $0.01 icm -> 50% savings)
    slots = [
        # Large task
        campaign.CampaignSlot(
            slot_id="l_b", campaign_id="cmp_rep10", task_id="TASK-LARGE",
            task_version="1.0.0", repetition_index=1, arm="baseline", planned_order=1,
            status="completed", verification_status="passed",
            input_tokens=90000, output_tokens=10000, total_tokens=100000,
            cost_usd=1.00, cost_status="usage_estimate"
        ),
        campaign.CampaignSlot(
            slot_id="l_i", campaign_id="cmp_rep10", task_id="TASK-LARGE",
            task_version="1.0.0", repetition_index=1, arm="icm", planned_order=2,
            status="completed", verification_status="passed",
            input_tokens=45000, output_tokens=5000, total_tokens=50000,
            cost_usd=0.50, cost_status="usage_estimate"
        ),
        # Small task
        campaign.CampaignSlot(
            slot_id="s_b", campaign_id="cmp_rep10", task_id="TASK-SMALL",
            task_version="1.0.0", repetition_index=1, arm="baseline", planned_order=3,
            status="completed", verification_status="passed",
            input_tokens=900, output_tokens=100, total_tokens=1000,
            cost_usd=0.02, cost_status="usage_estimate"
        ),
        campaign.CampaignSlot(
            slot_id="s_i", campaign_id="cmp_rep10", task_id="TASK-SMALL",
            task_version="1.0.0", repetition_index=1, arm="icm", planned_order=4,
            status="completed", verification_status="passed",
            input_tokens=450, output_tokens=50, total_tokens=500,
            cost_usd=0.01, cost_status="usage_estimate"
        ),
    ]

    report = campaign.generate_campaign_report(slots=slots, pooling_method="macro_average")

    # 1. Task-level results retained side-by-side
    assert "by_task" in report
    assert "TASK-LARGE" in report["by_task"]
    assert "TASK-SMALL" in report["by_task"]

    large_arms = report["by_task"]["TASK-LARGE"]["arms"]
    small_arms = report["by_task"]["TASK-SMALL"]["arms"]

    assert large_arms["baseline"]["mean_cost_usd"] == 1.00
    assert small_arms["baseline"]["mean_cost_usd"] == 0.02

    # 2. Pooling method is explicit and documented
    assert report["pooling_method"] == "macro_average"
    assert "Macro-average" in report["pooling_method_description"]

    # Under macro-average: mean cost is (1.00 + 0.02) / 2 = 0.51
    pooled_b = report["pooled_summary"]["arms"]["baseline"]
    assert pooled_b["mean_cost_usd"] == pytest.approx(0.51)


# ---------------------------------------------------------------------------
# Integration: Manifest Save/Load & Tamper Detection
# ---------------------------------------------------------------------------

def test_manifest_serialization_and_tamper_detection(tmp_path: Path):
    """Verify manifest file persistence and cryptographic tamper detection."""
    manifest_file = tmp_path / "test_campaign.json"

    manifest = campaign.plan_campaign(
        tasks=["BENCH-01", "BENCH-02"],
        arms=["baseline", "icm"],
        repetitions=2,
        random_seed=42,
    )
    manifest.save(manifest_file)

    loaded = campaign.CampaignManifest.load(manifest_file)
    assert loaded.verify_integrity()
    assert loaded.manifest_hash == manifest.manifest_hash
    assert len(loaded.slots) == 8

    # Tamper with a slot
    loaded.slots[0].model = "unauthorized-tampered-model"
    assert not loaded.verify_integrity()

    # Tamper with arm_configs
    loaded2 = campaign.CampaignManifest.load(manifest_file)
    assert loaded2.verify_integrity()
    loaded2.arm_configs["icm"]["model"] = "unauthorized-governance-model"
    assert not loaded2.verify_integrity(), "Tampering with arm_configs must invalidate manifest hash"


# ---------------------------------------------------------------------------
# Integration: End-to-End Mock Campaign Execution & Ledger Storage
# ---------------------------------------------------------------------------

def test_end_to_end_mock_campaign_with_ledger(tmp_path: Path):
    """Execute a simulated campaign and verify report matches ledger records."""
    db_file = tmp_path / "campaign_test.db"
    conn = ledger.get_connection(db_file)

    manifest = campaign.plan_campaign(
        tasks=["BENCH-01", "BENCH-02"],
        arms=["baseline", "icm"],
        repetitions=1,
        random_seed=999,
    )

    executed_manifest = campaign.execute_campaign_mock(manifest, conn=conn)

    report = campaign.generate_campaign_report(manifest=executed_manifest, conn=conn)

    assert report["total_scheduled"] == 4
    assert report["total_executed"] == 4
    assert report["execution_coverage_pct"] == 100.0
    assert report["has_measured_data"] is False
    assert report["is_demo_report"] is True
    assert "baseline" in report["pooled_summary"]["arms"]
    assert "icm" in report["pooled_summary"]["arms"]

    # Verify rows in ledger
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM runs WHERE manifest_id = ?", (manifest.campaign_id,))
    assert cursor.fetchone()[0] == 4

    conn.close()


def test_manifest_db_reconciliation_fresh_manifest(tmp_path: Path):
    """Verify that loading a fresh pre-execution manifest from disk reconciles executed runs from DB."""
    db_file = tmp_path / "recon_test.db"
    conn = ledger.get_connection(db_file)

    manifest = campaign.plan_campaign(
        tasks=["BENCH-01"],
        arms=["baseline", "icm"],
        repetitions=1,
        random_seed=42,
    )
    manifest_path = tmp_path / "fresh_manifest.json"
    manifest.save(manifest_path)

    # Execute into database
    campaign.execute_campaign_mock(manifest, conn=conn)
    conn.close()

    # Load fresh manifest (its slots are still 'scheduled')
    disk_manifest = campaign.CampaignManifest.load(manifest_path)
    assert disk_manifest.slots[0].status == "scheduled"

    # Report generated with fresh manifest + db must reconcile executed runs
    report = campaign.generate_campaign_report(manifest=disk_manifest, db_path=db_file)
    assert report["total_scheduled"] == 2
    assert report["total_executed"] == 2
    assert report["execution_coverage_pct"] == 100.0
    assert report["has_measured_data"] is False
    assert report["is_demo_report"] is True
    assert report["pooled_summary"]["arms"]["baseline"]["cost_eligible_sample_count"] == 1
    assert report["pooled_summary"]["arms"]["icm"]["cost_eligible_sample_count"] == 1


def test_three_arm_campaign_savings_and_paired_differences():
    """Verify 3-arm campaign (Baseline, ICM, Delegation) generates comparisons for both non-baseline arms."""
    manifest = campaign.plan_campaign(
        tasks=["BENCH-01"],
        arms=["baseline", "icm", "delegation"],
        repetitions=2,
        random_seed=100,
    )
    executed = campaign.execute_campaign_mock(manifest)
    report = campaign.generate_campaign_report(manifest=executed)

    assert len(report["pooled_summary"]["arms"]) == 3
    assert set(report["pooled_summary"]["arms"].keys()) == {"baseline", "icm", "delegation"}

    # Both non-baseline arms must have computed savings and paired differences
    savings = report["pooled_summary"]["savings"]
    assert savings is not None
    assert "by_arm" in savings
    assert "icm" in savings["by_arm"]
    assert "delegation" in savings["by_arm"]

    paired = report["pooled_summary"]["paired_differences"]
    assert paired is not None
    assert "by_arm" in paired
    assert "icm" in paired["by_arm"]
    assert "delegation" in paired["by_arm"]
    assert paired["by_arm"]["icm"]["complete_pairs_count"] == 2
    assert paired["by_arm"]["delegation"]["complete_pairs_count"] == 2


def test_db_runs_preserve_exclusion_reasons_and_eligibility(tmp_path: Path):
    """Verify runs loaded from DB preserve exclusion reasons and are excluded from cost measurement."""
    db_file = tmp_path / "exclusion_test.db"
    conn = ledger.get_connection(db_file)

    ledger.record_run(
        task_id="BENCH-01",
        arm="baseline",
        model="gemini-2.5-pro",
        run_index=1,
        timestamp="2026-10-02T12:00:00Z",
        input_tokens=1000,
        output_tokens=100,
        cost_usd=0.02,
        cost_status="incomplete",
        exclusion_reasons=["partial_telemetry"],
        manifest_id="cmp_exc",
        conn=conn,
    )
    conn.close()

    report = campaign.generate_campaign_report(db_path=db_file, campaign_id="cmp_exc")
    arm_b = report["pooled_summary"]["arms"]["baseline"]

    assert arm_b["sample_count"] == 1
    assert arm_b["cost_eligible_sample_count"] == 0
    assert arm_b["cost_excluded_sample_count"] == 1
    assert "partial_telemetry" in arm_b["cost_exclusion_reasons"]
    assert report["all_attempts"][0]["exclusion_reasons"] == ["partial_telemetry"]


def test_cost_per_success_not_deflated_by_missing_telemetry():
    """Verify cost per success evaluates strictly on cost-eligible successes (no free $0.00 treatment)."""
    slots = [
        campaign.CampaignSlot(
            slot_id="s1", campaign_id="c", task_id="T1", task_version="1.0", repetition_index=1,
            arm="baseline", planned_order=1, status="completed", verification_status="passed",
            input_tokens=1000, output_tokens=100, cost_usd=0.20, cost_status="usage_estimate"
        ),
        campaign.CampaignSlot(
            slot_id="s2", campaign_id="c", task_id="T1", task_version="1.0", repetition_index=2,
            arm="baseline", planned_order=2, status="completed", verification_status="passed",
            input_tokens=None, output_tokens=None, cost_usd=None, cost_status="unavailable",
            exclusion_reasons=["missing_usage_telemetry"]
        )
    ]
    report = campaign.generate_campaign_report(slots=slots)
    arm_b = report["pooled_summary"]["arms"]["baseline"]

    assert arm_b["passed_count"] == 2
    assert arm_b["cost_eligible_sample_count"] == 1
    # Cost per success must be $0.20 / 1 cost-eligible success = $0.20 (NOT $0.10)
    assert arm_b["cost_per_success"] == pytest.approx(0.20)


def test_macro_average_paired_differences():
    """Verify macro-average pooling averages per-task paired differences."""
    slots = [
        # Task 1: large diff ($1.00 - $0.50 = $0.50)
        campaign.CampaignSlot(
            slot_id="t1_b", campaign_id="c", task_id="T1", task_version="1.0", repetition_index=1,
            arm="baseline", planned_order=1, status="completed", verification_status="passed",
            input_tokens=1000, output_tokens=100, cost_usd=1.00
        ),
        campaign.CampaignSlot(
            slot_id="t1_i", campaign_id="c", task_id="T1", task_version="1.0", repetition_index=1,
            arm="icm", planned_order=2, status="completed", verification_status="passed",
            input_tokens=500, output_tokens=50, cost_usd=0.50
        ),
        # Task 2: small diff ($0.10 - $0.08 = $0.02)
        campaign.CampaignSlot(
            slot_id="t2_b", campaign_id="c", task_id="T2", task_version="1.0", repetition_index=1,
            arm="baseline", planned_order=3, status="completed", verification_status="passed",
            input_tokens=100, output_tokens=10, cost_usd=0.10
        ),
        campaign.CampaignSlot(
            slot_id="t2_i", campaign_id="c", task_id="T2", task_version="1.0", repetition_index=1,
            arm="icm", planned_order=4, status="completed", verification_status="passed",
            input_tokens=80, output_tokens=8, cost_usd=0.08
        ),
    ]

    report = campaign.generate_campaign_report(slots=slots, pooling_method="macro_average")
    paired = report["pooled_summary"]["paired_differences"]
    # Macro-average of ($0.50 + $0.02) / 2 = $0.26
    assert paired["mean_paired_cost_difference_usd"] == pytest.approx(0.26)
    assert paired["pooling_method"] == "macro_average"

