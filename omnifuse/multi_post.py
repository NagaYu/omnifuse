"""[MultiPost] Generate posts for X, LinkedIn, and Qiita from a single source
article (URL/text) and publish them immediately or on a schedule via official APIs.

- Scheduled posts are stored in a local queue (output/post_queue.json) and sent
  by `omnifuse post --run-queue` once their scheduled time has passed.
- Platforms without a configured token only get a saved draft (dry-run).
"""

import json
import logging
import re
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path

import requests

from . import llm
from .config import ensure_output_dir

logger = logging.getLogger("omnifuse")

PLATFORMS = ["x", "linkedin", "qiita"]
X_LIMIT = 140


# ---------------------------------------------------------------- input

class _TextExtractor(HTMLParser):
    SKIP = {"script", "style", "nav", "footer", "header"}

    def __init__(self):
        super().__init__()
        self._skip_depth = 0
        self.title = ""
        self._in_title = False
        self.chunks: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip_depth += 1
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip_depth:
            self._skip_depth -= 1
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data.strip()
        elif not self._skip_depth and data.strip():
            self.chunks.append(data.strip())


def fetch_source(source: str) -> dict:
    """Return {title, body, url} from a URL, text, or file."""
    if re.match(r"^https?://", source):
        resp = requests.get(source, timeout=30,
                            headers={"User-Agent": "OmniFuse/1.0"})
        if resp.status_code >= 400:
            raise RuntimeError(f"Failed to fetch the article ({resp.status_code}): {source}")
        parser = _TextExtractor()
        parser.feed(resp.text)
        body = " ".join(parser.chunks)
        return {"title": parser.title or source, "body": body[:4000], "url": source}
    if Path(source).is_file():
        text = Path(source).read_text(encoding="utf-8")
        title_match = re.search(r"^#\s+(.+)", text, re.M)
        if title_match:
            title = title_match.group(1).strip()
            text = text.replace(title_match.group(0), "", 1)  # avoid duplicating it in the body
        else:
            title = Path(source).stem
        return {"title": title, "body": text.strip()[:4000], "url": ""}
    return {"title": source[:40], "body": source, "url": ""}


# -------------------------------------------------------- template generation

def _summary(body: str, limit: int) -> str:
    text = re.sub(r"\s+", " ", re.sub(r"[#>*`\[\]]", "", body)).strip()
    return text[:limit] + ("…" if len(text) > limit else "")


def _template_x(src: dict) -> str:
    url = src["url"]
    # Reserve room for the URL (+ newline) so the whole thing fits in 140 chars
    reserve = (len(url) + 1) if url else 0
    head = f"[{src['title']}]"
    room = X_LIMIT - reserve - len(head) - 1
    text = head + "\n" + _summary(src["body"], max(room, 0))
    if url:
        text += "\n" + url
    # Final guard
    return text[:X_LIMIT] if not url else text


def _template_linkedin(src: dict) -> str:
    lines = [f"{src['title']}", "",
             _summary(src["body"], 300), "",
             "I hope this is helpful to anyone facing the same challenges in their work.",
             "Share your thoughts and feedback in the comments."]
    if src["url"]:
        lines += ["", f"Read more: {src['url']}"]
    lines += ["", "#productivity #DX #automation"]
    return "\n".join(lines)


def _template_qiita(src: dict) -> dict:
    body_lines = ["## Overview", "", _summary(src["body"], 500), ""]
    if src["url"]:
        body_lines += ["## Reference", "", f"- Source article: {src['url']}", ""]
    body_lines += ["## Key Points", "",
                   "- (add your technical key points here)", ""]
    return {
        "title": src["title"],
        "body": "\n".join(body_lines),
        "tags": [{"name": "automation"}, {"name": "productivity"}],
    }


_AI_SYSTEM = (
    "You are a professional social-media marketer and technical writer. "
    "Output only the post body, with no preamble or explanation."
)


def _ai_generate(config: dict, src: dict) -> dict:
    posts = {}
    prompts = {
        "x": f"From the article below, write one post for X (formerly Twitter). "
             f"The entire post, including the URL, must fit within {X_LIMIT} characters.\n\n"
             f"Title: {src['title']}\nURL: {src['url']}\nBody: {src['body'][:2000]}",
        "linkedin": "From the article below, write a business-toned LinkedIn post "
                    "(300-600 characters, with hashtags).\n\n"
                    f"Title: {src['title']}\nURL: {src['url']}\nBody: {src['body'][:2000]}",
        "qiita": "From the article below, write the body of a technical article for Qiita "
                 "(Markdown, with headings). Put only the title on the first line and the "
                 f"body from the second line onward.\n\nTitle: {src['title']}\n"
                 f"URL: {src['url']}\nBody: {src['body'][:2000]}",
    }
    for platform, prompt in prompts.items():
        text = llm.generate(config, _AI_SYSTEM, prompt)
        if text:
            posts[platform] = text
    return posts


def generate_posts(config: dict, source: str) -> dict:
    """Generate posts for all three platforms."""
    src = fetch_source(source)
    posts = _ai_generate(config, src) if llm.is_available(config) else {}

    if "x" not in posts:
        posts["x"] = _template_x(src)
    if "linkedin" not in posts:
        posts["linkedin"] = _template_linkedin(src)
    if "qiita" not in posts:
        qiita = _template_qiita(src)
        posts["qiita"] = qiita
    else:
        # Convert the AI output (title on line 1) into the Qiita structure
        lines = posts["qiita"].splitlines()
        posts["qiita"] = {
            "title": lines[0].lstrip("# ").strip() if lines else src["title"],
            "body": "\n".join(lines[1:]).strip() or src["body"][:500],
            "tags": [{"name": "automation"}, {"name": "productivity"}],
        }
    return posts


# ---------------------------------------------------------------- API posting

def _post_x(text: str, cfg: dict) -> str:
    resp = requests.post(
        "https://api.x.com/2/tweets",
        headers={"Authorization": f"Bearer {cfg['access_token']}",
                 "Content-Type": "application/json"},
        json={"text": text}, timeout=30,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"X API error ({resp.status_code}): {resp.text[:300]}")
    return f"post ID: {resp.json().get('data', {}).get('id', '?')}"


def _post_linkedin(text: str, cfg: dict) -> str:
    payload = {
        "author": cfg["author_urn"],
        "lifecycleState": "PUBLISHED",
        "specificContent": {"com.linkedin.ugc.ShareContent": {
            "shareCommentary": {"text": text},
            "shareMediaCategory": "NONE",
        }},
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }
    resp = requests.post(
        "https://api.linkedin.com/v2/ugcPosts",
        headers={"Authorization": f"Bearer {cfg['access_token']}",
                 "X-Restli-Protocol-Version": "2.0.0",
                 "Content-Type": "application/json"},
        json=payload, timeout=30,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"LinkedIn API error ({resp.status_code}): {resp.text[:300]}")
    return f"post ID: {resp.headers.get('x-restli-id', '?')}"


def _post_qiita(item: dict, cfg: dict) -> str:
    resp = requests.post(
        "https://qiita.com/api/v2/items",
        headers={"Authorization": f"Bearer {cfg['access_token']}",
                 "Content-Type": "application/json"},
        json={"title": item["title"], "body": item["body"],
              "tags": item["tags"], "private": False},
        timeout=30,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"Qiita API error ({resp.status_code}): {resp.text[:300]}")
    return resp.json().get("url", "(URL unknown)")


def _has_token(config: dict, platform: str) -> bool:
    return bool(config["multipost"][platform].get("access_token"))


def _post_now(config: dict, platform: str, content) -> str:
    cfg = config["multipost"][platform]
    if platform == "x":
        return _post_x(content, cfg)
    if platform == "linkedin":
        return _post_linkedin(content, cfg)
    return _post_qiita(content, cfg)


# ------------------------------------------------------------ queue management

def _queue_path(config: dict) -> Path:
    path = Path(config["multipost"]["queue_file"])
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _load_queue(config: dict) -> list[dict]:
    path = _queue_path(config)
    if path.is_file():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            logger.warning("Queue was corrupted; resetting it: %s", path)
    return []


def _save_queue(config: dict, queue: list[dict]) -> None:
    _queue_path(config).write_text(
        json.dumps(queue, ensure_ascii=False, indent=2), encoding="utf-8")


def schedule_posts(config: dict, source: str, when: str | None = None) -> str:
    """Generate posts and either publish immediately or add them to the queue."""
    posts = generate_posts(config, source)

    # Always save drafts (for review / manual posting)
    out_dir = ensure_output_dir(config) / "posts"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    for platform, content in posts.items():
        text = (f"# {content['title']}\n\n{content['body']}"
                if isinstance(content, dict) else content)
        (out_dir / f"{platform}_{stamp}.md").write_text(text, encoding="utf-8")

    scheduled_at = None
    if when:
        try:
            scheduled_at = datetime.strptime(when, "%Y-%m-%d %H:%M")
        except ValueError:
            raise ValueError(
                f"Invalid date/time format (e.g. 2026-06-15 09:00): {when}")

    messages = [f"📝 Saved drafts for all 3 platforms: {out_dir}/"]
    queue = _load_queue(config)
    queued_count = 0
    for platform, content in posts.items():
        if not _has_token(config, platform):
            messages.append(f"   - {platform}: draft only (no token configured)")
            continue
        if scheduled_at:
            queue.append({
                "platform": platform,
                "content": content,
                "scheduled_at": scheduled_at.strftime("%Y-%m-%d %H:%M"),
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            })
            queued_count += 1
            messages.append(f"   - {platform}: scheduled for {when}")
        else:
            result = _post_now(config, platform, content)
            messages.append(f"   - {platform}: ✅ posted ({result})")
    _save_queue(config, queue)
    if queued_count:
        messages.append("⏰ Scheduled posts will be sent when you run `omnifuse post --run-queue`.")
    return "\n".join(messages)


def run_queue(config: dict) -> str:
    """Publish queued items whose scheduled time has passed."""
    queue = _load_queue(config)
    if not queue:
        return "The queue is empty."
    now = datetime.now()
    remaining, messages = [], []
    for item in queue:
        due = datetime.strptime(item["scheduled_at"], "%Y-%m-%d %H:%M")
        if due > now:
            remaining.append(item)
            continue
        try:
            result = _post_now(config, item["platform"], item["content"])
            messages.append(f"✅ {item['platform']}: posted ({result})")
        except Exception as e:
            logger.error("Scheduled post failed: %s", e)
            remaining.append(item)
            messages.append(f"❌ {item['platform']}: failed (will retry): {e}")
    _save_queue(config, remaining)
    messages.append(f"Items remaining in queue: {len(remaining)}")
    return "\n".join(messages)
