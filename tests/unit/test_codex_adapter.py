"""Unit coverage for Codex CLI invocation and usage event normalization."""

import json
from pathlib import Path

from scripts import ledger, runner


def test_codex_command_uses_exec_json_and_workspace_write():
    command = runner._build_cli_command(
        "codex", "fix the issue", Path.cwd(), "gpt-6.2-astra", 90
    )

    assert command[:2] == ["codex", "exec"]
    assert "--json" in command
    assert "--sandbox" in command
    assert "workspace-write" in command
    assert "--model" in command
    assert command[-1] == "fix the issue"
    assert str(Path.cwd()) in command


def test_codex_turn_usage_maps_to_ledger_cumulative_schema():
    lines = [
        json.dumps({"type": "turn.started", "turn_id": "t1"}),
        json.dumps({"type": "turn.completed", "usage": {
            "input_tokens": 1200,
            "cached_input_tokens": 800,
            "output_tokens": 240,
        }}),
    ]

    normalized = runner._normalize_codex_events(lines)
    parsed = ledger.validate_and_parse_telemetry(normalized, adapter_name="subset")

    assert parsed["has_usage"] is True
    assert parsed["usage"]["input_tokens"] == 1200
    assert parsed["usage"]["cache_read_tokens"] == 800
    assert parsed["usage"]["output_tokens"] == 240
    assert parsed["num_turns"] == 1


def test_codex_multiple_turns_use_final_cumulative_usage_without_double_counting():
    lines = [
        json.dumps({"type": "turn.started"}),
        json.dumps({"type": "turn.completed", "usage": {
            "input_tokens": 10, "cached_input_tokens": 2, "output_tokens": 3,
        }}),
        json.dumps({"type": "turn.started"}),
        json.dumps({"type": "turn.completed", "usage": {
            "input_tokens": 35, "cached_input_tokens": 8, "output_tokens": 9,
        }}),
    ]

    parsed = ledger.validate_and_parse_telemetry(
        runner._normalize_codex_events(lines), adapter_name="subset"
    )

    assert parsed["num_turns"] == 2
    assert parsed["usage"]["input_tokens"] == 35
    assert parsed["usage"]["cache_read_tokens"] == 8
    assert parsed["usage"]["output_tokens"] == 9


def test_codex_events_without_usage_do_not_invent_zero_counts():
    normalized = runner._normalize_codex_events([
        json.dumps({"type": "turn.started"}),
        json.dumps({"type": "turn.completed"}),
    ])

    parsed = ledger.validate_and_parse_telemetry(normalized)

    assert parsed["has_usage"] is False
    assert parsed["usage"]["input_tokens"] is None
    assert parsed["usage"]["output_tokens"] is None


def test_codex_malformed_and_non_event_lines_are_ignored():
    normalized = runner._normalize_codex_events([
        "not json",
        json.dumps(["not", "an", "event"]),
        json.dumps({"type": "item.completed", "item": {"type": "agent_message"}}),
    ])

    assert normalized == []


def test_codex_windows_shim_names_recognized():
    for shim in (
        "codex.cmd",
        r"C:\Users\dev\AppData\Roaming\npm\codex.cmd",
        "codex.ps1",
        "codex.exe",
    ):
        command = runner._build_cli_command(
            shim, "fix the issue", Path.cwd(), "gpt-6.2-astra", 90
        )
        assert command[0] == shim
        assert command[1:3] == ["exec", "--json"]
        assert runner._is_codex_cli(shim) is True

    assert runner._is_codex_cli("agy") is False


def test_codex_phase1_plan_extraction_reads_agent_message_items():
    lines = [
        json.dumps({"type": "turn.started"}),
        json.dumps({
            "type": "item.completed",
            "item": {"type": "command_execution", "command": "pytest -q"},
        }),
        json.dumps({
            "type": "item.completed",
            "item": {
                "type": "agent_message",
                "text": "1. Edit a.py\n2. Run pytest tests/test_visible.py",
            },
        }),
        json.dumps({
            "type": "turn.completed",
            "usage": {"input_tokens": 500, "cached_input_tokens": 100, "output_tokens": 50},
        }),
    ]

    plan_text, truncated = runner._extract_phase1_plan_text(lines)

    assert truncated is False
    assert "Edit a.py" in plan_text
    assert "pytest -q" not in plan_text
