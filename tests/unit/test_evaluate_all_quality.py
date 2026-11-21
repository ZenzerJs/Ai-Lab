import pytest

from scripts.evaluate_all_quality import _load_db_verdicts
from scripts.ledger import record_run


@pytest.mark.parametrize("older_icm", [False, True])
def test_load_db_verdicts_uses_latest_lite_verification(tmp_path, older_icm):
    db = tmp_path / "verdicts.db"
    runs = [("baseline", "failed")]
    if older_icm:
        runs.append(("icm", "failed"))
    runs.append(("icm_lite", "passed"))
    for index, (arm, status) in enumerate(runs):
        record_run(
            task_id="EXP-001",
            arm=arm,
            model="gemini-2.5-pro",
            run_index=1,
            timestamp=f"2026-09-09T17:0{index}:00+00:00",
            input_tokens=1,
            output_tokens=1,
            source_kind="live",
            verification_status=status,
            db_path=db,
        )

    assert _load_db_verdicts(db) == {("EXP-001", "baseline"): False, ("EXP-001", "governed"): True}
