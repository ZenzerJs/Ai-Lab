#!/usr/bin/env python3
"""
scripts/hydrate_db.py - Lossless SQLite Hydration from Published Dashboard Snapshot

Rebuilds a working SQLite telemetry database (`data/usage.db`) from a committed
`dashboard/public/data.json` snapshot and its companion `experiments/evidence/*.ndjson`
files, including SHA-256 evidence hashes and backfilled NDJSON cache diagnostics.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

SCRIPTS_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = SCRIPTS_DIR.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import ledger


def _remove_sqlite_files(db_path: Path) -> None:
    for suffix in ("", "-journal", "-wal", "-shm"):
        candidate = Path(f"{db_path}{suffix}")
        if candidate.exists():
            candidate.unlink()


def hydrate_db_from_snapshot(
    snapshot_path: Path,
    db_path: Path,
    *,
    evidence_dir: Optional[Path] = None,
    pricing_path: Optional[Path] = None,
    workspace_root: Optional[Path] = None,
    overwrite: bool = False,
) -> Dict[str, int]:
    """Hydrate a SQLite usage ledger database from a snapshot JSON + evidence dir."""
    snapshot_file = Path(snapshot_path)
    target_db = Path(db_path)
    if not snapshot_file.is_file():
        raise FileNotFoundError(f"Snapshot file not found: {snapshot_file}")

    if target_db.exists():
        if not overwrite:
            raise FileExistsError(
                f"Target database already exists: {target_db} (pass overwrite=True or --force)"
            )
        _remove_sqlite_files(target_db)

    target_db.parent.mkdir(parents=True, exist_ok=True)
    ws_root = Path(workspace_root) if workspace_root is not None else WORKSPACE_ROOT
    ev_dir = Path(evidence_dir) if evidence_dir is not None else (ws_root / "experiments" / "evidence")
    price_file = Path(pricing_path) if pricing_path is not None else (ws_root / "config" / "PRICING.json")

    snapshot = json.loads(snapshot_file.read_text(encoding="utf-8"))
    runs = snapshot.get("runs") or []

    conn = ledger.get_connection(target_db)
    try:
        ledger.init_db(conn)
        if price_file.is_file():
            ledger.seed_pricing(price_file, conn=conn)

        db_cols = [row[1] for row in conn.execute("PRAGMA table_info(runs)").fetchall()]
        inserted = 0
        hashed_evidence = 0

        for run in runs:
            rec = dict(run)
            ref = rec.get("evidence_ref")
            if ref and ev_dir.is_dir():
                ev_file = ev_dir / Path(str(ref)).name
                if ev_file.is_file():
                    try:
                        rec["evidence_ref"] = ev_file.resolve().relative_to(ws_root.resolve()).as_posix()
                    except ValueError:
                        rec["evidence_ref"] = f"experiments/evidence/{ev_file.name}"
                    rec["evidence_hash"] = hashlib.sha256(ev_file.read_bytes()).hexdigest()
                    hashed_evidence += 1

            for json_field in ("exclusion_reasons", "notes"):
                if isinstance(rec.get(json_field), (list, dict)):
                    rec[json_field] = json.dumps(rec[json_field])

            rec["is_simulation"] = 1 if rec.get("is_simulation") else 0
            rec["loop_detected"] = 1 if rec.get("loop_detected") else 0

            row_cols = [col for col in db_cols if col in rec and col != "id"]
            placeholders = ",".join("?" for _ in row_cols)
            conn.execute(
                f"INSERT INTO runs ({','.join(row_cols)}) VALUES ({placeholders})",
                [rec[col] for col in row_cols],
            )
            inserted += 1

        conn.commit()
        backfilled = ledger.backfill_cache_diagnostics_from_evidence(
            conn=conn,
            workspace_root=ws_root,
        )
        total = int(conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0])
        priced = int(conn.execute("SELECT COUNT(*) FROM runs WHERE cost_usd IS NOT NULL").fetchone()[0])
        return {
            "inserted": inserted,
            "total": total,
            "priced": priced,
            "hashed_evidence": hashed_evidence,
            "backfilled_cache_diag": backfilled,
        }
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Hydrate a SQLite usage database from dashboard/public/data.json."
    )
    parser.add_argument(
        "--from-snapshot",
        type=Path,
        default=WORKSPACE_ROOT / "dashboard" / "public" / "data.json",
        help="Path to snapshot JSON (default: dashboard/public/data.json)",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=WORKSPACE_ROOT / "data" / "usage.db",
        help="Output SQLite database path (default: data/usage.db)",
    )
    parser.add_argument(
        "--evidence-dir",
        type=Path,
        default=None,
        help="Directory holding NDJSON evidence files (default: experiments/evidence)",
    )
    parser.add_argument(
        "--pricing",
        type=Path,
        default=None,
        help="Pricing configuration JSON (default: config/PRICING.json)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing target database if present",
    )
    args = parser.parse_args()
    summary = hydrate_db_from_snapshot(
        snapshot_path=args.from_snapshot,
        db_path=args.db,
        evidence_dir=args.evidence_dir,
        pricing_path=args.pricing,
        overwrite=args.force,
    )
    print(
        f"✓ Hydrated {summary['total']} runs ({summary['priced']} priced, "
        f"{summary['hashed_evidence']} evidence hashes, "
        f"{summary['backfilled_cache_diag']} cache backfills) -> {args.db}"
    )


if __name__ == "__main__":
    main()
