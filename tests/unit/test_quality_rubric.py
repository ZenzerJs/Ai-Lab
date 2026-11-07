"""
Unit tests for multi-dimensional benchmark scoring rubric (TSK-025).

Tests:
- Deterministic 0-5 rubric dimension scores (correctness, engineering, maintainability, process, design).
- Backend (0-20, max_possible=20) vs UI (0-25, max_possible=25) scoring.
- Maintainability tiers via AST (<=50 LOC -> 5, <=100 -> 3, >100 -> 1, syntax error -> 0).
- Process discipline tracking of out-of-scope touches.
- Serialization into CampaignSlot and runs.notes JSON payload.
"""

import json
from pathlib import Path
import tempfile
import pytest

from campaign import CampaignSlot, compute_quality_ci, prepare_blind_ab_packet, score_workspace
from scaffold_outlines import scaffold_task_outline


def test_score_workspace_backend_exemplary():
    """Backend task with zero defects: scores 20/20 (100.0%)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        code_file = tmp_path / "service.py"
        code_file.write_text(
            "def small_handler(x: int) -> int:\n"
            "    # Clean, concise handler\n"
            "    return x * 2\n",
            encoding="utf-8",
        )

        scores = score_workspace(
            workspace_path=tmp_path,
            target_files=["service.py"],
            test_passed=True,
            lint_errors=0,
            a11y_violations=None,
            modified_files=["service.py"],
        )

        assert scores["correctness"] == 5
        assert scores["engineering"] == 5
        assert scores["maintainability"] == 5
        assert scores["process"] == 5
        assert scores["design"] is None
        assert scores["total"] == 20
        assert scores["max_possible"] == 20
        assert scores["normalized_pct"] == 100.0


def test_score_workspace_ui_exemplary():
    """UI task with zero a11y violations: scores 25/25 (100.0%)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        code_file = tmp_path / "component.py"
        code_file.write_text(
            "def render_button():\n"
            "    return '<button aria-label=\"Submit\">OK</button>'\n",
            encoding="utf-8",
        )

        scores = score_workspace(
            workspace_path=tmp_path,
            target_files=["component.py"],
            test_passed=True,
            lint_errors=0,
            a11y_violations=0,
            modified_files=["component.py"],
        )

        assert scores["correctness"] == 5
        assert scores["engineering"] == 5
        assert scores["maintainability"] == 5
        assert scores["process"] == 5
        assert scores["design"] == 5
        assert scores["total"] == 25
        assert scores["max_possible"] == 25
        assert scores["normalized_pct"] == 100.0


def test_score_workspace_correctness_failure():
    """Failing test asserts correctness=0."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        scores = score_workspace(
            workspace_path=tmp_path,
            target_files=None,
            test_passed=False,
            lint_errors=0,
            a11y_violations=None,
        )
        assert scores["correctness"] == 0
        assert scores["total"] == 15
        assert scores["normalized_pct"] == 75.0


def test_score_workspace_engineering_penalties():
    """Engineering score starts at 5 and deducts 1 per lint error down to 0."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        scores_3 = score_workspace(
            workspace_path=tmp_path,
            test_passed=True,
            lint_errors=2,
            a11y_violations=None,
        )
        assert scores_3["engineering"] == 3

        scores_0 = score_workspace(
            workspace_path=tmp_path,
            test_passed=True,
            lint_errors=10,
            a11y_violations=None,
        )
        assert scores_0["engineering"] == 0


def test_score_workspace_maintainability_tiers():
    """Maintainability tiers: <=50 -> 5, <=100 -> 3, >100 -> 1, syntax error -> 0."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # 1. Modular function (<=50 LOC) -> 5
        f5 = tmp_path / "mod5.py"
        f5.write_text("def f():\n" + "    pass\n" * 20, encoding="utf-8")
        s5 = score_workspace(workspace_path=tmp_path, target_files=["mod5.py"], test_passed=True)
        assert s5["maintainability"] == 5

        # 2. Medium function (51-100 LOC) -> 3
        f3 = tmp_path / "mod3.py"
        f3.write_text("def f():\n" + "    x = 1\n" * 65, encoding="utf-8")
        s3 = score_workspace(workspace_path=tmp_path, target_files=["mod3.py"], test_passed=True)
        assert s3["maintainability"] == 3

        # 3. Large function (>100 LOC) -> 1
        f1 = tmp_path / "mod1.py"
        f1.write_text("def f():\n" + "    y = 2\n" * 120, encoding="utf-8")
        s1 = score_workspace(workspace_path=tmp_path, target_files=["mod1.py"], test_passed=True)
        assert s1["maintainability"] == 1

        # 4. Syntax Error -> 0
        f0 = tmp_path / "mod0.py"
        f0.write_text("def syntax_error(:\n    pass", encoding="utf-8")
        s0 = score_workspace(workspace_path=tmp_path, target_files=["mod0.py"], test_passed=True)
        assert s0["maintainability"] == 0


def test_score_workspace_process_discipline():
    """Process discipline: 5 if strictly in-scope, minus 1 per out-of-scope touch."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # In-scope only
        s_clean = score_workspace(
            workspace_path=tmp_path,
            target_files=["src/app.py"],
            modified_files=["src/app.py"],
            test_passed=True,
        )
        assert s_clean["process"] == 5

        # 1 out-of-scope file
        s_warn = score_workspace(
            workspace_path=tmp_path,
            target_files=["src/app.py"],
            modified_files=["src/app.py", "config/secret.json"],
            test_passed=True,
        )
        assert s_warn["process"] == 4

        # 6 out-of-scope files
        s_fail = score_workspace(
            workspace_path=tmp_path,
            target_files=["src/app.py"],
            modified_files=["src/app.py"] + [f"extra_{i}.py" for i in range(6)],
            test_passed=True,
        )
        assert s_fail["process"] == 0

        # Unconstrained target_files (None) -> 5
        s_unconstrained = score_workspace(
            workspace_path=tmp_path,
            target_files=None,
            modified_files=["anything.py"],
            test_passed=True,
        )
        assert s_unconstrained["process"] == 5


def test_score_workspace_design_penalties():
    """Design score: None when a11y_violations is None; max(0, 5 - a11y_violations) when active."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # Backend: None
        s_backend = score_workspace(workspace_path=tmp_path, test_passed=True, a11y_violations=None)
        assert s_backend["design"] is None
        assert s_backend["max_possible"] == 20

        # UI: 2 violations -> 3
        s_ui_2 = score_workspace(workspace_path=tmp_path, test_passed=True, a11y_violations=2)
        assert s_ui_2["design"] == 3
        assert s_ui_2["max_possible"] == 25

        # UI: 7 violations -> 0
        s_ui_7 = score_workspace(workspace_path=tmp_path, test_passed=True, a11y_violations=7)
        assert s_ui_7["design"] == 0
        assert s_ui_7["max_possible"] == 25


def test_campaign_slot_quality_scores_serialization():
    """CampaignSlot serialization preserves quality_scores in notes JSON column without schema migration."""
    quality_payload = {
        "correctness": 5,
        "engineering": 5,
        "maintainability": 5,
        "process": 5,
        "design": 5,
        "total": 25,
        "max_possible": 25,
        "normalized_pct": 100.0,
    }

    slot = CampaignSlot(
        slot_id="slot_test_001",
        campaign_id="camp_test",
        task_id="TSK-025",
        task_version="1.0.0",
        repetition_index=1,
        arm="governed",
        planned_order=1,
        quality_scores=quality_payload,
    )

    ledger_run = slot.to_ledger_run()
    assert "notes" in ledger_run
    parsed_notes = json.loads(ledger_run["notes"])
    assert parsed_notes["quality_scores"] == quality_payload
    assert parsed_notes["slot_id"] == "slot_test_001"

    # Verify CampaignSlot.from_dict preserves quality_scores
    slot_dict = slot.to_dict()
    assert slot_dict["quality_scores"] == quality_payload
    restored_slot = CampaignSlot.from_dict(slot_dict)
    assert restored_slot.quality_scores == quality_payload

    # Verify slot without quality_scores omits key in notes
    empty_slot = CampaignSlot(
        slot_id="slot_test_002",
        campaign_id="camp_test",
        task_id="TSK-025",
        task_version="1.0.0",
        repetition_index=1,
        arm="baseline",
        planned_order=2,
    )
    empty_run = empty_slot.to_ledger_run()
    empty_notes = json.loads(empty_run["notes"])
    assert "quality_scores" not in empty_notes


def test_scaffold_outlines():
    """Verify scaffold_task_outline materializes correct file counts and structures."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # EXP-009: 7 files
        dir_009 = tmp_path / "exp009"
        files_009 = scaffold_task_outline("EXP-009", dir_009)
        assert len(files_009) == 7
        assert (dir_009 / "queue_engine/schema.py").is_file()
        assert (dir_009 / "queue_engine/storage.py").is_file()
        assert (dir_009 / "queue_engine/dag.py").is_file()
        assert (dir_009 / "queue_engine/worker.py").is_file()
        assert (dir_009 / "queue_engine/retry.py").is_file()
        assert (dir_009 / "queue_engine/ui.html").is_file()
        assert (dir_009 / "tests/test_exp009.py").is_file()

        # EXP-010: 8 files
        dir_010 = tmp_path / "exp010"
        files_010 = scaffold_task_outline("EXP-010", dir_010)
        assert len(files_010) == 8
        assert (dir_010 / "kg_engine/parser.py").is_file()
        assert (dir_010 / "kg_engine/graph.py").is_file()
        assert (dir_010 / "kg_engine/bm25.py").is_file()
        assert (dir_010 / "kg_engine/indexer.py").is_file()
        assert (dir_010 / "kg_engine/cli.py").is_file()
        assert (dir_010 / "kg_engine/exporter.py").is_file()
        assert (dir_010 / "kg_engine/viewer.html").is_file()
        assert (dir_010 / "tests/test_exp010.py").is_file()

        # EXP-011: 6 files
        dir_011 = tmp_path / "exp011"
        files_011 = scaffold_task_outline("EXP-011", dir_011)
        assert len(files_011) == 6
        assert (dir_011 / "gateway/limiter.py").is_file()
        assert (dir_011 / "gateway/webhook.py").is_file()
        assert (dir_011 / "gateway/billing.py").is_file()
        assert (dir_011 / "gateway/router.py").is_file()
        assert (dir_011 / "gateway/console.html").is_file()
        assert (dir_011 / "tests/test_exp011.py").is_file()

        # Unknown task_id raises ValueError
        with pytest.raises(ValueError, match="Unknown task_id"):
            scaffold_task_outline("EXP-999", tmp_path / "unknown")


def test_prepare_blind_ab_packet():
    """Verify prepare_blind_ab_packet strips stage contracts, redacts identifiers, and blinds arms."""
    diff_baseline = (
        "diff --git a/tasks/TSK-026/02_plan.md b/tasks/TSK-026/02_plan.md\n"
        "--- a/tasks/TSK-026/02_plan.md\n"
        "+++ b/tasks/TSK-026/02_plan.md\n"
        "@@ -1,3 +1,3 @@\n"
        "-# Baseline plan\n"
        "+# Updated baseline plan\n"
        "diff --git a/queue_engine/worker.py b/queue_engine/worker.py\n"
        "--- a/queue_engine/worker.py\n"
        "+++ b/queue_engine/worker.py\n"
        "@@ -10,3 +10,3 @@\n"
        "-# baseline implementation\n"
        "+# fixed baseline worker implementation\n"
    )

    diff_governed = (
        "diff --git a/.agents/rules/okr-gate.md b/.agents/rules/okr-gate.md\n"
        "--- a/.agents/rules/okr-gate.md\n"
        "+++ b/.agents/rules/okr-gate.md\n"
        "@@ -1,3 +1,3 @@\n"
        "-# Rule definition\n"
        "+# Updated rule\n"
        "diff --git a/queue_engine/worker.py b/queue_engine/worker.py\n"
        "--- a/queue_engine/worker.py\n"
        "+++ b/queue_engine/worker.py\n"
        "@@ -10,3 +10,3 @@\n"
        "-# governed logic\n"
        "+# icm governed worker implementation\n"
    )

    packet = prepare_blind_ab_packet(
        campaign_id="CAMP-2026-03",
        task_id="EXP-009",
        baseline_diff=diff_baseline,
        governed_diff=diff_governed,
        seed=100,
    )

    assert packet["campaign_id"] == "CAMP-2026-03"
    assert packet["task_id"] == "EXP-009"
    assert "blind_packet" in packet
    assert "sealed_key" in packet

    # Sealed key maps Alpha and Beta to baseline and governed
    sealed = packet["sealed_key"]
    assert set(sealed.keys()) == {"Arm_Alpha", "Arm_Beta"}
    assert set(sealed.values()) == {"baseline", "governed"}

    # Neither blinded diff contains tasks/TSK-* or .agents/*
    for arm in ("Arm_Alpha", "Arm_Beta"):
        arm_diff = packet["blind_packet"][arm]
        assert "tasks/TSK-" not in arm_diff
        assert ".agents/" not in arm_diff
        # Verify case-insensitive tokens were redacted
        assert "baseline" not in arm_diff.lower()
        assert "governed" not in arm_diff.lower()
        assert "icm" not in arm_diff.lower()
        assert "[ARM_REDACTED]" in arm_diff


def test_compute_quality_ci():
    """Verify compute_quality_ci computes mean paired deltas and 95% bootstrap intervals."""
    # Paired runs: Governed consistently outperforms Baseline
    pair_1 = (
        {"correctness": 3, "engineering": 3, "maintainability": 3, "process": 3, "design": None, "normalized_pct": 60.0},
        {"correctness": 5, "engineering": 5, "maintainability": 5, "process": 5, "design": None, "normalized_pct": 100.0},
    )
    pair_2 = (
        {"correctness": 4, "engineering": 3, "maintainability": 3, "process": 4, "design": None, "normalized_pct": 70.0},
        {"correctness": 5, "engineering": 5, "maintainability": 5, "process": 5, "design": None, "normalized_pct": 100.0},
    )
    pair_3 = (
        {"correctness": 3, "engineering": 4, "maintainability": 4, "process": 3, "design": None, "normalized_pct": 70.0},
        {"correctness": 5, "engineering": 5, "maintainability": 5, "process": 5, "design": None, "normalized_pct": 100.0},
    )

    ci_results = compute_quality_ci([pair_1, pair_2, pair_3], seed=42, iterations=500)

    assert ci_results["sample_count"] == 3
    # Correctness deltas: [2, 1, 2] -> mean = 1.667
    corr = ci_results["correctness"]
    assert corr["mean_delta"] == pytest.approx(1.667, abs=0.01)
    assert corr["ci_95"][0] <= corr["mean_delta"] <= corr["ci_95"][1]

    # Engineering deltas: [2, 2, 1] -> mean = 1.667
    eng = ci_results["engineering"]
    assert eng["mean_delta"] == pytest.approx(1.667, abs=0.01)
    assert eng["ci_95"][0] <= eng["mean_delta"] <= eng["ci_95"][1]

    # Normalized pct deltas: [40.0, 30.0, 30.0] -> mean = 33.333
    pct = ci_results["normalized_pct"]
    assert pct["mean_delta"] == pytest.approx(33.333, abs=0.05)
    assert pct["ci_95"][0] <= pct["mean_delta"] <= pct["ci_95"][1]

    # Design was None for all pairs: returns None
    design_ci = ci_results["design"]
    assert design_ci["mean_delta"] is None
    assert design_ci["ci_95"] is None
    assert design_ci["n"] == 0
