"""
config_loader.py - Flawed solution for BENCH-005.
Follows stale legacy notes where config file overrides environment variables.
"""
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

DEFAULT_CONFIG: Dict[str, Any] = {
    "host": "127.0.0.1",
    "port": 8000,
    "debug": False,
    "timeout": 30.0,
    "log_level": "INFO",
}


def load_configuration(
    cli_args: Optional[Dict[str, Any]] = None,
    config_path: Optional[str] = None,
) -> Dict[str, Any]:
    # Flawed: Followed legacy notes 2023 where file overrides env!
    config = dict(DEFAULT_CONFIG)
    for k, v in os.environ.items():
        if k.startswith("APP_"):
            config[k[4:].lower()] = v

    path = Path(config_path) if config_path else Path("config.json")
    if path.exists():
        try:
            config.update(json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            pass

    if cli_args:
        config.update(cli_args)
    return config
