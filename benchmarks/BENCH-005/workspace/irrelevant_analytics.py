"""
irrelevant_analytics.py - Unrelated telemetry and metrics helpers.
DO NOT MODIFY THIS FILE.
"""
from typing import Dict, Any


def track_metric(name: str, value: float, tags: Dict[str, Any] = None) -> Dict[str, Any]:
    return {"metric": name, "value": value, "tags": tags or {}}
