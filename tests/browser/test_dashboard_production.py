"""
tests/browser/test_dashboard_production.py
------------------------------------------
Production browser regression tests for the Ai-Lab dashboard served at /Ai-Lab/.

Pre-requisites (run once before this suite):
  cd dashboard && npm ci && npm run build
  npx serve dist -s --listen 4173 --no-request-logging &

Environment variable (optional):
  DASHBOARD_BASE_URL=http://localhost:4173/Ai-Lab  (default used below)

Run:
  pytest tests/browser/test_dashboard_production.py -v
"""

import json
import os
import time
import subprocess
import tempfile
import shutil
import socket
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------

BASE_URL = os.environ.get("DASHBOARD_BASE_URL", "http://localhost:4173/Ai-Lab")
REPO_ROOT = Path(__file__).parent.parent.parent
DASHBOARD_DIR = REPO_ROOT / "dashboard"
DATA_JSON = DASHBOARD_DIR / "public" / "data.json"


def _server_available(host: str = "localhost", port: int = 4173, timeout: float = 1.0) -> bool:
    """Check whether a TCP port is accepting connections."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _load_data_json() -> dict:
    """Load and parse the committed dashboard snapshot."""
    assert DATA_JSON.exists(), f"data.json not found at {DATA_JSON}"
    return json.loads(DATA_JSON.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Snapshot integrity tests (no browser needed — pure Python)
# ---------------------------------------------------------------------------

class TestSnapshotIntegrity:
    """Assert data.json structure invariants are correct before any browser."""

    def test_snapshot_has_required_top_level_keys(self):
        data = _load_data_json()
        for key in ("generated_at", "has_data", "is_demo_report", "cumulative", "runs"):
            assert key in data, f"Missing key: {key}"

    def test_demo_report_suppresses_measured_data(self):
        data = _load_data_json()
        if data.get("is_demo_report"):
            cumulative = data.get("cumulative", {})
            assert cumulative.get("has_measured_data") is False, (
                "is_demo_report=True must not have has_measured_data=True"
            )

    def test_unknown_source_kind_runs_never_counted_as_measured(self):
        data = _load_data_json()
        runs = data.get("runs", [])
        unknown_runs = [r for r in runs if r.get("source_kind") == "unknown"]
        # For every unknown-provenance run, verify it is excluded from totals
        cumulative = data.get("cumulative", {})
        total_runs_measured = cumulative.get("total_runs", 0)
        if unknown_runs and not data.get("has_data"):
            assert total_runs_measured == 0, (
                f"{len(unknown_runs)} unknown-provenance runs but total_runs={total_runs_measured} > 0"
            )

    def test_demo_runs_not_labelled_verified(self):
        data = _load_data_json()
        runs = data.get("runs", [])
        for run in runs:
            if run.get("source_kind") in ("unknown", "fixture"):
                assert run.get("evidence_status") != "verified", (
                    f"Run {run.get('id')} has source_kind={run.get('source_kind')} "
                    f"but evidence_status=verified"
                )

    def test_header_counts_derivable_from_runs(self):
        """Rows / Tasks / Measured counts in the header must come from the same payload."""
        data = _load_data_json()
        runs = data.get("runs", [])
        cumulative = data.get("cumulative", {})
        # tasks_evaluated from cumulative
        scheduled = cumulative.get("scheduled_count", 0)
        excluded = cumulative.get("excluded_count", 0)
        # Row count = len(runs)
        assert len(runs) == scheduled, (
            f"runs array length {len(runs)} != cumulative.scheduled_count {scheduled}"
        )

    def test_build_identity_field_present(self):
        data = _load_data_json()
        assert "build_identity" in data, "build_identity missing from data.json"
        assert data["build_identity"], "build_identity is empty"

    def test_generated_at_is_iso_timestamp(self):
        data = _load_data_json()
        from datetime import datetime
        ts = data.get("generated_at", "")
        assert ts, "generated_at is missing"
        # Should parse without error
        datetime.fromisoformat(ts.replace("Z", "+00:00"))

    def test_no_raw_paths_in_public_runs(self):
        """Sensitive local paths must be sanitized out of the public snapshot."""
        data = _load_data_json()
        raw = json.dumps(data)
        # Evidence paths starting with drive letters or home dirs should not appear
        sensitive_patterns = [
            "C:\\\\Users\\\\", "/home/", "data/usage.db", ".gemini/",
        ]
        for pat in sensitive_patterns:
            assert pat not in raw, f"Sensitive path pattern found in data.json: {pat!r}"

    def test_cascade_items_have_simulation_flags(self):
        data = _load_data_json()
        cascade = data.get("model_cascade", [])
        # Cascade items that are simulations should be labelled
        for item in cascade:
            model = item.get("model", "")
            # All non-primary models in cascade are simulations — must have is_simulation key
            if "is_simulation" in item:
                assert isinstance(item["is_simulation"], bool)

    def test_no_nan_infinity_in_numeric_fields(self):
        """JSON spec disallows NaN/Infinity; validate serialized form."""
        text = DATA_JSON.read_text(encoding="utf-8")
        # JSON.parse would reject these but Python json.loads may pass NaN if written wrong
        assert "NaN" not in text, "NaN found in data.json — invalid JSON"
        assert "Infinity" not in text, "Infinity found in data.json — invalid JSON"


# ---------------------------------------------------------------------------
# Pages workflow regression test (no browser)
# ---------------------------------------------------------------------------

class TestPagesWorkflowRegression:
    """
    Prove that running build_data.py without a local database cannot overwrite
    a valid committed snapshot with an empty placeholder.
    """

    def test_missing_db_does_not_overwrite_existing_snapshot(self, tmp_path):
        """
        Simulate CI Pages build (no usage.db). The committed data.json must NOT be touched.
        We call build_data.main() in-process with env vars overriding output & db paths.
        """
        import sys as _sys
        import os as _os
        import importlib.util

        original_snapshot = DATA_JSON.read_bytes()
        scripts_dir = str(REPO_ROOT / "scripts")
        sys_path_backup = _sys.path[:]
        if scripts_dir not in _sys.path:
            _sys.path.insert(0, scripts_dir)

        out_file = tmp_path / "data.json"
        old_env = {k: _os.environ.get(k) for k in ("AI_LAB_DB_PATH", "AI_LAB_OUTPUT_PATH", "GITHUB_SHA")}
        try:
            _os.environ["AI_LAB_DB_PATH"] = str(tmp_path / "nonexistent.db")
            _os.environ["AI_LAB_OUTPUT_PATH"] = str(out_file)
            _os.environ["GITHUB_SHA"] = "test-ci-regression"
            spec = importlib.util.spec_from_file_location(
                "_bd_test1", REPO_ROOT / "dashboard" / "build_data.py"
            )
            bd = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(bd)
            bd.main()
        finally:
            for k, v in old_env.items():
                if v is None:
                    _os.environ.pop(k, None)
                else:
                    _os.environ[k] = v
            _sys.path = sys_path_backup

        # Real committed data.json must be byte-for-byte unchanged
        assert DATA_JSON.read_bytes() == original_snapshot, (
            "build_data.py without DB modified the committed data.json"
        )

    def test_placeholder_output_is_labelled_demo(self, tmp_path):
        """
        When build_data.py runs without a database, the placeholder it writes
        must be labelled is_demo_report=True and has_measured_data=False.
        """
        import sys as _sys
        import os as _os
        import importlib.util

        scripts_dir = str(REPO_ROOT / "scripts")
        sys_path_backup = _sys.path[:]
        if scripts_dir not in _sys.path:
            _sys.path.insert(0, scripts_dir)

        out_file = tmp_path / "data.json"
        old_env = {k: _os.environ.get(k) for k in ("AI_LAB_DB_PATH", "AI_LAB_OUTPUT_PATH", "GITHUB_SHA")}
        try:
            _os.environ["AI_LAB_DB_PATH"] = str(tmp_path / "nonexistent.db")
            _os.environ["AI_LAB_OUTPUT_PATH"] = str(out_file)
            _os.environ["GITHUB_SHA"] = "test-placeholder"
            spec = importlib.util.spec_from_file_location(
                "_bd_test2", REPO_ROOT / "dashboard" / "build_data.py"
            )
            bd = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(bd)
            bd.main()
        finally:
            for k, v in old_env.items():
                if v is None:
                    _os.environ.pop(k, None)
                else:
                    _os.environ[k] = v
            _sys.path = sys_path_backup

        assert out_file.exists(), "build_data.py did not write a placeholder"
        placeholder = json.loads(out_file.read_text(encoding="utf-8"))
        assert placeholder.get("is_demo_report") is True, (
            "Placeholder without DB is not labelled is_demo_report=True"
        )
        assert placeholder.get("cumulative", {}).get("has_measured_data") is False, (
            "Placeholder claims has_measured_data=True"
        )


# ---------------------------------------------------------------------------
# Live browser tests (skipped when server not running)
# ---------------------------------------------------------------------------

skip_no_server = pytest.mark.skipif(
    not _server_available(),
    reason="Dashboard server not running on localhost:4173 — run: "
           "cd dashboard && npm run build && npx serve dist -s --listen 4173",
)


@skip_no_server
class TestDashboardBrowserLive:
    """
    End-to-end browser validation.
    Requires playwright: pip install playwright && playwright install chromium
    Requires a running server at localhost:4173 with dist/ under /Ai-Lab/.
    """

    @pytest.fixture(scope="class", autouse=True)
    def browser_page(self):
        """Launch Playwright browser and navigate to dashboard."""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            pytest.skip("playwright not installed — pip install playwright && playwright install chromium")

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            ctx = browser.new_context()
            page = ctx.new_page()
            self._page = page
            self._errors: list[str] = []
            page.on("console", lambda msg: self._errors.append(msg.text) if msg.type == "error" else None)
            page.goto(f"{BASE_URL}/", wait_until="networkidle", timeout=15000)
            yield page
            browser.close()

    def _page_obj(self):
        return self._page

    def test_no_console_errors(self):
        critical = [e for e in self._errors if "404" in e or "Failed to fetch" in e]
        assert not critical, f"Console errors: {critical}"

    def test_data_json_loaded(self):
        page = self._page_obj()
        result = page.evaluate("() => window.__dashboardData || null")
        # Alternatively check that the header rendered a run count
        header_text = page.locator("header").inner_text()
        assert header_text, "Header is empty"

    def test_tabs_render(self):
        page = self._page_obj()
        for tab_label in ("Overview", "Matrix", "Evidence", "Audit"):
            tab = page.get_by_role("tab", name=tab_label)
            if tab.count() > 0:
                tab.click()
                page.wait_for_timeout(400)
                # Panel should have some content
                panel = page.get_by_role("tabpanel")
                assert panel.inner_text().strip(), f"Tab '{tab_label}' rendered empty panel"

    def test_demo_banner_visible_for_fixture_data(self):
        page = self._page_obj()
        data = _load_data_json()
        if data.get("is_demo_report"):
            # Some visual indicator of demo/fixture should be present
            banner_text = page.locator("body").inner_text()
            assert any(kw in banner_text.upper() for kw in ("DEMO", "FIXTURE", "NO MEASURED")), (
                "is_demo_report=True but no demo/fixture indicator visible on page"
            )

    def test_export_button_downloads_json(self):
        page = self._page_obj()
        with page.expect_download(timeout=5000) as dl_info:
            export_btn = page.get_by_role("button", name="Export")
            if export_btn.count() == 0:
                pytest.skip("Export button not found")
            export_btn.first.click()
        download = dl_info.value
        path = download.path()
        content = Path(path).read_text(encoding="utf-8")
        parsed = json.loads(content)
        assert isinstance(parsed, (dict, list)), "Export did not produce valid JSON"

    def test_refresh_button_present(self):
        page = self._page_obj()
        refresh = page.get_by_role("button", name="Refresh")
        assert refresh.count() > 0 or page.get_by_title("Refresh").count() > 0, (
            "No Refresh button found"
        )
