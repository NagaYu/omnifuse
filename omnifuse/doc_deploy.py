"""[DocDeploy] Convert Git commit logs / Markdown into spec pages and
auto-deploy them to Notion / Confluence via their APIs.

When no token is configured, it runs as a dry-run, saving the payload to be
sent and a preview Markdown file locally.
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


# ---------------------------------------------------------------- input parsing

def collect_git_log(repo_path: str = ".", limit: int = 30) -> str:
    """Convert the Git commit log into Markdown."""
    try:
        result = subprocess.run(
            ["git", "-C", repo_path, "log", f"-{limit}",
             "--pretty=format:%h|%ad|%an|%s", "--date=format:%Y-%m-%d"],
            capture_output=True, text=True, timeout=30,
        )
    except FileNotFoundError:
        raise RuntimeError("The 'git' command was not found. Please install Git.")
    if result.returncode != 0:
        raise RuntimeError(
            f"Failed to read the Git log (are you running inside a Git repository?): "
            f"{result.stderr.strip()}"
        )
    lines = ["# Changelog (commit log)", ""]
    current_date = None
    for raw in result.stdout.strip().splitlines():
        parts = raw.split("|", 3)
        if len(parts) != 4:
            continue
        sha, date, author, subject = parts
        if date != current_date:
            lines.append(f"## {date}")
            current_date = date
        lines.append(f"- {subject} ({author} / `{sha}`)")
    return "\n".join(lines)


def parse_markdown(md_text: str) -> list[dict]:
    """Break Markdown into a simple block structure (heading/paragraph/bullet/code)."""
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
    if in_code and code_lines:  # also rescue an unclosed code block
        blocks.append({"type": "code", "text": "\n".join(code_lines),
                       "language": code_lang or "plain text"})
    return blocks


def _strip_inline_md(text: str) -> str:
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    return text


# ------------------------------------------------------------ convert to Notion

def to_notion_blocks(blocks: list[dict]) -> list[dict]:
    notion_blocks = []
    for b in blocks:
        text = _strip_inline_md(b["text"])[:2000]  # respect Notion's rich_text limit
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
    return notion_blocks[:100]  # Notion API's per-request limit


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
        raise RuntimeError(f"Notion API error ({resp.status_code}): {resp.text[:300]}")
    return resp.json().get("url", "(URL unknown)")


# -------------------------------------------------------- convert to Confluence

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
        raise RuntimeError(f"Confluence API error ({resp.status_code}): {resp.text[:300]}")
    data = resp.json()
    return base + data.get("_links", {}).get("webui", "")


# ---------------------------------------------------------------- entry point

def deploy(
    config: dict,
    source: str = "git",
    md_path: str | None = None,
    title: str | None = None,
) -> str:
    """Generate a spec and deploy it. Returns a result message."""
    if source == "git":
        md_text = collect_git_log()
        title = title or f"Changelog {datetime.now():%Y-%m-%d}"
    else:
        if not md_path or not Path(md_path).is_file():
            raise FileNotFoundError(f"Markdown file not found: {md_path}")
        md_text = Path(md_path).read_text(encoding="utf-8")
        first_heading = re.search(r"^#\s+(.+)", md_text, re.M)
        title = title or (first_heading.group(1).strip() if first_heading
                          else Path(md_path).stem)

    blocks = parse_markdown(md_text)
    if not blocks:
        raise ValueError("There was no content to convert.")

    dd = config["docdeploy"]
    target = dd.get("target", "dryrun")

    if target == "notion" and dd["notion"].get("token") and dd["notion"].get("parent_page_id"):
        url = deploy_to_notion(title, blocks, dd["notion"])
        return f"✅ Deployed to Notion: {url}"
    if target == "confluence" and dd["confluence"].get("api_token"):
        url = deploy_to_confluence(title, blocks, dd["confluence"])
        return f"✅ Deployed to Confluence: {url}"

    # Dry-run: save the payload and a preview
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
        "ℹ️ No API token configured, so this was saved as a dry-run.\n"
        f"   Preview: {preview}\n"
        f"   Notion payload: {payload_file}\n"
        "   Set a token in the docdeploy section of config.yaml to deploy automatically."
    )
