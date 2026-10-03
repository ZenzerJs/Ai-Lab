# Test Suite Architecture & Verification Guide

This repository employs a two-tier testing architecture to ensure high-velocity, reliable CI/CD while accommodating browser-based interactive evaluations.

---

## Tier 1: Hermetic Unit & Integration Tests

**Paths**: `tests/unit/`, `tests/integration/`  
**Execution Command**:
```bash
python scripts/filter_output.py uv run --isolated --python 3.12 --with pytest pytest
```

### Characteristics:
- **Zero External Network**: Network sockets in the current Python process are intercepted (`scripts/runner.py:block_network`). Offline execution tests replay fixtures without paid API calls. (Note: evaluator subprocesses execute outside this in-process monkeypatch).
- **Isolated SQLite Storage**: All tests utilize `tmp_path` fixtures for temporary SQLite ledgers. The baseline production ledger (`data/usage.db`) is strictly protected and never modified.
- **Fast & Deterministic**: Runs in under 5 seconds on Python 3.12 without external services or container prerequisites.

### Key Test Modules:
- `tests/unit/test_accounting.py`: Pricing calculations, token tier aggregation, and cost estimation.
- `tests/unit/test_runner.py`: Disposable workspace lifecycle, manifest verification, and isolation enforcement.
- `tests/unit/test_provenance.py`: Evidence validation, artifact SHA-256 hash checks, and classification rules.
- `tests/unit/test_telemetry.py`: NDJSON parsing, partial turn detection, and usage extraction.
- `tests/unit/test_migration.py`: Schema migrations and backward compatibility.
- `tests/integration/test_reporting_export.py`: Public JSON export sanitization and data consistency.
- `tests/unit/test_hardening_phase1_2.py`: Dedicated Phase 1/2 hardening regression assertions (Findings 1–7).
- `tests/unit/test_hardening_phase3_4.py`: Dedicated Phase 3/4 hardening regression assertions (Findings 1–8).
- `tests/unit/test_benchmarks.py`: First-party benchmark pack integrity, reference solutions, and tampered patches (BEN-01 to BEN-04). Validates organizational filesystem separation.
- `tests/unit/test_campaign.py`: Campaign matrix planning, repeat comparisons, cache stratification, and reporting (REP-01 to REP-10).

---

## Tier 2: End-to-End Playwright Browser Suites

**Paths**: `tests/exp007/`, `tests/exp008/`  
**Prerequisites**: Requires `pytest-playwright` and installed browser binaries:
```bash
uv run --with playwright playwright install chromium
```

### Execution Commands:

#### EXP-007 (Topology Canvas & Chaos Resilience):
Requires a local web server serving the experiment sandbox on port 8000:
```bash
# Terminal 1: Start local server
python -m http.server 8000 --directory sandbox/exp007_vanilla

# Terminal 2: Run Playwright suite
uv run --with pytest --with pytest-playwright pytest tests/exp007
```

#### EXP-008 (Interview Flow Sandbox Evaluation):
Evaluates local file URIs directly in headless Chromium:
```bash
uv run --with pytest --with pytest-playwright pytest tests/exp008
```

---

## Database Protection Invariant

The reference database `data/usage.db` contains empirical benchmark run data and must remain pristine (verified SHA-256: `a17d786221afb00b22ed22ab27664e38cebdf6c2ffe66e1ae7b3809298aa8213`).
Tests must **never** connect to `DEFAULT_DB_PATH` or alter `data/usage.db`.
