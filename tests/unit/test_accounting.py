import json
import sqlite3
from pathlib import Path
import pytest

import ledger


def test_acc_01_hand_calculated_rate_fixture(tmp_path: Path):
    """
    ACC-01: Use a tiny hand-calculated rate-card fixture.
    Expected: Result agrees with documented decimal/rounding rules.
    """
    db_file = tmp_path / "acc01.db"
    conn = ledger.get_connection(db_file)

    # Insert deterministic test rates
    with conn:
        conn.execute(
            """
            INSERT INTO pricing (
                model, input_usd_per_mtok, cache_read_usd_per_mtok, output_usd_per_mtok,
                source_url, fetched_at, cache_accounting
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("test-calc-model", 2.0, 0.5, 10.0, "https://example.com/rates", "2026-10-02T00:00:00Z", "separate"),
        )

    # Calculation:
    # 500,000 input tokens * $2.00 / 1M = $1.000000
    # 200,000 cache read tokens * $0.50 / 1M = $0.100000
    # 50,000 output tokens * $10.00 / 1M = $0.500000
    # Expected total = $1.600000
    res = ledger.calculate_cost_detailed(
        input_tokens=500_000,
        cache_read_tokens=200_000,
        output_tokens=50_000,
        model="test-calc-model",
        conn=conn,
    )

    assert res["cost_status"] == "usage_estimate"
    assert res["cost_usd"] == 1.600000
    assert len(res["reasons"]) == 0

    conn.close()


def test_acc_02_subset_cache_accounting(tmp_path: Path):
    """
    ACC-02: Cache counters are a subset of provider input tokens.
    Expected: Cached and uncached input charged once under that adapter's rules.
    """
    db_file = tmp_path / "acc02.db"
    conn = ledger.get_connection(db_file)

    with conn:
        conn.execute(
            """
            INSERT INTO pricing (
                model, input_usd_per_mtok, cache_read_usd_per_mtok, output_usd_per_mtok,
                source_url, fetched_at, cache_accounting
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("test-subset-model", 3.0, 0.75, 12.0, "https://example.com/rates", "2026-10-02T00:00:00Z", "subset"),
        )

    # In subset accounting:
    # Total input reported by provider = 1,000,000 (which contains 400,000 cache reads)
    # Uncached input = 1,000,000 - 400,000 = 600,000
    # Uncached input cost: 600,000 * $3.00 / 1M = $1.800000
    # Cache read cost:     400,000 * $0.75 / 1M = $0.300000
    # Output cost:         100,000 * $12.00 / 1M = $1.200000
    # Expected total = 1.80 + 0.30 + 1.20 = $3.300000
    res = ledger.calculate_cost_detailed(
        input_tokens=1_000_000,
        cache_read_tokens=400_000,
        output_tokens=100_000,
        model="test-subset-model",
        conn=conn,
    )

    assert res["cost_status"] == "usage_estimate"
    assert res["cost_usd"] == 3.300000

    conn.close()


def test_acc_03_separate_cache_accounting(tmp_path: Path):
    """
    ACC-03: Cache counters are separate under another adapter.
    Expected: Correct total without imposing the previous provider's semantics.
    """
    db_file = tmp_path / "acc03.db"
    conn = ledger.get_connection(db_file)

    with conn:
        conn.execute(
            """
            INSERT INTO pricing (
                model, input_usd_per_mtok, cache_read_usd_per_mtok, output_usd_per_mtok,
                source_url, fetched_at, cache_accounting
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("test-separate-model", 3.0, 0.75, 12.0, "https://example.com/rates", "2026-10-02T00:00:00Z", "separate"),
        )

    # In separate accounting:
    # input_tokens = 600,000 (uncached only)
    # cache_read_tokens = 400,000
    # output_tokens = 100,000
    # Expected total = 600,000 * 3.0/1M + 400,000 * 0.75/1M + 100,000 * 12.0/1M = 1.80 + 0.30 + 1.20 = $3.300000
    res = ledger.calculate_cost_detailed(
        input_tokens=600_000,
        cache_read_tokens=400_000,
        output_tokens=100_000,
        model="test-separate-model",
        conn=conn,
    )

    assert res["cost_status"] == "usage_estimate"
    assert res["cost_usd"] == 3.300000

    conn.close()


def test_acc_04_thinking_tokens_undocumented_billing_unavailable(tmp_path: Path):
    """
    ACC-04: Thinking tokens lack documented billing semantics.
    Expected: No guessed bill; unavailable or qualified cost status.
    """
    db_file = tmp_path / "acc04.db"
    conn = ledger.get_connection(db_file)

    with conn:
        conn.execute(
            """
            INSERT INTO pricing (
                model, input_usd_per_mtok, cache_read_usd_per_mtok, output_usd_per_mtok,
                source_url, fetched_at, cache_accounting, thinking_billed_as, thinking_usd_per_mtok
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("test-thinking-undoc", 1.0, 0.25, 4.0, "https://example.com/rates", "2026-10-02T00:00:00Z", "separate", None, None),
        )
        conn.execute(
            """
            INSERT INTO pricing (
                model, input_usd_per_mtok, cache_read_usd_per_mtok, output_usd_per_mtok,
                source_url, fetched_at, cache_accounting, thinking_billed_as, thinking_usd_per_mtok
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("test-thinking-doc", 1.0, 0.25, 4.0, "https://example.com/rates", "2026-10-02T00:00:00Z", "separate", "output", None),
        )

    # 1. Undocumented thinking token semantics: must NOT guess or silently omit!
    res_undoc = ledger.calculate_cost_detailed(
        input_tokens=100_000,
        cache_read_tokens=0,
        output_tokens=20_000,
        thinking_tokens=50_000,  # Has thinking tokens, but billing semantics unknown
        model="test-thinking-undoc",
        conn=conn,
    )
    assert res_undoc["cost_usd"] is None
    assert res_undoc["cost_status"] == "unavailable"
    assert "thinking_token_pricing_unspecified" in res_undoc["reasons"]

    # 2. Documented thinking tokens billed as output:
    # 100k input * 1.0/1M = 0.10
    # 20k output * 4.0/1M = 0.08
    # 50k thinking * 4.0/1M = 0.20
    # Total = 0.10 + 0.08 + 0.20 = $0.380000
    res_doc = ledger.calculate_cost_detailed(
        input_tokens=100_000,
        cache_read_tokens=0,
        output_tokens=20_000,
        thinking_tokens=50_000,
        model="test-thinking-doc",
        conn=conn,
    )
    assert res_doc["cost_status"] == "usage_estimate"
    assert res_doc["cost_usd"] == 0.380000

    conn.close()


def test_acc_05_missing_model_rate_unavailable(tmp_path: Path):
    """
    ACC-05: Model rate is absent.
    Expected: Cost unavailable rather than zero or borrowed from another model.
    """
    db_file = tmp_path / "acc05.db"
    conn = ledger.get_connection(db_file)
    ledger.seed_pricing(conn=conn)

    res = ledger.calculate_cost_detailed(
        input_tokens=500_000,
        cache_read_tokens=100_000,
        output_tokens=10_000,
        model="completely-unregistered-model-2029",
        conn=conn,
    )

    assert res["cost_usd"] is None
    assert res["cost_status"] == "unavailable"
    assert "model_rate_absent" in res["reasons"]

    conn.close()


def test_acc_06_simulation_tagged_separately_empirical_unchanged(tmp_path: Path):
    """
    ACC-06: Apply a different model rate to a recorded run.
    Expected: Simulation labelled separately; empirical totals unchanged.
    """
    db_file = tmp_path / "acc06.db"
    conn = ledger.get_connection(db_file)
    ledger.seed_pricing(conn=conn)

    # Record an empirical run with gemini-2.5-pro for baseline and icm
    run_id = ledger.record_run(
        task_id="EXP-SIM",
        arm="baseline",
        model="gemini-2.5-pro",
        run_index=1,
        timestamp="2026-09-10T12:00:00Z",
        input_tokens=1_000_000,
        output_tokens=100_000,
        cache_read_tokens=200_000,
        num_turns=3,
        duration_seconds=15.0,
        source_kind="live",
        evidence_status="verified",
        conn=conn,
    )
    ledger.record_run(
        task_id="EXP-SIM",
        arm="icm",
        model="gemini-2.5-pro",
        run_index=1,
        timestamp="2026-09-10T12:01:00Z",
        input_tokens=500_000,
        output_tokens=80_000,
        cache_read_tokens=400_000,
        num_turns=2,
        duration_seconds=10.0,
        source_kind="live",
        evidence_status="verified",
        conn=conn,
    )

    # 1. Standard empirical summary
    s_empirical = ledger.task_summary("EXP-SIM", conn=conn)
    assert s_empirical["has_measured_data"] is True
    assert s_empirical["is_simulation"] is False
    assert s_empirical["measured_runs_count"] == 2
    assert s_empirical["arms"]["baseline"]["model"] == "gemini-2.5-pro"
    pro_cost = s_empirical["arms"]["baseline"]["mean_cost_usd"]
    assert pro_cost is not None and pro_cost > 0

    # 2. Simulated summary under gemini-3.8-flash
    s_sim = ledger.task_summary("EXP-SIM", model_override="gemini-3.8-flash", conn=conn)
    assert s_sim["is_simulation"] is True
    assert s_sim["arms"]["baseline"]["model"] == "gemini-3.8-flash"
    flash_cost = s_sim["arms"]["baseline"]["mean_cost_usd"]
    assert flash_cost is not None and flash_cost > 0
    # Flash rate is significantly cheaper than Pro
    assert flash_cost < pro_cost

    # 3. Assert database row and cumulative empirical totals remain uncorrupted
    cursor = conn.cursor()
    cursor.execute("SELECT model, is_simulation, cost_usd FROM runs WHERE id = ?", (run_id,))
    row = dict(cursor.fetchone())
    assert row["model"] == "gemini-2.5-pro"
    assert row["is_simulation"] == 0
    assert row["cost_usd"] == pro_cost

    cum = ledger.cumulative_savings(conn=conn)
    assert cum["has_measured_data"] is True
    assert cum["total_runs"] == 2
    assert cum["total_baseline_cost_usd"] == pro_cost

    conn.close()


def test_acc_07_incomplete_telemetry_partial_cost_marked_incomplete(tmp_path: Path):
    """
    ACC-07: Incomplete telemetry has partial usage.
    Expected: Partial cost labelled incomplete; not a complete-run bill; excluded from measured totals.
    """
    db_file = tmp_path / "acc07.db"
    conn = ledger.get_connection(db_file)
    ledger.seed_pricing(conn=conn)

    # Detailed cost calculation directly
    cost_info = ledger.calculate_cost_detailed(
        input_tokens=20_000,
        cache_read_tokens=5_000,
        output_tokens=1_000,
        model="gemini-2.5-pro",
        conn=conn,
        is_partial=True,
    )
    assert cost_info["cost_status"] == "incomplete"
    assert "partial_telemetry" in cost_info["reasons"]
    assert cost_info["cost_usd"] is not None

    # Record incomplete run in DB (with live provenance, but cost_status incomplete)
    run_id = ledger.record_run(
        task_id="EXP-PARTIAL",
        arm="baseline",
        model="gemini-2.5-pro",
        run_index=1,
        timestamp="2026-09-10T12:00:00Z",
        input_tokens=20_000,
        output_tokens=1_000,
        cache_read_tokens=5_000,
        cost_status="incomplete",
        source_kind="live",
        evidence_status="verified",
        exclusion_reasons=["partial_telemetry"],
        conn=conn,
    )

    summary = ledger.task_summary("EXP-PARTIAL", conn=conn)
    # Must be excluded from measured totals because cost is incomplete
    assert summary["measured_runs_count"] == 0
    assert summary["has_measured_data"] is False
    assert len(summary["excluded_runs"]) == 1
    assert "cost_incomplete" in summary["excluded_runs"][0]["exclusion_reasons"]

    conn.close()


def test_acc_unknown_cache_accounting_mode(tmp_path: Path):
    """
    ACC-02/03: Pricing table specifies an unsupported or unknown cache_accounting mode.
    Expected: Cost calculation returns unavailable rather than guessing or defaulting to separate.
    """
    db_file = tmp_path / "acc_unknown_cache.db"
    conn = ledger.get_connection(db_file)
    with conn:
        conn.execute(
            """
            INSERT INTO pricing (
                model, input_usd_per_mtok, cache_read_usd_per_mtok, output_usd_per_mtok,
                source_url, fetched_at, cache_accounting
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("test-unknown-cache", 3.0, 0.75, 12.0, "https://example.com/rates", "2026-10-02T00:00:00Z", "unsupported_future_mode"),
        )
    res = ledger.calculate_cost_detailed(
        input_tokens=1000,
        cache_read_tokens=200,
        output_tokens=100,
        model="test-unknown-cache",
        conn=conn,
    )
    assert res["cost_status"] == "unavailable"
    assert res["cost_usd"] is None
    assert any("unknown_cache_accounting" in r for r in res["reasons"])
    conn.close()


def test_acc_06_simulation_on_pure_fixture_task_not_measured(tmp_path: Path):
    """
    ACC-06 Edge Case: Running a pricing simulation on a task with only fixture runs.
    Expected: has_measured_data remains False; fixtures cannot be promoted to measured empirical claims.
    """
    db_file = tmp_path / "acc06_fix.db"
    conn = ledger.get_connection(db_file)
    ledger.seed_pricing(conn=conn)
    ledger.record_run(
        task_id="EXP-FIX-TASK",
        arm="baseline",
        model="gemini-2.5-pro",
        run_index=1,
        timestamp="2026-09-10T12:00:00Z",
        input_tokens=10000,
        output_tokens=500,
        source_kind="fixture",
        evidence_status="unverified",
        exclusion_reasons=["fixture_replay"],
        conn=conn,
    )
    ledger.record_run(
        task_id="EXP-FIX-TASK",
        arm="icm",
        model="gemini-2.5-pro",
        run_index=1,
        timestamp="2026-09-10T12:01:00Z",
        input_tokens=5000,
        output_tokens=300,
        source_kind="fixture",
        evidence_status="unverified",
        exclusion_reasons=["fixture_replay"],
        conn=conn,
    )
    sim_summary = ledger.task_summary("EXP-FIX-TASK", model_override="gemini-3.8-flash", conn=conn)
    assert sim_summary["has_measured_data"] is False
    assert sim_summary["measured_runs_count"] == 0
    assert sim_summary["is_simulation"] is True
    conn.close()

