"""
test_visible.py - Accessible tests for BENCH-003.
"""
from event_parser import parse_event


def test_parse_valid_event():
    raw = {
        "event_id": "EVT-100",
        "event_type": "ping",
        "version": "1.0",
        "timestamp": "2026-06-01T12:00:00Z",
        "payload": {"status": "ok"},
    }
    rec = parse_event(raw)
    assert rec.event_id == "EVT-100"
    assert rec.event_type == "ping"
    assert rec.payload["status"] == "ok"
