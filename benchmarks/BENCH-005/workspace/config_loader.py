"""
config_loader.py - Multi-tier application configuration loader.
BROKEN STATE: Inverts precedence by allowing config files to override environment variables.
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


def _coerce_env_val(v: str) -> Any:
    v_clean = v.strip()
    if v_clean.lower() == "true":
        return True
    if v_clean.lower() == "false":
        return False
    try:
        return int(v_clean)
    except ValueError:
        pass
    try:
        return float(v_clean)
    except ValueError:
        pass
    return v_clean


def load_env_overrides() -> Dict[str, Any]:
    overrides = {}
    for k, v in os.environ.items():
        if k.startswith("APP_"):
            key_name = k[4:].lower()
            overrides[key_name] = _coerce_env_val(v)
    return overrides


def load_file_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    path = Path(config_path) if config_path else Path("config.json")
    if path.exists() and path.is_file():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def load_configuration(
    cli_args: Optional[Dict[str, Any]] = None,
    config_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Load configuration adhering to strict precedence:
    Runtime/CLI > Environment (APP_*) > Config File > Defaults.
    """
    defaults = dict(DEFAULT_CONFIG)
    file_cfg = load_file_config(config_path)
    env_cfg = load_env_overrides()
    cli = dict(cli_args or {})

    # BROKEN PRECEDENCE BUG:
    # Merges env_cfg BEFORE file_cfg, so file_cfg overrides env_cfg!
    # According to contract: Env must override file!
    config = {}
    config.update(defaults)
    config.update(env_cfg)
    config.update(file_cfg)  # BUG: overrides env_cfg!
    config.update(cli)

    return config
