#!/usr/bin/env python3
"""Unit and round-trip tests for scripts/hydrate_db.py."""

import json
import sys
from pathlib import Path

import pytest

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = WORKSPACE_ROOT / "scripts"
DASHBOARD_DIR = WORKSPACE_ROOT / "dashboard"
for p in (str(SCRIPTS_DIR), str(DASHBOARD_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

import build_data
import hydrate_db


def test_hydrate_round_trip_matches_snapshot(tmp_path):
    snapshot_path = WORKSPACE_ROOT / "dashboard" / "public" / "data.json"
    original = json.loads(snapshot_path.read_text(encoding="utf-8"))
    db_path = tmp_path / "usage.db"

    summary = hydrate_db.hydrate_db_from_snapshot(
        snapshot_path=snapshot_path,
        db_path=db_path,
        workspace_root=WORKSPACE_ROOT,
        overwrite=True,
    )

    expected_runs = len(original["runs"])
    expected_priced = sum(1 for r in original["runs"] if r.get("cost_usd") is not None)
    assert summary["inserted"] == expected_runs
    assert summary["total"] == expected_runs
    assert summary["priced"] == expected_priced
    assert summary["hashed_evidence"] == expected_runs

    rebuilt = build_data.build_data_payload(db_path=db_path)
    assert len(rebuilt["runs"]) == expected_runs
    assert sum(1 for r in rebuilt["runs"] if r.get("cost_usd") is not None) == expected_priced
    assert rebuilt["iteration_lineage"]["has_data"] is True
    assert rebuilt["headline"]["sentence"] == original["headline"]["sentence"]


def test_hydrate_refuses_overwrite_without_force(tmp_path):
    snapshot_path = WORKSPACE_ROOT / "dashboard" / "public" / "data.json"
    db_path = tmp_path / "existing.db"
    db_path.write_text("placeholder", encoding="utf-8")

    with pytest.raises(FileExistsError):
        hydrate_db.hydrate_db_from_snapshot(snapshot_path=snapshot_path, db_path=db_path)
