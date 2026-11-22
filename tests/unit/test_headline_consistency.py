import hashlib
import json
from pathlib import Path

import build_data
import evaluate_all_quality
import ledger


def _seed_paired_db(tmp_path, pairs, extra_unpriced=0):
    tmp_path.mkdir(parents=True, exist_ok=True)
    db = tmp_path / "usage.db"
    evidence = tmp_path / "live.ndjson"
    evidence.write_text('{"event":"start"}\n', encoding="utf-8")
    evidence_hash = hashlib.sha256(evidence.read_bytes()).hexdigest()

    for task_id, base_tokens, icm_tokens in pairs:
        for arm, tokens in (("baseline", base_tokens), ("icm", icm_tokens)):
            ledger.record_run(
                task_id=task_id,
                arm=arm,
                model="gemini-2.5-pro",
                run_index=1,
                timestamp="2026-11-22T12:00:00Z",
                input_tokens=tokens,
                output_tokens=tokens,
                cache_read_tokens=0,
                source_kind="live",
                evidence_status="verified",
                evidence_ref=str(evidence),
                evidence_hash=evidence_hash,
                verification_status="passed",
                db_path=db,
            )

    for idx in range(extra_unpriced):
        ledger.record_run(
            task_id=f"BENCH-90{idx}",
            arm="baseline",
            model="unpriced-custom-model",
            run_index=1,
            timestamp="2026-11-22T12:00:00Z",
            input_tokens=500,
            output_tokens=500,
            cache_read_tokens=0,
            source_kind="live",
            evidence_status="verified",
            evidence_ref=str(evidence),
            evidence_hash=evidence_hash,
            verification_status="passed",
            db_path=db,
        )
    return db


def test_headline_matches_recomputed_cumulative_for_cost_increase_and_savings(tmp_path, monkeypatch):
    monkeypatch.setattr(build_data, "OPS_DB_PATH", tmp_path / "missing.db")
    monkeypatch.setattr(evaluate_all_quality, "evaluate_all", lambda **_: {"tasks": [], "quality_ci": {}})

    # Case 1: Governed costs MORE than baseline (+25.0% cost)
    db_more = _seed_paired_db(
        tmp_path / "more",
        [("BENCH-001", 1000, 1250), ("BENCH-002", 2000, 2500)],
        extra_unpriced=1,
    )
    payload_more = build_data.build_data_payload(db_path=db_more)
    cum_more = payload_more["cumulative"]
    headline_more = payload_more["headline"]
    assert headline_more is not None

    cost_stat = next(s for s in headline_more["stats"] if s["id"] == "cost_reduction")
    recomputed_savings = round(
        (cum_more["total_baseline_cost_usd"] - cum_more["total_icm_cost_usd"])
        / cum_more["total_baseline_cost_usd"]
        * 100.0,
        1,
    )
    assert cost_stat["value"] == recomputed_savings
    assert cost_stat["value"] == round(cum_more["cumulative_savings_percent"], 1)
    assert cost_stat["signed_cost_label"] == "+25.0% cost"
    assert cost_stat["cost_delta_pct"] == 25.0

    scope = headline_more["scope"]
    assert scope["unique_task_count"] == len({t["task_id"] for t in payload_more["tasks"]})
    assert scope["total_run_count"] == len(payload_more["runs"])
    assert scope["priced_run_count"] == sum(1 for r in payload_more["runs"] if r.get("cost_usd") is not None)
    assert scope["pooling_method"] == "pooled_sum"
    assert scope["macro_average_savings_pct"] == -25.0
    assert "macro_average" in scope["pooling_note"]
    assert "+25.0% cost" in headline_more["sentence"]
    assert "pooled_sum" in headline_more["sentence"]
    assert "macro_average" in headline_more["sentence"]
    assert f"{scope['unique_task_count']} tasks" in headline_more["sentence"]
    assert f"{scope['total_run_count']} runs" in headline_more["sentence"]
    assert f"{scope['priced_run_count']} priced runs" in headline_more["sentence"]

    # Case 2: Governed costs LESS than baseline (-40.0% savings)
    db_less = _seed_paired_db(
        tmp_path / "less",
        [("BENCH-001", 1000, 600), ("BENCH-002", 2000, 1200)],
    )
    payload_less = build_data.build_data_payload(db_path=db_less)
    cum_less = payload_less["cumulative"]
    headline_less = payload_less["headline"]
    cost_stat_less = next(s for s in headline_less["stats"] if s["id"] == "cost_reduction")
    assert cost_stat_less["value"] == round(cum_less["cumulative_savings_percent"], 1)
    assert cost_stat_less["signed_cost_label"] == "-40.0% savings"
    assert cost_stat_less["cost_delta_pct"] == -40.0
    assert "-40.0% savings" in headline_less["sentence"]


def test_declared_benchmarks_cross_check_labels_unmeasured_suites(tmp_path):
    bench_dir = tmp_path / "benchmarks"
    (bench_dir / "BENCH-001").mkdir(parents=True)
    (bench_dir / "BENCH-002").mkdir(parents=True)
    (bench_dir / "README.md").write_text("ignore non-dir\n", encoding="utf-8")

    runs = [
        {"task_id": "BENCH-001", "source_kind": "live"},
        {"task_id": "BENCH-002", "source_kind": "imported"},
    ]
    inventory = build_data.build_declared_benchmarks([], runs=runs, benchmarks_dir=bench_dir)
    assert inventory == [
        {"task_id": "BENCH-001", "measured_runs": 1, "status": "measured"},
        {"task_id": "BENCH-002", "measured_runs": 0, "status": "suite present, unmeasured"},
    ]


def test_published_snapshot_headline_matches_recomputed_cumulative():
    snapshot_path = Path(__file__).resolve().parents[2] / "dashboard" / "public" / "data.json"
    data = json.loads(snapshot_path.read_text(encoding="utf-8"))
    cum = data["cumulative"]
    cost_stat = next(s for s in data["headline"]["stats"] if s["id"] == "cost_reduction")
    recomputed = round(
        (cum["total_baseline_cost_usd"] - cum["total_icm_cost_usd"])
        / cum["total_baseline_cost_usd"]
        * 100.0,
        1,
    )
    assert cost_stat["value"] == recomputed
    assert cost_stat["value"] == round(cum["cumulative_savings_percent"], 1)
    assert cost_stat["baseline"] == f"${cum['total_baseline_cost_usd']:.4f}"
    assert cost_stat["icm"] == f"${cum['total_icm_cost_usd']:.4f}"
