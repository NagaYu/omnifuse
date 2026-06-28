# OmniFuse

A business automation core CLI tool. Automate four routine tasks with a single command (or through an interactive menu).

| Command | Feature |
|---|---|
| `omnifuse chart <file>` | **ChartPurify** — Turn Excel/CSV into business-quality charts (PNG/PDF) |
| `omnifuse doc` | **DocDeploy** — Auto-deploy Git logs / Markdown to Notion / Confluence |
| `omnifuse tone <md>` | **ToneSwitcher** — Generate a completion report in 3 tones at once (Slack / Teams / email) |
| `omnifuse post <src>` | **MultiPost** — Generate and schedule posts for X / LinkedIn / Qiita from a single article |

## Quick Start

```bash
# 1. Setup (auto-checks dependencies and installs everything)
bash setup.sh          # Mac / Linux
setup.bat              # Windows

# 2. Launch (no arguments → interactive menu)
./omnifuse.sh

# 3. Try it with the samples
./omnifuse.sh chart samples/sample_sales.csv
./omnifuse.sh tone samples/sample_report.md
```

- All features work without API keys, running in dry-run mode (drafts are saved to `output/`)
- For detailed setup steps and how to configure API keys, see **[USER_GUIDE.md](USER_GUIDE.md)**
- Set a Claude API key in `config.yaml` to switch text generation to high-quality AI mode

## Requirements

- Python 3.10+
- macOS / Linux / Windows
