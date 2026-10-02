"""
test_visible.py - Accessible tests for BENCH-005.
"""
from config_loader import load_configuration, DEFAULT_CONFIG


def test_defaults_load():
    cfg = load_configuration()
    assert cfg["host"] == DEFAULT_CONFIG["host"]
    assert cfg["port"] == DEFAULT_CONFIG["port"]
