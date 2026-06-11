"""[MultiPost] 1つの元記事URL/テキストから X・LinkedIn・Qiita 用の投稿文を
一括生成し、公式API経由で即時/予約投稿する。

- 予約投稿はローカルキュー (output/post_queue.json) に保存し、
  `omnifuse post --run-queue` で送信時刻を過ぎたものを投稿する。
- トークン未設定のプラットフォームは下書き保存のみ（ドライラン）。
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


# ---------------------------------------------------------------- 入力取得

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
    """URLまたはテキスト/ファイルから {title, body, url} を取得する。"""
    if re.match(r"^https?://", source):
        resp = requests.get(source, timeout=30,
                            headers={"User-Agent": "OmniFuse/1.0"})
        if resp.status_code >= 400:
            raise RuntimeError(f"記事の取得に失敗しました ({resp.status_code}): {source}")
        parser = _TextExtractor()
        parser.feed(resp.text)
        body = " ".join(parser.chunks)
        return {"title": parser.title or source, "body": body[:4000], "url": source}
    if Path(source).is_file():
        text = Path(source).read_text(encoding="utf-8")
        title_match = re.search(r"^#\s+(.+)", text, re.M)
        if title_match:
            title = title_match.group(1).strip()
            text = text.replace(title_match.group(0), "", 1)  # 本文との重複を防ぐ
        else:
            title = Path(source).stem
        return {"title": title, "body": text.strip()[:4000], "url": ""}
    return {"title": source[:40], "body": source, "url": ""}


# -------------------------------------------------------- テンプレート生成

def _summary(body: str, limit: int) -> str:
    text = re.sub(r"\s+", " ", re.sub(r"[#>*`\[\]]", "", body)).strip()
    return text[:limit] + ("…" if len(text) > limit else "")


def _template_x(src: dict) -> str:
    url = src["url"]
    # URL分（+改行）を差し引いて140文字に収める
    reserve = (len(url) + 1) if url else 0
    head = f"【{src['title']}】"
    room = X_LIMIT - reserve - len(head) - 1
    text = head + "\n" + _summary(src["body"], max(room, 0))
    if url:
        text += "\n" + url
    # 最終ガード
    return text[:X_LIMIT] if not url else text


def _template_linkedin(src: dict) -> str:
    lines = [f"{src['title']}", "",
             _summary(src["body"], 300), "",
             "ビジネスの現場で同じ課題をお持ちの方の参考になれば幸いです。",
             "ご意見・ご感想をコメントでお聞かせください。"]
    if src["url"]:
        lines += ["", f"詳細はこちら: {src['url']}"]
    lines += ["", "#業務効率化 #DX #自動化"]
    return "\n".join(lines)


def _template_qiita(src: dict) -> dict:
    body_lines = ["## 概要", "", _summary(src["body"], 500), ""]
    if src["url"]:
        body_lines += ["## 参考", "", f"- 元記事: {src['url']}", ""]
    body_lines += ["## ポイント", "",
                   "- （ここに技術的なポイントを追記してください）", ""]
    return {
        "title": src["title"],
        "body": "\n".join(body_lines),
        "tags": [{"name": "自動化"}, {"name": "業務効率化"}],
    }


_AI_SYSTEM = (
    "あなたはSNSマーケティングと技術記事執筆のプロです。"
    "出力は投稿本文のみとし、前置きや説明は不要です。"
)


def _ai_generate(config: dict, src: dict) -> dict:
    posts = {}
    prompts = {
        "x": f"次の記事から、X（旧Twitter）向けの投稿文を日本語で1つ作成してください。"
             f"URL込みで全体を{X_LIMIT}文字以内に必ず収めてください。\n\n"
             f"タイトル: {src['title']}\nURL: {src['url']}\n本文: {src['body'][:2000]}",
        "linkedin": "次の記事から、LinkedIn向けのビジネス調の投稿文（日本語、300〜600字、"
                    f"ハッシュタグ付き）を作成してください。\n\n"
                    f"タイトル: {src['title']}\nURL: {src['url']}\n本文: {src['body'][:2000]}",
        "qiita": "次の記事から、Qiita向け技術記事の本文（Markdown、見出し付き）を"
                 "作成してください。1行目にタイトルだけを書き、2行目以降を本文として"
                 f"ください。\n\nタイトル: {src['title']}\nURL: {src['url']}\n"
                 f"本文: {src['body'][:2000]}",
    }
    for platform, prompt in prompts.items():
        text = llm.generate(config, _AI_SYSTEM, prompt)
        if text:
            posts[platform] = text
    return posts


def generate_posts(config: dict, source: str) -> dict:
    """3プラットフォーム分の投稿文を生成する。"""
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
        # AI出力（1行目タイトル）をQiita用構造に変換
        lines = posts["qiita"].splitlines()
        posts["qiita"] = {
            "title": lines[0].lstrip("# ").strip() if lines else src["title"],
            "body": "\n".join(lines[1:]).strip() or src["body"][:500],
            "tags": [{"name": "自動化"}, {"name": "業務効率化"}],
        }
    return posts


# ---------------------------------------------------------------- API投稿

def _post_x(text: str, cfg: dict) -> str:
    resp = requests.post(
        "https://api.x.com/2/tweets",
        headers={"Authorization": f"Bearer {cfg['access_token']}",
                 "Content-Type": "application/json"},
        json={"text": text}, timeout=30,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"X APIエラー ({resp.status_code}): {resp.text[:300]}")
    return f"投稿ID: {resp.json().get('data', {}).get('id', '?')}"


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
        raise RuntimeError(f"LinkedIn APIエラー ({resp.status_code}): {resp.text[:300]}")
    return f"投稿ID: {resp.headers.get('x-restli-id', '?')}"


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
        raise RuntimeError(f"Qiita APIエラー ({resp.status_code}): {resp.text[:300]}")
    return resp.json().get("url", "(URL不明)")


def _has_token(config: dict, platform: str) -> bool:
    return bool(config["multipost"][platform].get("access_token"))


def _post_now(config: dict, platform: str, content) -> str:
    cfg = config["multipost"][platform]
    if platform == "x":
        return _post_x(content, cfg)
    if platform == "linkedin":
        return _post_linkedin(content, cfg)
    return _post_qiita(content, cfg)


# ------------------------------------------------------------ キュー管理

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
            logger.warning("キューが壊れていたため初期化します: %s", path)
    return []


def _save_queue(config: dict, queue: list[dict]) -> None:
    _queue_path(config).write_text(
        json.dumps(queue, ensure_ascii=False, indent=2), encoding="utf-8")


def schedule_posts(config: dict, source: str, when: str | None = None) -> str:
    """投稿文を生成し、即時投稿または予約キューへ登録する。"""
    posts = generate_posts(config, source)

    # 下書きは常に保存（確認・手動投稿用）
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
                f"日時の形式が正しくありません（例: 2026-06-15 09:00）: {when}")

    messages = [f"📝 3プラットフォーム分の下書きを保存しました: {out_dir}/"]
    queue = _load_queue(config)
    queued_count = 0
    for platform, content in posts.items():
        if not _has_token(config, platform):
            messages.append(f"   - {platform}: トークン未設定のため下書きのみ")
            continue
        if scheduled_at:
            queue.append({
                "platform": platform,
                "content": content,
                "scheduled_at": scheduled_at.strftime("%Y-%m-%d %H:%M"),
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            })
            queued_count += 1
            messages.append(f"   - {platform}: {when} に予約しました")
        else:
            result = _post_now(config, platform, content)
            messages.append(f"   - {platform}: ✅ 投稿しました（{result}）")
    _save_queue(config, queue)
    if queued_count:
        messages.append("⏰ 予約分は `omnifuse post --run-queue` の実行時に投稿されます。")
    return "\n".join(messages)


def run_queue(config: dict) -> str:
    """送信時刻を過ぎたキュー項目を投稿する。"""
    queue = _load_queue(config)
    if not queue:
        return "キューは空です。"
    now = datetime.now()
    remaining, messages = [], []
    for item in queue:
        due = datetime.strptime(item["scheduled_at"], "%Y-%m-%d %H:%M")
        if due > now:
            remaining.append(item)
            continue
        try:
            result = _post_now(config, item["platform"], item["content"])
            messages.append(f"✅ {item['platform']}: 投稿しました（{result}）")
        except Exception as e:
            logger.error("予約投稿に失敗: %s", e)
            remaining.append(item)
            messages.append(f"❌ {item['platform']}: 失敗（再試行待ち）: {e}")
    _save_queue(config, remaining)
    messages.append(f"残りのキュー: {len(remaining)}件")
    return "\n".join(messages)
