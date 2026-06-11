"""[DocDeploy] Gitコミットログ / Markdown を仕様書ページに変換し、
Notion / Confluence へAPI経由で自動デプロイする。

トークン未設定時はドライランとして、送信予定のペイロードと
プレビュー用Markdownをローカルに保存する。
"""

import json
import logging
import re
import subprocess
from datetime import datetime
from pathlib import Path

import requests

from .config import ensure_output_dir

logger = logging.getLogger("omnifuse")

NOTION_VERSION = "2022-06-28"


# ---------------------------------------------------------------- 入力の解析

def collect_git_log(repo_path: str = ".", limit: int = 30) -> str:
    """GitコミットログをMarkdownに変換する。"""
    try:
        result = subprocess.run(
            ["git", "-C", repo_path, "log", f"-{limit}",
             "--pretty=format:%h|%ad|%an|%s", "--date=format:%Y-%m-%d"],
            capture_output=True, text=True, timeout=30,
        )
    except FileNotFoundError:
        raise RuntimeError("git コマンドが見つかりません。Gitをインストールしてください。")
    if result.returncode != 0:
        raise RuntimeError(
            f"Gitログの取得に失敗しました（Gitリポジトリ内で実行していますか？）: "
            f"{result.stderr.strip()}"
        )
    lines = ["# 更新履歴（コミットログ）", ""]
    current_date = None
    for raw in result.stdout.strip().splitlines():
        parts = raw.split("|", 3)
        if len(parts) != 4:
            continue
        sha, date, author, subject = parts
        if date != current_date:
            lines.append(f"## {date}")
            current_date = date
        lines.append(f"- {subject}（{author} / `{sha}`）")
    return "\n".join(lines)


def parse_markdown(md_text: str) -> list[dict]:
    """Markdownを簡易ブロック構造（heading/paragraph/bullet/code）へ分解する。"""
    blocks = []
    in_code = False
    code_lines: list[str] = []
    code_lang = ""
    for line in md_text.splitlines():
        if line.strip().startswith("```"):
            if in_code:
                blocks.append({"type": "code", "text": "\n".join(code_lines),
                               "language": code_lang or "plain text"})
                code_lines, in_code = [], False
            else:
                in_code = True
                code_lang = line.strip().lstrip("`").strip()
            continue
        if in_code:
            code_lines.append(line)
            continue
        heading = re.match(r"^(#{1,3})\s+(.*)", line)
        if heading:
            blocks.append({"type": f"heading_{len(heading.group(1))}",
                           "text": heading.group(2).strip()})
        elif re.match(r"^\s*[-*]\s+", line):
            blocks.append({"type": "bullet",
                           "text": re.sub(r"^\s*[-*]\s+", "", line).strip()})
        elif line.strip():
            blocks.append({"type": "paragraph", "text": line.strip()})
    if in_code and code_lines:  # 閉じ忘れのコードブロックも救済
        blocks.append({"type": "code", "text": "\n".join(code_lines),
                       "language": code_lang or "plain text"})
    return blocks


def _strip_inline_md(text: str) -> str:
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    return text


# ------------------------------------------------------------ Notion へ変換

def to_notion_blocks(blocks: list[dict]) -> list[dict]:
    notion_blocks = []
    for b in blocks:
        text = _strip_inline_md(b["text"])[:2000]  # Notionのrich_text上限対策
        rich = [{"type": "text", "text": {"content": text}}]
        if b["type"].startswith("heading_"):
            notion_blocks.append({
                "object": "block", "type": b["type"],
                b["type"]: {"rich_text": rich},
            })
        elif b["type"] == "bullet":
            notion_blocks.append({
                "object": "block", "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": rich},
            })
        elif b["type"] == "code":
            notion_blocks.append({
                "object": "block", "type": "code",
                "code": {"rich_text": rich, "language": b.get("language", "plain text")},
            })
        else:
            notion_blocks.append({
                "object": "block", "type": "paragraph",
                "paragraph": {"rich_text": rich},
            })
    return notion_blocks[:100]  # Notion APIの1リクエスト上限


def deploy_to_notion(title: str, blocks: list[dict], cfg: dict) -> str:
    payload = {
        "parent": {"page_id": cfg["parent_page_id"]},
        "properties": {"title": {"title": [{"text": {"content": title}}]}},
        "children": to_notion_blocks(blocks),
    }
    resp = requests.post(
        "https://api.notion.com/v1/pages",
        headers={
            "Authorization": f"Bearer {cfg['token']}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        },
        json=payload, timeout=30,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"Notion APIエラー ({resp.status_code}): {resp.text[:300]}")
    return resp.json().get("url", "(URL不明)")


# -------------------------------------------------------- Confluence へ変換

def to_confluence_storage(blocks: list[dict]) -> str:
    import html
    parts, open_ul = [], False
    for b in blocks:
        text = html.escape(_strip_inline_md(b["text"]))
        if b["type"] == "bullet":
            if not open_ul:
                parts.append("<ul>")
                open_ul = True
            parts.append(f"<li>{text}</li>")
            continue
        if open_ul:
            parts.append("</ul>")
            open_ul = False
        if b["type"].startswith("heading_"):
            level = b["type"][-1]
            parts.append(f"<h{level}>{text}</h{level}>")
        elif b["type"] == "code":
            parts.append(
                '<ac:structured-macro ac:name="code">'
                f"<ac:plain-text-body><![CDATA[{b['text']}]]></ac:plain-text-body>"
                "</ac:structured-macro>"
            )
        else:
            parts.append(f"<p>{text}</p>")
    if open_ul:
        parts.append("</ul>")
    return "".join(parts)


def deploy_to_confluence(title: str, blocks: list[dict], cfg: dict) -> str:
    payload = {
        "type": "page",
        "title": title,
        "space": {"key": cfg["space_key"]},
        "body": {"storage": {"value": to_confluence_storage(blocks),
                             "representation": "storage"}},
    }
    base = cfg["base_url"].rstrip("/")
    resp = requests.post(
        f"{base}/rest/api/content",
        auth=(cfg["email"], cfg["api_token"]),
        headers={"Content-Type": "application/json"},
        json=payload, timeout=30,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"Confluence APIエラー ({resp.status_code}): {resp.text[:300]}")
    data = resp.json()
    return base + data.get("_links", {}).get("webui", "")


# ---------------------------------------------------------------- エントリ

def deploy(
    config: dict,
    source: str = "git",
    md_path: str | None = None,
    title: str | None = None,
) -> str:
    """仕様書を生成してデプロイする。戻り値は結果メッセージ。"""
    if source == "git":
        md_text = collect_git_log()
        title = title or f"更新履歴 {datetime.now():%Y-%m-%d}"
    else:
        if not md_path or not Path(md_path).is_file():
            raise FileNotFoundError(f"Markdownファイルが見つかりません: {md_path}")
        md_text = Path(md_path).read_text(encoding="utf-8")
        first_heading = re.search(r"^#\s+(.+)", md_text, re.M)
        title = title or (first_heading.group(1).strip() if first_heading
                          else Path(md_path).stem)

    blocks = parse_markdown(md_text)
    if not blocks:
        raise ValueError("変換できる内容がありませんでした。")

    dd = config["docdeploy"]
    target = dd.get("target", "dryrun")

    if target == "notion" and dd["notion"].get("token") and dd["notion"].get("parent_page_id"):
        url = deploy_to_notion(title, blocks, dd["notion"])
        return f"✅ Notionへデプロイしました: {url}"
    if target == "confluence" and dd["confluence"].get("api_token"):
        url = deploy_to_confluence(title, blocks, dd["confluence"])
        return f"✅ Confluenceへデプロイしました: {url}"

    # ドライラン: ペイロードとプレビューを保存
    out_dir = ensure_output_dir(config) / "docs"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    preview = out_dir / f"doc_{stamp}.md"
    preview.write_text(f"# {title}\n\n{md_text}", encoding="utf-8")
    payload_file = out_dir / f"notion_payload_{stamp}.json"
    payload_file.write_text(
        json.dumps(to_notion_blocks(blocks), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return (
        "ℹ️ APIトークン未設定のためドライランで保存しました。\n"
        f"   プレビュー: {preview}\n"
        f"   Notion用ペイロード: {payload_file}\n"
        "   config.yaml の docdeploy セクションにトークンを設定すると自動デプロイされます。"
    )
