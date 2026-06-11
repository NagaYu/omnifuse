"""設定ファイル (config.yaml) の読み込みと既定値の管理"""

import os
import copy
from pathlib import Path

import yaml

DEFAULT_CONFIG = {
    "general": {
        "output_dir": "output",
        "log_dir": "logs",
        "language": "ja",
    },
    "anthropic": {
        # AI文章生成（任意）。空なら環境変数 ANTHROPIC_API_KEY → テンプレート方式の順で動作
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
            "base_url": "",  # 例: https://example.atlassian.net/wiki
            "email": "",
            "api_token": "",
            "space_key": "",
        },
    },
    "tone": {
        "signature": "",      # メール署名（任意）
        "sender_name": "",    # 差出人名（任意）
        "copy_to_clipboard": True,
    },
    "multipost": {
        "x": {"access_token": ""},          # OAuth2.0 ユーザートークン (tweet.write)
        "linkedin": {"access_token": "", "author_urn": ""},  # 例: urn:li:person:xxxx
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
                f"config.yaml の読み込みに失敗しました（YAML構文エラー）: {e}"
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
