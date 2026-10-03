"""
evaluator.py - Protected evaluator for BENCH-006.
Evaluates agent test suite against genuine implementation and 5 predefined faulty variants:
1. reversed_comparison
2. removed_validation
3. missing_boundary_case
4. double_counted_cache_input
5. swallowed_error
"""
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

GENUINE_HASH = "dda7ef21d09750f257066c0682f431f5c763a6f407be8f04b85548d155dd9417"

VARIANTS = {
    "reversed_comparison": """
from typing import Any, Dict

def compute_token_bill(input_tokens: int, output_tokens: int, cache_read_tokens: int, rate_card: Dict[str, float]) -> Dict[str, Any]:
    for name, val in (("input_tokens", input_tokens), ("output_tokens", output_tokens), ("cache_read_tokens", cache_read_tokens)):
        if not isinstance(val, int) or isinstance(val, bool) or val < 0:
            raise ValueError(f"{name} must be a non-negative integer, got {val!r}")
    # FAULTY VARIANT: Reversed comparison (< instead of >)
    if cache_read_tokens < input_tokens:
        raise ValueError(f"cache_read_tokens ({cache_read_tokens}) cannot exceed input_tokens ({input_tokens})")
    required_keys = ("input_per_million", "output_per_million", "cache_per_million")
    for req in required_keys:
        if req not in rate_card:
            raise KeyError(f"Missing required rate_card key: '{req}'")
    uncached_input = input_tokens - cache_read_tokens
    cost = (uncached_input * rate_card["input_per_million"] + cache_read_tokens * rate_card["cache_per_million"] + output_tokens * rate_card["output_per_million"]) / 1_000_000.0
    return {"cost_usd": round(cost, 6), "billable_uncached_input": uncached_input, "cache_tokens": cache_read_tokens, "output_tokens": output_tokens}
""",
    "removed_validation": """
from typing import Any, Dict

def compute_token_bill(input_tokens: int, output_tokens: int, cache_read_tokens: int, rate_card: Dict[str, float]) -> Dict[str, Any]:
    # FAULTY VARIANT: Removed non-negative integer validation
    if cache_read_tokens > input_tokens:
        raise ValueError(f"cache_read_tokens ({cache_read_tokens}) cannot exceed input_tokens ({input_tokens})")
    required_keys = ("input_per_million", "output_per_million", "cache_per_million")
    for req in required_keys:
        if req not in rate_card:
            raise KeyError(f"Missing required rate_card key: '{req}'")
    uncached_input = input_tokens - cache_read_tokens
    cost = (uncached_input * rate_card["input_per_million"] + cache_read_tokens * rate_card["cache_per_million"] + output_tokens * rate_card["output_per_million"]) / 1_000_000.0
    return {"cost_usd": round(cost, 6), "billable_uncached_input": uncached_input, "cache_tokens": cache_read_tokens, "output_tokens": output_tokens}
""",
    "missing_boundary_case": """
from typing import Any, Dict

def compute_token_bill(input_tokens: int, output_tokens: int, cache_read_tokens: int, rate_card: Dict[str, float]) -> Dict[str, Any]:
    # FAULTY VARIANT: Rejects zero token transactions
    if input_tokens == 0 and output_tokens == 0 and cache_read_tokens == 0:
        raise ValueError("Zero token transactions are not supported")
    for name, val in (("input_tokens", input_tokens), ("output_tokens", output_tokens), ("cache_read_tokens", cache_read_tokens)):
        if not isinstance(val, int) or isinstance(val, bool) or val < 0:
            raise ValueError(f"{name} must be a non-negative integer, got {val!r}")
    if cache_read_tokens > input_tokens:
        raise ValueError(f"cache_read_tokens ({cache_read_tokens}) cannot exceed input_tokens ({input_tokens})")
    required_keys = ("input_per_million", "output_per_million", "cache_per_million")
    for req in required_keys:
        if req not in rate_card:
            raise KeyError(f"Missing required rate_card key: '{req}'")
    uncached_input = input_tokens - cache_read_tokens
    cost = (uncached_input * rate_card["input_per_million"] + cache_read_tokens * rate_card["cache_per_million"] + output_tokens * rate_card["output_per_million"]) / 1_000_000.0
    return {"cost_usd": round(cost, 6), "billable_uncached_input": uncached_input, "cache_tokens": cache_read_tokens, "output_tokens": output_tokens}
""",
    "double_counted_cache_input": """
from typing import Any, Dict

def compute_token_bill(input_tokens: int, output_tokens: int, cache_read_tokens: int, rate_card: Dict[str, float]) -> Dict[str, Any]:
    for name, val in (("input_tokens", input_tokens), ("output_tokens", output_tokens), ("cache_read_tokens", cache_read_tokens)):
        if not isinstance(val, int) or isinstance(val, bool) or val < 0:
            raise ValueError(f"{name} must be a non-negative integer, got {val!r}")
    if cache_read_tokens > input_tokens:
        raise ValueError(f"cache_read_tokens ({cache_read_tokens}) cannot exceed input_tokens ({input_tokens})")
    required_keys = ("input_per_million", "output_per_million", "cache_per_million")
    for req in required_keys:
        if req not in rate_card:
            raise KeyError(f"Missing required rate_card key: '{req}'")
    # FAULTY VARIANT: Double-counts cache by not subtracting cache_read_tokens from input_tokens
    cost = (input_tokens * rate_card["input_per_million"] + cache_read_tokens * rate_card["cache_per_million"] + output_tokens * rate_card["output_per_million"]) / 1_000_000.0
    return {"cost_usd": round(cost, 6), "billable_uncached_input": input_tokens, "cache_tokens": cache_read_tokens, "output_tokens": output_tokens}
""",
    "swallowed_error": """
from typing import Any, Dict

def compute_token_bill(input_tokens: int, output_tokens: int, cache_read_tokens: int, rate_card: Dict[str, float]) -> Dict[str, Any]:
    for name, val in (("input_tokens", input_tokens), ("output_tokens", output_tokens), ("cache_read_tokens", cache_read_tokens)):
        if not isinstance(val, int) or isinstance(val, bool) or val < 0:
            raise ValueError(f"{name} must be a non-negative integer, got {val!r}")
    if cache_read_tokens > input_tokens:
        raise ValueError(f"cache_read_tokens ({cache_read_tokens}) cannot exceed input_tokens ({input_tokens})")
    # FAULTY VARIANT: Swallows missing key error and returns dummy zero bill
    try:
        r_in = rate_card["input_per_million"]
        r_out = rate_card["output_per_million"]
        r_cache = rate_card["cache_per_million"]
    except KeyError:
        return {"cost_usd": 0.0, "billable_uncached_input": 0, "cache_tokens": 0, "output_tokens": 0}
    uncached_input = input_tokens - cache_read_tokens
    cost = (uncached_input * r_in + cache_read_tokens * r_cache + output_tokens * r_out) / 1_000_000.0
    return {"cost_usd": round(cost, 6), "billable_uncached_input": uncached_input, "cache_tokens": cache_read_tokens, "output_tokens": output_tokens}
""",
}


def run_checks():
    cwd = Path.cwd()
    validator_file = cwd / "accounting_validator.py"
    test_file = cwd / "tests" / "test_accounting.py"

    if not validator_file.exists():
        print("REASON: missing_implementation_file", file=sys.stderr)
        print("accounting_validator.py is missing.", file=sys.stderr)
        sys.exit(1)

    if not test_file.exists():
        print("REASON: missing_test_suite", file=sys.stderr)
        print("tests/test_accounting.py is missing.", file=sys.stderr)
        sys.exit(1)

    # Check 1: Invariant - Agent must NOT modify accounting_validator.py
    actual_hash = hashlib.sha256(validator_file.read_bytes()).hexdigest()
    if actual_hash != GENUINE_HASH:
        print("REASON: prohibited_file_modified", file=sys.stderr)
        print(f"accounting_validator.py was modified or corrupted! Expected {GENUINE_HASH}, got {actual_hash}", file=sys.stderr)
        sys.exit(1)
    orig_code = validator_file.read_text(encoding="utf-8")

    env = dict(os.environ)
    env["PYTHONPATH"] = str(cwd) + os.pathsep + env.get("PYTHONPATH", "")

    # Check 2: Submitted tests must PASS against genuine implementation
    res_genuine = subprocess.run(
        [sys.executable, "-m", "pytest", str(test_file)],
        cwd=str(cwd),
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if res_genuine.returncode != 0:
        print("REASON: tests_failed_against_genuine_implementation", file=sys.stderr)
        print("Submitted tests failed when executed against genuine accounting_validator.py!", file=sys.stderr)
        print(res_genuine.stdout + "\n" + res_genuine.stderr, file=sys.stderr)
        sys.exit(1)

    # Check 3: Submitted tests must FAIL against all 5 predefined faulty variants
    # Use disposable variant workspace to avoid in-place workspace mutation (Finding 5)
    detected = []
    missed = []
    infra_errors = []

    for var_name, var_code in VARIANTS.items():
        with tempfile.TemporaryDirectory() as tmp_variant_dir:
            tmp_dir_p = Path(tmp_variant_dir)
            tmp_tests = tmp_dir_p / "tests"
            tmp_tests.mkdir(parents=True, exist_ok=True)
            shutil.copy2(test_file, tmp_tests / "test_accounting.py")

            # Write variant implementation in disposable workspace
            (tmp_dir_p / "accounting_validator.py").write_text(var_code, encoding="utf-8")

            var_env = dict(os.environ)
            var_env["PYTHONPATH"] = str(tmp_dir_p) + os.pathsep + var_env.get("PYTHONPATH", "")

            timeout_sec = float(os.environ.get("BENCH006_MUTANT_TIMEOUT", "30.0"))
            try:
                res_var = subprocess.run(
                    [sys.executable, "-m", "pytest", str(tmp_tests / "test_accounting.py")],
                    cwd=str(tmp_dir_p),
                    env=var_env,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=timeout_sec,
                )
            except subprocess.TimeoutExpired:
                infra_errors.append((var_name, "timeout_expired"))
                continue
            except Exception as e:
                infra_errors.append((var_name, f"execution_exception: {e}"))
                continue

            # Analyze pytest outcome:
            # Code 0: all tests passed -> mutant was MISSED by the test suite
            # Code 1: tests collected and at least 1 test failed -> mutant DETECTED
            # Note: Verify actual test assertion/failure, NOT a collection or syntax error!
            stdout = res_var.stdout
            stderr = res_var.stderr
            combined = stdout + "\n" + stderr

            if res_var.returncode == 0:
                missed.append(var_name)
            elif res_var.returncode == 1:
                has_collection_err = (
                    "ERROR collecting" in combined
                    or "error during collection" in combined
                    or "=== ERRORS ===" in combined
                )
                has_test_failure = (
                    "=== FAILURES ===" in combined
                    or "FAILED " in combined
                    or bool(re.search(r"\b\d+ failed\b", stdout))
                )
                if has_collection_err or not has_test_failure:
                    infra_errors.append((var_name, "collection_error"))
                else:
                    detected.append(var_name)
            else:
                # Exit code 2 (interrupted), 3 (internal error), 4 (usage error), 5 (no tests collected)
                infra_errors.append((var_name, f"pytest_infrastructure_exit_code_{res_var.returncode}"))

    if infra_errors:
        print(f"REASON: mutation_infrastructure_error", file=sys.stderr)
        print(f"Encountered infrastructure/collection errors on variants: {infra_errors}", file=sys.stderr)
        sys.exit(1)

    if len(detected) < len(VARIANTS):
        print(f"REASON: insufficient_faulty_variant_detection ({len(detected)}/{len(VARIANTS)} detected)", file=sys.stderr)
        print(f"Detected {len(detected)} of {len(VARIANTS)} faulty variants.", file=sys.stderr)
        print(f"Missed variants: {missed}", file=sys.stderr)
        sys.exit(1)

    print(f"ALL CHECKS PASSED: {len(detected)}/{len(VARIANTS)} faulty variants successfully detected.")
    sys.exit(0)


if __name__ == "__main__":
    run_checks()
