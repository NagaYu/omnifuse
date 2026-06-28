"""Text generation via the Claude API (optional feature).

If an API key is configured, generate high-quality text with AI; otherwise
return None so the caller falls back to template mode.
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
    """Generate text with the Claude API. Returns None if unavailable or on failure."""
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
    except Exception as e:  # fall back to templates on API error
        logger.warning("Claude API call failed; continuing in template mode: %s", e)
        return None
