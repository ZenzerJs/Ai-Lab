"""
evaluator.py - Protected evaluator for BENCH-003.
Verifies modular structural refactoring and strict preservation of parser behavior.
"""
from pathlib import Path
import sys


def run_checks():
    cwd = Path.cwd()

    # Check 1: Structural Refactor Requirement
    # Must have modular package 'event_parser' with models.py, validator.py, normalizer.py
    pkg_dir = cwd / "event_parser"
    if not pkg_dir.is_dir():
        print("REASON: structural_refactor_incomplete", file=sys.stderr)
        print("Required modular package directory 'event_parser/' does not exist.", file=sys.stderr)
        sys.exit(1)

    required_modules = ["models.py", "validator.py", "normalizer.py", "__init__.py"]
    for m in required_modules:
        m_path = pkg_dir / m
        if not m_path.is_file():
            print("REASON: structural_refactor_incomplete", file=sys.stderr)
            print(f"Required modular sub-file 'event_parser/{m}' is missing.", file=sys.stderr)
            sys.exit(1)
        line_count = len(m_path.read_text(encoding="utf-8").splitlines())
        if line_count > 150:
            print("REASON: structural_refactor_incomplete", file=sys.stderr)
            print(f"Module 'event_parser/{m}' exceeds maximum line budget of 150 lines ({line_count} lines).", file=sys.stderr)
            sys.exit(1)

    try:
        from event_parser import (
            EventRecord,
            ParserError,
            ValidationError,
            UnsupportedEventVersionError,
            parse_event,
            parse_event_stream,
        )
    except Exception as exc:
        print(f"REASON: import_error\nFailed to import from event_parser package: {exc}", file=sys.stderr)
        sys.exit(1)

    # Check 2: Golden outputs match
    golden_event = {
        "event_id": "EVT-GOLD-01",
        "event_type": "transaction",
        "version": "1.0",
        "timestamp": "2026-06-01T15:30:00Z",
        "payload": {"account": "A123", "amount": 100.5, "tags": ["prod", "us"]},
        "metadata": {"origin": "gateway"},
    }
    rec = parse_event(golden_event)
    if not isinstance(rec, EventRecord):
        print("REASON: golden_output_mismatch", file=sys.stderr)
        print(f"parse_event did not return EventRecord instance: {type(rec)}", file=sys.stderr)
        sys.exit(1)
    if rec.event_id != "EVT-GOLD-01" or rec.payload["amount"] != 100.5 or rec.metadata["origin"] != "gateway":
        print("REASON: golden_output_mismatch", file=sys.stderr)
        print(f"Parsed EventRecord fields do not match golden input: {rec}", file=sys.stderr)
        sys.exit(1)

    # Check 3: Exceptions and invalid inputs
    # 3a. Missing required field -> ValidationError
    try:
        parse_event({"event_id": "E1", "version": "1.0", "timestamp": "now", "payload": {}})
        print("REASON: exception_handling_regression", file=sys.stderr)
        print("Missing event_type did not raise ValidationError.", file=sys.stderr)
        sys.exit(1)
    except ValidationError:
        pass
    except Exception as exc:
        print("REASON: exception_handling_regression", file=sys.stderr)
        print(f"Expected ValidationError for missing field, got {type(exc)}: {exc}", file=sys.stderr)
        sys.exit(1)

    # 3b. Unsupported version -> UnsupportedEventVersionError
    try:
        bad_ver = dict(golden_event)
        bad_ver["version"] = "9.9"
        parse_event(bad_ver)
        print("REASON: exception_handling_regression", file=sys.stderr)
        print("Unsupported version did not raise UnsupportedEventVersionError.", file=sys.stderr)
        sys.exit(1)
    except UnsupportedEventVersionError:
        pass
    except Exception as exc:
        print("REASON: exception_handling_regression", file=sys.stderr)
        print(f"Expected UnsupportedEventVersionError, got {type(exc)}: {exc}", file=sys.stderr)
        sys.exit(1)

    # 3c. Malformed JSON string -> ParserError
    try:
        parse_event("{bad-json-syntax")
        print("REASON: exception_handling_regression", file=sys.stderr)
        print("Malformed JSON did not raise ParserError.", file=sys.stderr)
        sys.exit(1)
    except ParserError:
        pass
    except Exception as exc:
        print("REASON: exception_handling_regression", file=sys.stderr)
        print(f"Expected ParserError for malformed JSON, got {type(exc)}: {exc}", file=sys.stderr)
        sys.exit(1)

    # Check 4: Unicode preservation and input stream ordering
    unicode_stream = [
        {
            "event_id": f"EVT-U-{i}",
            "event_type": "intl_message",
            "version": "2.0",
            "timestamp": "2026-06-01T12:00:00Z",
            "payload": {"text": text, "index": i},
        }
        for i, text in enumerate(["こんにちは世界", "مرحبا بالعالم", "Привет мир", "Hello 🚀 🌍"])
    ]
    parsed_stream = parse_event_stream(unicode_stream)
    if len(parsed_stream) != 4:
        print("REASON: ordering_or_unicode_regression", file=sys.stderr)
        print(f"Stream output length mismatch: expected 4, got {len(parsed_stream)}", file=sys.stderr)
        sys.exit(1)

    for i, (orig, p) in enumerate(zip(unicode_stream, parsed_stream)):
        if p.event_id != orig["event_id"] or p.payload["text"] != orig["payload"]["text"]:
            print("REASON: ordering_or_unicode_regression", file=sys.stderr)
            print(f"Unicode text or order corrupted at index {i}: expected {orig['payload']['text']!r}, got {p.payload['text']!r}", file=sys.stderr)
            sys.exit(1)

    # Check 5: No mutable global state accumulation
    run1 = parse_event_stream(unicode_stream[:2])
    run2 = parse_event_stream(unicode_stream[2:])
    if len(run1) != 2 or len(run2) != 2:
        print("REASON: mutable_global_state_detected", file=sys.stderr)
        print("Parser stream accumulated state across consecutive invocations.", file=sys.stderr)
        sys.exit(1)

    print("ALL CHECKS PASSED")
    sys.exit(0)


if __name__ == "__main__":
    run_checks()
