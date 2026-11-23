#!/usr/bin/env python3
"""Unit tests for Devin ACU telemetry metadata extraction and cost_usd integrity."""

import hashlib
import json
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


def test_validate_acus_consumed():
    assert pricing.validate_acus_consumed(None) is None
    assert pricing.validate_acus_consumed(0) is None
    assert pricing.validate_acus_consumed(0.0) is None
    assert pricing.validate_acus_consumed("0") is None
    assert pricing.validate_acus_consumed(1e-7) is None
    assert pricing.validate_acus_consumed(1e-6) == pytest.approx(1e-6)
    assert pricing.validate_acus_consumed(1.23456789) == pytest.approx(1.234568)
    assert pricing.validate_acus_consumed("0.5") == pytest.approx(0.5)

    for bad in (True, False, -0.1, float("nan"), float("inf"), "abc"):
        with pytest.raises(ValueError):
            pricing.validate_acus_consumed(bad)


def test_extract_and_fetch_devin_session_acus():
    assert runner.extract_acus_consumed({"acus_consumed": 0.75}) == pytest.approx(0.75)
    assert runner.extract_acus_consumed({"usage": {"acus_consumed": 1.5}}) == pytest.approx(1.5)
    assert runner.extract_acus_consumed({"session": {"acus_consumed": 2.0}}) == pytest.approx(2.0)
    assert runner.extract_acus_consumed({"session_id": "devin-abc"}) is None
    assert runner.extract_acus_consumed({"acus_consumed": 0.0}) is None

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

    with mock.patch(
        "urllib.request.urlopen",
        return_value=_FakeHTTPResponse({"session_id": "devin-zero", "acus_consumed": 0.0}),
    ):
        zero_acus = runner.fetch_devin_session_acus(
            devin_id="devin-zero",
            org_id="org-123",
            api_key="test-token-value",
        )
    assert zero_acus is None


def test_ndjson_nested_result_usage_and_replay_dedup():
    lines = [
        json.dumps({"event_id": "e1", "type": "init", "devin_session_id": "devin-999", "acus_consumed": 0.25}),
        json.dumps({"event_id": "e2", "type": "result", "result": {"usage": {"acus_consumed": 1.4}}}),
        json.dumps({"event_id": "e1", "type": "init", "devin_session_id": "devin-999", "acus_consumed": 0.25}),
    ]
    parsed = ledger.validate_and_parse_telemetry(lines)
    assert parsed["acus_consumed"] == pytest.approx(1.4)
    assert parsed["devin_session_id"] == "devin-999"


def test_devin_acu_metadata_never_converts_to_cost_usd(tmp_path):
    """REVIEW.md invariant: ACUs are optional metadata only; Devin runs stay unpriced."""
    db_path = tmp_path / "usage.db"
    evidence_file = tmp_path / "ev.ndjson"
    evidence_bytes = b'{"type":"result","acus_consumed":0.8}\n'
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
        assert direct_row["cost_status"] == "usage_estimate"
        assert direct_row["cost_usd"] > 0
        assert direct_row["acus_consumed"] is None

        # Devin run with ACUs but no direct token/USD billing MUST stay unpriced
        devin_id = ledger.record_run(
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
        devin_row = dict(conn.execute("SELECT * FROM runs WHERE id = ?", (devin_id,)).fetchone())
        assert devin_row["acus_consumed"] == pytest.approx(0.8)
        assert devin_row["cost_status"] == "unavailable"
        assert devin_row["cost_usd"] is None

        elig = ledger.evaluate_run_eligibility(devin_row, capture_policy="approved")
        assert elig["is_cost_complete"] is False

        pub = ledger.to_public_run(devin_row)
        assert pub["acus_consumed"] == pytest.approx(0.8)
        assert pub["cost_usd"] is None
        assert pub["cost_status"] == "unavailable"
    finally:
        conn.close()


def test_import_run_detects_conflicting_acus(tmp_path):
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


def test_build_data_exports_acus_as_metadata_without_pricing_devin_runs(tmp_path):
    db_path = tmp_path / "usage.db"
    evidence_file = tmp_path / "ev.ndjson"
    evidence_bytes = b'{"type":"result"}\n'
    evidence_file.write_bytes(evidence_bytes)
    ev_hash = hashlib.sha256(evidence_bytes).hexdigest()

    conn = ledger.get_connection(db_path)
    try:
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
    assert len(payload["runs"]) == 2
    assert [r["acus_consumed"] for r in payload["runs"]] == [2.0, 1.5]
    assert all(r["cost_usd"] is None for r in payload["runs"])
    assert all(r["cost_status"] == "unavailable" for r in payload["runs"])


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
