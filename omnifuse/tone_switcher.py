"""[ToneSwitcher] 1つのMarkdown完了報告から、送信先文化に合わせた
3種類の文章（Slack / Teams / クライアント向けメール）を同時生成する。

Claude APIキーが設定されていればAIが文面を生成し、
なければ組み込みテンプレートで変換する。
"""

import logging
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from . import llm
from .config import ensure_output_dir

logger = logging.getLogger("omnifuse")

TONES = ["slack", "teams", "email"]
TONE_LABELS = {"slack": "Slack（フランク）", "teams": "Teams（業務連絡）",
               "email": "メール（クライアント向け）"}


# ------------------------------------------------------------ クリップボード

def copy_to_clipboard(text: str) -> bool:
    try:
        if sys.platform == "darwin":
            subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)
        elif sys.platform.startswith("win"):
            subprocess.run(["clip"], input=text.encode("cp932", errors="replace"),
                           check=True)
        else:
            subprocess.run(["xclip", "-selection", "clipboard"],
                           input=text.encode("utf-8"), check=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        logger.warning("クリップボードへのコピーに失敗しました（下書きファイルは保存済み）")
        return False


# ---------------------------------------------------------------- 解析処理

def _parse_report(md_text: str) -> dict:
    """Markdown報告からタイトル・要点・本文を抽出する。"""
    title_match = re.search(r"^#\s+(.+)", md_text, re.M)
    title = title_match.group(1).strip() if title_match else "完了報告"
    bullets = [re.sub(r"^\s*[-*]\s+", "", l).strip()
               for l in md_text.splitlines() if re.match(r"^\s*[-*]\s+", l)]
    paragraphs = [l.strip() for l in md_text.splitlines()
                  if l.strip() and not l.startswith("#")
                  and not re.match(r"^\s*[-*]\s+", l)]
    return {"title": title, "bullets": bullets, "paragraphs": paragraphs}


# -------------------------------------------------------- テンプレート生成

def _template_slack(report: dict) -> str:
    lines = [f":white_check_mark: *{report['title']}* 完了しました！:tada:", ""]
    if report["bullets"]:
        lines.append("*やったこと*")
        lines += [f"• {b}" for b in report["bullets"][:8]]
    if report["paragraphs"]:
        lines += ["", report["paragraphs"][0]]
    lines += ["", "なにか気になる点あれば気軽に声かけてください〜 :pray:"]
    return "\n".join(lines)


def _template_teams(report: dict) -> str:
    today = datetime.now().strftime("%Y/%m/%d")
    lines = ["【業務連絡】作業完了のご報告", "",
             f"件名: {report['title']}", f"完了日: {today}", "", "■ 実施内容"]
    if report["bullets"]:
        lines += [f"・{b}" for b in report["bullets"]]
    elif report["paragraphs"]:
        lines += [f"・{p}" for p in report["paragraphs"][:5]]
    lines += ["", "■ 補足"]
    lines.append(report["paragraphs"][0] if report["paragraphs"] else "特記事項はありません。")
    lines += ["", "ご確認のほどよろしくお願いいたします。"]
    return "\n".join(lines)


def _template_email(report: dict, signature: str, sender: str) -> str:
    lines = [f"件名: 【完了のご報告】{report['title']}", "", "お世話になっております。"]
    if sender:
        lines[-1] = f"お世話になっております。{sender}でございます。"
    lines += ["",
              f"このたびご依頼いただいておりました「{report['title']}」につきまして、"
              "作業が完了いたしましたのでご報告申し上げます。", ""]
    if report["bullets"]:
        lines.append("【実施内容】")
        lines += [f"・{b}" for b in report["bullets"]]
        lines.append("")
    if report["paragraphs"]:
        lines += [report["paragraphs"][0], ""]
    lines += ["ご不明な点やご要望などございましたら、お気軽にお申し付けください。",
              "今後ともどうぞよろしくお願い申し上げます。"]
    if signature:
        lines += ["", "----------------", signature]
    return "\n".join(lines)


# ---------------------------------------------------------------- AI生成

_AI_SYSTEM = (
    "あなたは日本のビジネス文化に精通したプロのビジネスライターです。"
    "与えられた完了報告Markdownを、指定されたチャネルの文化に合わせて書き直してください。"
    "出力は本文のみとし、前置きや説明は不要です。"
)

_AI_PROMPTS = {
    "slack": "次の完了報告を、社内Slack向けのフランクで親しみやすい進捗報告に書き直してください。"
             "絵文字を適度に使い、箇条書き中心で簡潔に。\n\n---\n{md}",
    "teams": "次の完了報告を、Microsoft Teams向けの丁寧な業務連絡に書き直してください。"
             "「【業務連絡】」で始め、■見出しと箇条書きで整理してください。\n\n---\n{md}",
    "email": "次の完了報告を、クライアント向けの丁寧なビジネスメール（件名付き）に"
             "書き直してください。冒頭の挨拶と結びの言葉を含めてください。\n\n---\n{md}",
}


# ---------------------------------------------------------------- エントリ

def switch(config: dict, md_path: str, clipboard_tone: str | None = "slack") -> dict:
    """3トーンの文章を生成して下書き保存。戻り値: {tone: (text, path)}"""
    path = Path(md_path)
    if not path.is_file():
        raise FileNotFoundError(f"Markdownファイルが見つかりません: {md_path}")
    md_text = path.read_text(encoding="utf-8")
    if not md_text.strip():
        raise ValueError("報告ファイルが空です。")

    report = _parse_report(md_text)
    tone_cfg = config["tone"]
    use_ai = llm.is_available(config)
    logger.info("文章生成モード: %s", "Claude API" if use_ai else "テンプレート")

    results = {}
    for tone in TONES:
        text = None
        if use_ai:
            text = llm.generate(config, _AI_SYSTEM, _AI_PROMPTS[tone].format(md=md_text))
        if not text:
            if tone == "slack":
                text = _template_slack(report)
            elif tone == "teams":
                text = _template_teams(report)
            else:
                text = _template_email(report, tone_cfg.get("signature", ""),
                                       tone_cfg.get("sender_name", ""))
        results[tone] = text

    out_dir = ensure_output_dir(config) / "drafts"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    saved = {}
    for tone, text in results.items():
        out_path = out_dir / f"{path.stem}_{tone}_{stamp}.txt"
        out_path.write_text(text, encoding="utf-8")
        saved[tone] = (text, out_path)
        logger.info("下書きを保存しました: %s", out_path)

    if clipboard_tone and tone_cfg.get("copy_to_clipboard", True):
        if copy_to_clipboard(results[clipboard_tone]):
            logger.info("%s 版をクリップボードにコピーしました", clipboard_tone)

    return saved
