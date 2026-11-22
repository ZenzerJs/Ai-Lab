#!/usr/bin/env python3
"""Unit tests for Devin ACU telemetry extraction, cost normalization, and dashboard export."""

import hashlib
import io
import json
import sqlite3
import sys
from pathlib import Path
from unittest import mock

import pytest

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = WORKSPACE_ROOT / "scripts"
DASHBOARD_DIR = WORKSPACE_ROOT / "dashboard"
for p in (str(SCRIPTS_DIR), str(DASHBOARD_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

import build_data
import ledger
import pricing
import runner


class _FakeHTTPResponse:
    def __init__(self, payload: dict):
        self._body = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_default_and_configurable_devin_acu_rate(monkeypatch):
    monkeypatch.delenv("DEVIN_ACU_USD_RATE", raising=False)
    assert pricing.get_devin_acu_usd_rate() == pytest.approx(2.25)

    monkeypatch.setenv("DEVIN_ACU_USD_RATE", "3.50")
    assert pricing.get_devin_acu_usd_rate() == pytest.approx(3.50)

    assert pricing.get_devin_acu_usd_rate(rate_override=1.80) == pytest.approx(1.80)

    with pytest.raises(ValueError):
        pricing.get_devin_acu_usd_rate(rate_override=0)
    with pytest.raises(ValueError):
        pricing.get_devin_acu_usd_rate(rate_override=-2.0)


def test_calculate_acu_cost_and_classification(monkeypatch):
    monkeypatch.delenv("DEVIN_ACU_USD_RATE", raising=False)
    res = pricing.calculate_acu_cost(1.2)
    assert res["acus_consumed"] == pytest.approx(1.2)
    assert res["acu_usd_rate"] == pytest.approx(2.25)
    assert res["estimated_cost_usd"] == pytest.approx(2.7)
    assert res["cost_usd"] == pytest.approx(2.7)
    assert res["cost_status"] == "estimated_acu_derived"
    assert res["cost_source"] == "estimated_acu_derived"

    none_res = pricing.calculate_acu_cost(None)
    assert none_res["cost_usd"] is None
    assert none_res["cost_source"] == "unavailable"

    assert pricing.classify_cost_source({"cost_usd": 0.5, "cost_status": "usage_estimate"}) == "billed_direct"
    assert (
        pricing.classify_cost_source(
            {"cost_usd": 2.7, "acus_consumed": 1.2, "cost_status": "estimated_acu_derived"}
        )
        == "estimated_acu_derived"
    )
    assert pricing.classify_cost_source({"cost_usd": None, "cost_status": "unavailable"}) == "unavailable"


def test_extract_and_fetch_devin_session_acus():
    assert runner.extract_acus_consumed({"acus_consumed": 0.75}) == pytest.approx(0.75)
    assert runner.extract_acus_consumed({"usage": {"acus_consumed": 1.5}}) == pytest.approx(1.5)
    assert runner.extract_acus_consumed({"session": {"acus_consumed": 2.0}}) == pytest.approx(2.0)
    assert runner.extract_acus_consumed({"session_id": "devin-abc"}) is None

    with pytest.raises(ValueError):
        runner.extract_acus_consumed({"acus_consumed": -0.5})

    captured = {}

    def fake_urlopen(req, timeout=15.0):
        captured["url"] = req.full_url
        captured["auth"] = req.get_header("Authorization")
        captured["method"] = req.get_method()
        return _FakeHTTPResponse({"session_id": "devin-xyz", "acus_consumed": 0.48})

    with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
        acus = runner.fetch_devin_session_acus(
            devin_id="devin-xyz",
            org_id="org-123",
            api_key="test-token-value",
        )

    assert acus == pytest.approx(0.48)
    assert captured["url"] == "https://api.devin.ai/v3/organizations/org-123/sessions/devin-xyz"
    assert captured["auth"] == "Bearer test-token-value"
    assert captured["method"] == "GET"


def test_ndjson_telemetry_extracts_acus_and_devin_session_id():
    lines = [
        json.dumps({"type": "init", "devin_session_id": "devin-999", "model": "swe-2-max-lightning"}),
        json.dumps({"type": "result", "acus_consumed": 0.64, "duration_seconds": 12.5}),
    ]
    parsed = ledger.validate_and_parse_telemetry(lines)
    assert parsed["acus_consumed"] == pytest.approx(0.64)
    assert parsed["devin_session_id"] == "devin-999"


def test_ledger_persists_acu_telemetry_and_separates_cost_sources(tmp_path, monkeypatch):
    monkeypatch.delenv("DEVIN_ACU_USD_RATE", raising=False)
    db_path = tmp_path / "usage.db"
    evidence_file = tmp_path / "ev.ndjson"
    evidence_bytes = b'{"type":"result","acus_consumed":0.5}\n'
    evidence_file.write_bytes(evidence_bytes)
    ev_hash = hashlib.sha256(evidence_bytes).hexdigest()

    conn = ledger.get_connection(db_path)
    try:
        # Direct billed run (Gemini API)
        direct_id = ledger.record_run(
            task_id="BENCH-001",
            arm="baseline",
            model="gemini-3.8-flash",
            run_index=1,
            timestamp="2026-11-22T00:00:00Z",
            input_tokens=100_000,
            output_tokens=10_000,
            cache_read_tokens=20_000,
            source_kind="live",
            evidence_status="verified",
            evidence_ref=str(evidence_file),
            evidence_hash=ev_hash,
            verification_status="passed",
            conn=conn,
        )
        direct_row = dict(conn.execute("SELECT * FROM runs WHERE id = ?", (direct_id,)).fetchone())
        assert direct_row["cost_source"] == "billed_direct"
        assert direct_row["cost_status"] == "usage_estimate"
        assert direct_row["cost_usd"] > 0
        assert direct_row["acus_consumed"] is None

        # ACU-derived Devin run (no raw token counts)
        acu_id = ledger.record_run(
            task_id="BENCH-001",
            arm="icm",
            model="devin-session-v3",
            run_index=1,
            timestamp="2026-11-22T00:05:00Z",
            input_tokens=None,
            output_tokens=None,
            acus_consumed=0.8,
            source_kind="live",
            evidence_status="verified",
            evidence_ref=str(evidence_file),
            evidence_hash=ev_hash,
            verification_status="passed",
            conn=conn,
        )
        acu_row = dict(conn.execute("SELECT * FROM runs WHERE id = ?", (acu_id,)).fetchone())
        assert acu_row["cost_source"] == "estimated_acu_derived"
        assert acu_row["cost_status"] == "estimated_acu_derived"
        assert acu_row["acus_consumed"] == pytest.approx(0.8)
        assert acu_row["acu_usd_rate"] == pytest.approx(2.25)
        assert acu_row["estimated_cost_usd"] == pytest.approx(1.8)
        assert acu_row["cost_usd"] == pytest.approx(1.8)

        elig = ledger.evaluate_run_eligibility(acu_row, capture_policy="approved")
        assert elig["is_cost_complete"] is True
        assert elig["is_comparison_eligible"] is True

        pub = ledger.to_public_run(acu_row)
        assert pub["acus_consumed"] == pytest.approx(0.8)
        assert pub["cost_source"] == "estimated_acu_derived"
        assert pub["estimated_cost_usd"] == pytest.approx(1.8)
    finally:
        conn.close()


def test_build_data_payload_emits_acu_fields_and_cost_basis(tmp_path, monkeypatch):
    monkeypatch.delenv("DEVIN_ACU_USD_RATE", raising=False)
    db_path = tmp_path / "usage.db"
    evidence_file = tmp_path / "ev.ndjson"
    evidence_bytes = b'{"type":"result"}\n'
    evidence_file.write_bytes(evidence_bytes)
    ev_hash = hashlib.sha256(evidence_bytes).hexdigest()

    conn = ledger.get_connection(db_path)
    try:
        # Paired ACU-derived Devin runs
        ledger.record_run(
            task_id="BENCH-001",
            arm="baseline",
            model="devin-session-v3",
            run_index=1,
            timestamp="2026-11-22T00:00:00Z",
            input_tokens=None,
            output_tokens=None,
            acus_consumed=2.0,
            source_kind="live",
            evidence_status="verified",
            evidence_ref=str(evidence_file),
            evidence_hash=ev_hash,
            verification_status="passed",
            conn=conn,
        )
        ledger.record_run(
            task_id="BENCH-001",
            arm="icm",
            model="devin-session-v3",
            run_index=1,
            timestamp="2026-11-22T00:01:00Z",
            input_tokens=None,
            output_tokens=None,
            acus_consumed=1.5,
            source_kind="live",
            evidence_status="verified",
            evidence_ref=str(evidence_file),
            evidence_hash=ev_hash,
            verification_status="passed",
            conn=conn,
        )
    finally:
        conn.close()

    payload = build_data.build_data_payload(db_path=db_path)
    assert payload["acu_pricing"]["devin_acu_usd_rate"] == pytest.approx(2.25)
    assert len(payload["runs"]) == 2
    assert all(r["cost_source"] == "estimated_acu_derived" for r in payload["runs"])
    assert [r["acus_consumed"] for r in payload["runs"]] == [2.0, 1.5]
    assert [r["estimated_cost_usd"] for r in payload["runs"]] == [4.5, 3.375]

    headline = payload["headline"]
    assert headline is not None
    scope = headline["scope"]
    assert scope["billed_direct_run_count"] == 0
    assert scope["estimated_acu_derived_run_count"] == 2
    assert scope["cost_basis"] == "ACU Derived"
    assert scope["signed_cost_label"] == "-25.0% savings"
    assert scope["paired_priced_task_count"] == 1


def test_ndjson_nested_result_usage_and_replay_dedup():
    lines = [
        json.dumps({"event_id": "e1", "type": "turn", "turn": 1, "acus_consumed": 0.25}),
        json.dumps({"event_id": "e2", "type": "result", "result": {"usage": {"acus_consumed": 1.4}}}),
        json.dumps({"event_id": "e1", "type": "turn", "turn": 1, "acus_consumed": 0.25}),
    ]
    parsed = ledger.validate_and_parse_telemetry(lines)
    assert parsed["acus_consumed"] == pytest.approx(1.4)


def test_record_imported_run_detects_conflicting_acus(tmp_path):
    db_path = tmp_path / "usage.db"
    conn = ledger.get_connection(db_path)
    try:
        base_run = {
            "import_id": "imp-acu-1",
            "task_id": "BENCH-001",
            "arm": "baseline",
            "model": "devin-session-v3",
            "run_index": 1,
            "timestamp": "2026-11-22T00:00:00Z",
            "acus_consumed": 1.0,
        }
        first_id = ledger.import_run(conn, base_run)
        assert ledger.import_run(conn, dict(base_run)) == first_id

        changed = dict(base_run, acus_consumed=1.5)
        with pytest.raises(ledger.DuplicateConflictError):
            ledger.import_run(conn, changed)
    finally:
        conn.close()


def test_cumulative_savings_cost_per_mtok_excludes_acu_only_pairs(tmp_path, monkeypatch):
    monkeypatch.delenv("DEVIN_ACU_USD_RATE", raising=False)
    db_path = tmp_path / "usage.db"
    ev = tmp_path / "ev.ndjson"
    ev_bytes = b'{"type":"result"}\n'
    ev.write_bytes(ev_bytes)
    ev_hash = hashlib.sha256(ev_bytes).hexdigest()

    conn = ledger.get_connection(db_path)
    try:
        # Token-priced pair (Gemini)
        ledger.record_run(
            task_id="BENCH-001",
            arm="baseline",
            model="gemini-3.8-flash",
            run_index=1,
            timestamp="2026-11-22T00:00:00Z",
            input_tokens=1_000_000,
            output_tokens=0,
            source_kind="live",
            evidence_status="verified",
            evidence_ref=str(ev),
            evidence_hash=ev_hash,
            verification_status="passed",
            conn=conn,
        )
        ledger.record_run(
            task_id="BENCH-001",
            arm="icm",
            model="gemini-3.8-flash",
            run_index=1,
            timestamp="2026-11-22T00:01:00Z",
            input_tokens=500_000,
            output_tokens=0,
            source_kind="live",
            evidence_status="verified",
            evidence_ref=str(ev),
            evidence_hash=ev_hash,
            verification_status="passed",
            conn=conn,
        )
        cum_token_only = ledger.cumulative_savings(conn=conn)

        # Add an ACU-only pair (no tokens, $22.50 baseline / $11.25 icm)
        ledger.record_run(
            task_id="BENCH-002",
            arm="baseline",
            model="devin-session-v3",
            run_index=1,
            timestamp="2026-11-22T00:02:00Z",
            input_tokens=None,
            output_tokens=None,
            acus_consumed=10.0,
            source_kind="live",
            evidence_status="verified",
            evidence_ref=str(ev),
            evidence_hash=ev_hash,
            verification_status="passed",
            conn=conn,
        )
        ledger.record_run(
            task_id="BENCH-002",
            arm="icm",
            model="devin-session-v3",
            run_index=1,
            timestamp="2026-11-22T00:03:00Z",
            input_tokens=None,
            output_tokens=None,
            acus_consumed=5.0,
            source_kind="live",
            evidence_status="verified",
            evidence_ref=str(ev),
            evidence_hash=ev_hash,
            verification_status="passed",
            conn=conn,
        )
        cum_mixed = ledger.cumulative_savings(conn=conn)
        assert cum_mixed["cost_per_mtok_baseline"] == pytest.approx(cum_token_only["cost_per_mtok_baseline"])
        assert cum_mixed["cost_per_mtok_icm"] == pytest.approx(cum_token_only["cost_per_mtok_icm"])
    finally:
        conn.close()


def test_build_declared_benchmarks_excludes_invalidated_evidence(tmp_path):
    bench_dir = tmp_path / "benchmarks"
    (bench_dir / "BENCH-999").mkdir(parents=True)
    runs = [
        {
            "task_id": "BENCH-999",
            "source_kind": "live",
            "is_simulation": False,
            "evidence_status": "verified",
            "exclusion_reasons": ["evidence_hash_mismatch"],
        }
    ]
    declared = build_data.build_declared_benchmarks([], runs=runs, benchmarks_dir=bench_dir)
    assert declared == [
        {"task_id": "BENCH-999", "measured_runs": 0, "status": "suite present, unmeasured"}
    ]

