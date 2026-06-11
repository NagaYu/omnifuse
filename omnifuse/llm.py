"""Claude APIによる文章生成（任意機能）。

APIキーが設定されていれば高品質なAI生成、なければ None を返して
呼び出し側がテンプレート方式へフォールバックする。
"""

import logging

from .config import get_anthropic_key

logger = logging.getLogger("omnifuse")


def is_available(config: dict) -> bool:
    if not get_anthropic_key(config):
        return False
    try:
        import anthropic  # noqa: F401
        return True
    except ImportError:
        return False


def generate(config: dict, system: str, prompt: str, max_tokens: int = 4000) -> str | None:
    """Claude APIでテキストを生成する。利用不可・失敗時は None。"""
    if not is_available(config):
        return None
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=get_anthropic_key(config))
        response = client.messages.create(
            model=config["anthropic"].get("model", "claude-opus-4-8"),
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(b.text for b in response.content if b.type == "text").strip()
    except Exception as e:  # APIエラー時はテンプレートへフォールバック
        logger.warning("Claude API呼び出しに失敗したためテンプレート方式で続行します: %s", e)
        return None
