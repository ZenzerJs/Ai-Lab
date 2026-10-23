import subprocess
import pytest
from pathlib import Path

def test_evidence_gitattributes_unset():
    """Verify that experiments/evidence/*.ndjson files are treated as binary (-text)."""
    gitattr_file = Path(".gitattributes")
    assert gitattr_file.exists(), ".gitattributes file is missing"
    content = gitattr_file.read_text(encoding="utf-8")
    assert "experiments/evidence/*.ndjson -text" in content

    sample_file = "experiments/evidence/live_EXP-001_baseline_run1_1791060060.ndjson"
    try:
        res = subprocess.run(
            ["git", "check-attr", "text", sample_file],
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
        )
        if res.returncode == 0:
            assert "unset" in res.stdout or "-text" in res.stdout or "unspecified" not in res.stdout
    except OSError:
        pass  # Subprocess invocation handles vary on Windows test runners


def test_evidence_files_no_crlf():
    """Verify that all evidence ndjson files contain pure LF line endings."""
    evidence_dir = Path("experiments/evidence")
    if not evidence_dir.exists():
        pytest.skip("No evidence directory found")
    ndjson_files = list(evidence_dir.glob("*.ndjson"))
    assert len(ndjson_files) > 0, "Expected at least one evidence file"
    for file_path in ndjson_files:
        content = file_path.read_bytes()
        assert b"\r\n" not in content, f"CRLF detected in {file_path}"
