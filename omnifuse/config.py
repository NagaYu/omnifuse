"""Load the config file (config.yaml) and manage default values."""

import os
import copy
from pathlib import Path

import yaml

DEFAULT_CONFIG = {
    "general": {
        "output_dir": "output",
        "log_dir": "logs",
        "language": "en",
    },
    "anthropic": {
        # AI text generation (optional). If empty, falls back to the
        # ANTHROPIC_API_KEY env var, then to template mode.
        "api_key": "",
        "model": "claude-opus-4-8",
    },
    "chart": {
        "accent_color": "#2563EB",
        "mono_colors": ["#1F2937", "#6B7280", "#9CA3AF", "#D1D5DB"],
        "font_candidates": [
            "Yu Gothic", "YuGothic", "Yu Gothic UI",
            "Hiragino Sans", "Meiryo", "Noto Sans CJK JP", "IPAexGothic",
        ],
        "formats": ["png", "pdf"],
        "dpi": 200,
    },
    "docdeploy": {
        "target": "notion",  # notion | confluence | dryrun
        "notion": {"token": "", "parent_page_id": ""},
        "confluence": {
            "base_url": "",  # e.g. https://example.atlassian.net/wiki
            "email": "",
            "api_token": "",
            "space_key": "",
        },
    },
    "tone": {
        "signature": "",      # email signature (optional)
        "sender_name": "",    # sender name (optional)
        "copy_to_clipboard": True,
    },
    "multipost": {
        "x": {"access_token": ""},          # OAuth 2.0 user token (tweet.write)
        "linkedin": {"access_token": "", "author_urn": ""},  # e.g. urn:li:person:xxxx
        "qiita": {"access_token": ""},
        "queue_file": "output/post_queue.json",
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    result = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def find_config_path() -> Path | None:
    candidates = [
        Path.cwd() / "config.yaml",
        Path(__file__).resolve().parent.parent / "config.yaml",
        Path.home() / ".omnifuse" / "config.yaml",
    ]
    for path in candidates:
        if path.is_file():
            return path
    return None


def load_config(path: str | None = None) -> dict:
    config_path = Path(path) if path else find_config_path()
    user_config = {}
    if config_path and config_path.is_file():
        try:
            with open(config_path, encoding="utf-8") as f:
                user_config = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ValueError(
                f"Failed to read config.yaml (YAML syntax error): {e}"
            ) from e
    config = _deep_merge(DEFAULT_CONFIG, user_config)
    config["_config_path"] = str(config_path) if config_path else ""
    return config


def get_anthropic_key(config: dict) -> str:
    return config["anthropic"].get("api_key") or os.environ.get("ANTHROPIC_API_KEY", "")


def ensure_output_dir(config: dict) -> Path:
    out = Path(config["general"]["output_dir"])
    out.mkdir(parents=True, exist_ok=True)
    return out
