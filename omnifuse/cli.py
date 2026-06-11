"""OmniFuse CLI - 引数で機能を切り替え。引数なしならインタラクティブメニュー。"""

import argparse
import logging
import sys
import traceback
from pathlib import Path

from . import __version__
from .config import load_config

logger = logging.getLogger("omnifuse")

BANNER = r"""
  ____                  _ ______
 / __ \____ ___  ____  (_) ____/_  __________
/ / / / __ `__ \/ __ \/ / /_  / / / / ___/ _ \
/ /_/ / / / / / / / / / / __/ / /_/ (__  )  __/
\____/_/ /_/ /_/_/ /_/_/_/    \__,_/____/\___/   v{version}

  ビジネス自動化コアCLIツール
"""

MENU = """
═══════════════════════════════════════════════
 何を自動化しますか？
═══════════════════════════════════════════════
  1. グラフ整形      … Excel/CSVを美しいグラフ(PDF/画像)に
  2. 仕様書デプロイ  … Gitログ/MarkdownをNotion/Confluenceへ
  3. 文章作成        … 完了報告をSlack/Teams/メール用に変換
  4. SNS一括投稿     … 記事からX/LinkedIn/Qiita投稿文を生成
  q. 終了
───────────────────────────────────────────────"""


def setup_logging(config: dict) -> None:
    log_dir = Path(config["general"]["log_dir"])
    log_dir.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_dir / "omnifuse.log", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)  # トレースバックはファイルのみに記録
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    logging.basicConfig(
        level=logging.INFO,  # 外部ライブラリのDEBUGログは抑制
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[file_handler, console_handler],
    )
    logger.setLevel(logging.DEBUG)  # OmniFuse自身の詳細ログはファイルへ


# ---------------------------------------------------------------- 各コマンド

def cmd_chart(args, config) -> None:
    from . import chart_purify
    outputs = chart_purify.purify(args.input, config,
                                  chart_type=args.type, title=args.title)
    print("\n✅ グラフを出力しました:")
    for path in outputs:
        print(f"   {path}")


def cmd_doc(args, config) -> None:
    from . import doc_deploy
    result = doc_deploy.deploy(config, source=args.source,
                               md_path=args.input, title=args.title)
    print("\n" + result)


def cmd_tone(args, config) -> None:
    from . import tone_switcher
    saved = tone_switcher.switch(config, args.input, clipboard_tone=args.clipboard)
    print("\n✅ 3種類の文章を生成しました:")
    for tone, (text, path) in saved.items():
        print(f"\n──── {tone_switcher.TONE_LABELS[tone]} ────")
        preview = text if len(text) <= 400 else text[:400] + "…"
        print(preview)
        print(f"（保存先: {path}）")
    if args.clipboard:
        print(f"\n📋 {args.clipboard} 版をクリップボードにコピー済みです。")


def cmd_post(args, config) -> None:
    from . import multi_post
    if args.run_queue:
        print("\n" + multi_post.run_queue(config))
        return
    if not args.source:
        raise ValueError("元記事のURLまたはテキスト/ファイルを指定してください。")
    result = multi_post.schedule_posts(config, args.source, when=args.when)
    print("\n" + result)


# ---------------------------------------------------------- 対話式メニュー

def _ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{prompt}{suffix}: ").strip()
    return value or default


def interactive_menu(config: dict) -> None:
    print(BANNER.format(version=__version__))
    while True:
        print(MENU)
        try:
            choice = input(" 番号を選んでください > ").strip().lower()
            if choice == "1":
                path = _ask(" Excel/CSVファイルのパス")
                if not path:
                    print(" ⚠️ ファイルパスを入力してください。")
                    continue
                args = argparse.Namespace(input=path, type="auto", title=None)
                cmd_chart(args, config)
            elif choice == "2":
                source = _ask(" 入力元（git=コミットログ / mdファイルパス）", "git")
                if source == "git":
                    args = argparse.Namespace(source="git", input=None, title=None)
                else:
                    args = argparse.Namespace(source="md", input=source, title=None)
                cmd_doc(args, config)
            elif choice == "3":
                path = _ask(" 完了報告Markdownのパス")
                if not path:
                    print(" ⚠️ ファイルパスを入力してください。")
                    continue
                clip = _ask(" クリップボードにコピーする版 (slack/teams/email/no)", "slack")
                args = argparse.Namespace(input=path,
                                          clipboard=None if clip == "no" else clip)
                cmd_tone(args, config)
            elif choice == "4":
                source = _ask(" 元記事のURL・ファイル・テキスト")
                if not source:
                    print(" ⚠️ 入力してください。")
                    continue
                when = _ask(" 予約日時（例 2026-06-15 09:00 / 空=即時）", "")
                args = argparse.Namespace(source=source, when=when or None,
                                          run_queue=False)
                cmd_post(args, config)
            elif choice in ("q", "quit", "exit"):
                print(" ご利用ありがとうございました！")
                return
            else:
                print(" ⚠️ 1〜4 または q を入力してください。")
        except (EOFError, KeyboardInterrupt):
            print("\n 終了します。ご利用ありがとうございました！")
            return
        except Exception as e:
            print(f"\n ❌ エラー: {e}")
            logger.debug(traceback.format_exc())


# ---------------------------------------------------------------- パーサー

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="omnifuse",
        description="OmniFuse - ビジネス自動化コアCLIツール（引数なしで対話メニュー起動）",
    )
    parser.add_argument("--version", action="version",
                        version=f"OmniFuse {__version__}")
    parser.add_argument("--config", help="config.yaml のパス（省略時は自動検出）")
    sub = parser.add_subparsers(dest="command")

    p = sub.add_parser("chart", help="[ChartPurify] Excel/CSVをグラフ整形")
    p.add_argument("input", help="入力ファイル (CSV/TSV/Excel)")
    p.add_argument("--type", choices=["auto", "bar", "line"], default="auto",
                   help="グラフ種別（既定: auto）")
    p.add_argument("--title", help="グラフタイトル")

    p = sub.add_parser("doc", help="[DocDeploy] 仕様書をNotion/Confluenceへ")
    p.add_argument("--source", choices=["git", "md"], default="git",
                   help="入力元（git=コミットログ / md=Markdownファイル）")
    p.add_argument("--input", help="Markdownファイルパス（--source md のとき）")
    p.add_argument("--title", help="ページタイトル")

    p = sub.add_parser("tone", help="[ToneSwitcher] 報告を3トーンで生成")
    p.add_argument("input", help="完了報告Markdownのパス")
    p.add_argument("--clipboard", choices=["slack", "teams", "email"],
                   default="slack", help="クリップボードへコピーする版")

    p = sub.add_parser("post", help="[MultiPost] SNS投稿文を一括生成・予約投稿")
    p.add_argument("source", nargs="?", help="元記事URL・ファイル・テキスト")
    p.add_argument("--when", help='予約日時（例: "2026-06-15 09:00"）')
    p.add_argument("--run-queue", action="store_true",
                   help="予約キューの送信時刻を過ぎた投稿を実行")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
    except ValueError as e:
        print(f"❌ {e}")
        return 1
    setup_logging(config)

    handlers = {"chart": cmd_chart, "doc": cmd_doc,
                "tone": cmd_tone, "post": cmd_post}
    try:
        if args.command in handlers:
            handlers[args.command](args, config)
        else:
            interactive_menu(config)
        return 0
    except KeyboardInterrupt:
        print("\n中断しました。")
        return 130
    except FileNotFoundError as e:
        print(f"\n❌ {e}")
        return 1
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        print("   詳細は logs/omnifuse.log を確認してください。")
        logger.debug("未処理のエラー", exc_info=True)
        return 1
