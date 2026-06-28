"""OmniFuse CLI - switch features by argument. With no arguments, show an interactive menu."""

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

  Business Automation Core CLI Tool
"""

MENU = """
═══════════════════════════════════════════════
 What would you like to automate?
═══════════════════════════════════════════════
  1. Chart Purify   … Excel/CSV into beautiful charts (PDF/image)
  2. Doc Deploy     … Git log/Markdown to Notion/Confluence
  3. Tone Switcher  … Convert a report for Slack/Teams/email
  4. Multi Post     … Generate X/LinkedIn/Qiita posts from an article
  q. Quit
───────────────────────────────────────────────"""


def setup_logging(config: dict) -> None:
    log_dir = Path(config["general"]["log_dir"])
    log_dir.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_dir / "omnifuse.log", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)  # tracebacks go to the file only
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    logging.basicConfig(
        level=logging.INFO,  # suppress DEBUG logs from third-party libraries
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[file_handler, console_handler],
    )
    logger.setLevel(logging.DEBUG)  # OmniFuse's own verbose logs go to the file


# ---------------------------------------------------------------- commands

def cmd_chart(args, config) -> None:
    from . import chart_purify
    outputs = chart_purify.purify(args.input, config,
                                  chart_type=args.type, title=args.title)
    print("\n✅ Charts generated:")
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
    print("\n✅ Generated 3 versions:")
    for tone, (text, path) in saved.items():
        print(f"\n──── {tone_switcher.TONE_LABELS[tone]} ────")
        preview = text if len(text) <= 400 else text[:400] + "…"
        print(preview)
        print(f"(saved to: {path})")
    if args.clipboard:
        print(f"\n📋 The {args.clipboard} version has been copied to the clipboard.")


def cmd_post(args, config) -> None:
    from . import multi_post
    if args.run_queue:
        print("\n" + multi_post.run_queue(config))
        return
    if not args.source:
        raise ValueError("Specify the source article URL, text, or file.")
    result = multi_post.schedule_posts(config, args.source, when=args.when)
    print("\n" + result)


# ---------------------------------------------------------- interactive menu

def _ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{prompt}{suffix}: ").strip()
    return value or default


def interactive_menu(config: dict) -> None:
    print(BANNER.format(version=__version__))
    while True:
        print(MENU)
        try:
            choice = input(" Enter a number > ").strip().lower()
            if choice == "1":
                path = _ask(" Path to the Excel/CSV file")
                if not path:
                    print(" ⚠️ Please enter a file path.")
                    continue
                args = argparse.Namespace(input=path, type="auto", title=None)
                cmd_chart(args, config)
            elif choice == "2":
                source = _ask(" Source (git=commit log / path to .md file)", "git")
                if source == "git":
                    args = argparse.Namespace(source="git", input=None, title=None)
                else:
                    args = argparse.Namespace(source="md", input=source, title=None)
                cmd_doc(args, config)
            elif choice == "3":
                path = _ask(" Path to the completion-report Markdown")
                if not path:
                    print(" ⚠️ Please enter a file path.")
                    continue
                clip = _ask(" Version to copy to clipboard (slack/teams/email/no)", "slack")
                args = argparse.Namespace(input=path,
                                          clipboard=None if clip == "no" else clip)
                cmd_tone(args, config)
            elif choice == "4":
                source = _ask(" Source article URL / file / text")
                if not source:
                    print(" ⚠️ Please enter a value.")
                    continue
                when = _ask(" Schedule time (e.g. 2026-06-15 09:00 / empty = now)", "")
                args = argparse.Namespace(source=source, when=when or None,
                                          run_queue=False)
                cmd_post(args, config)
            elif choice in ("q", "quit", "exit"):
                print(" Thank you for using OmniFuse!")
                return
            else:
                print(" ⚠️ Please enter 1-4 or q.")
        except (EOFError, KeyboardInterrupt):
            print("\n Exiting. Thank you for using OmniFuse!")
            return
        except Exception as e:
            print(f"\n ❌ Error: {e}")
            logger.debug(traceback.format_exc())


# ---------------------------------------------------------------- parser

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="omnifuse",
        description="OmniFuse - Business Automation Core CLI (run with no arguments for the interactive menu)",
    )
    parser.add_argument("--version", action="version",
                        version=f"OmniFuse {__version__}")
    parser.add_argument("--config", help="Path to config.yaml (auto-detected if omitted)")
    sub = parser.add_subparsers(dest="command")

    p = sub.add_parser("chart", help="[ChartPurify] Format Excel/CSV into a chart")
    p.add_argument("input", help="Input file (CSV/TSV/Excel)")
    p.add_argument("--type", choices=["auto", "bar", "line"], default="auto",
                   help="Chart type (default: auto)")
    p.add_argument("--title", help="Chart title")

    p = sub.add_parser("doc", help="[DocDeploy] Deploy a spec to Notion/Confluence")
    p.add_argument("--source", choices=["git", "md"], default="git",
                   help="Source (git=commit log / md=Markdown file)")
    p.add_argument("--input", help="Path to the Markdown file (when --source md)")
    p.add_argument("--title", help="Page title")

    p = sub.add_parser("tone", help="[ToneSwitcher] Generate a report in 3 tones")
    p.add_argument("input", help="Path to the completion-report Markdown")
    p.add_argument("--clipboard", choices=["slack", "teams", "email"],
                   default="slack", help="Version to copy to the clipboard")

    p = sub.add_parser("post", help="[MultiPost] Generate and schedule social posts")
    p.add_argument("source", nargs="?", help="Source article URL / file / text")
    p.add_argument("--when", help='Schedule time (e.g. "2026-06-15 09:00")')
    p.add_argument("--run-queue", action="store_true",
                   help="Send queued posts whose scheduled time has passed")
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
        print("\nAborted.")
        return 130
    except FileNotFoundError as e:
        print(f"\n❌ {e}")
        return 1
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        print("   See logs/omnifuse.log for details.")
        logger.debug("Unhandled error", exc_info=True)
        return 1
