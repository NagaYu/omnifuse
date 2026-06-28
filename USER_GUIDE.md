# OmniFuse User Guide

**OmniFuse** is a tool that automates tedious business tasks with a single command.
No programming knowledge is required. If you follow this guide in order, anyone can get started.

---

## 📌 What OmniFuse Can Do

```
                        ┌─────────────────────────────┐
                        │         OmniFuse            │
                        │   (just pick from the menu) │
                        └──────────────┬──────────────┘
        ┌────────────────┬─────────────┼─────────────────┐
        ▼                ▼             ▼                 ▼
 ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
 │ 1.Chart     │ │ 2.Doc       │ │ 3.Tone      │ │ 4.Multi     │
 │   Purify    │ │   Deploy    │ │   Switcher  │ │   Post      │
 │ Excel/CSV   │ │ Git log/MD  │ │ report MD   │ │ article URL │
 │   ↓        │ │   ↓        │ │   ↓        │ │   ↓        │
 │ polished    │ │ Notion/    │ │ Slack/Teams │ │ X/LinkedIn/ │
 │ PDF/PNG     │ │ Confluence │ │ /email x3   │ │ Qiita draft │
 └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
```

| Feature | Input | Output |
|---------|-------|--------|
| **1. Chart Purify** | Excel / CSV | Business-quality charts (PNG & PDF) |
| **2. Doc Deploy** | Git log / Markdown | Notion / Confluence pages |
| **3. Tone Switcher** | Completion report (Markdown) | 3 messages for Slack / Teams / email |
| **4. Multi Post** | Article URL / text | Posts for X / LinkedIn / Qiita (with scheduling) |

> 💡 **You can use it without setting up API keys.** In that case, results are all saved
> as drafts in the `output/` folder (dry-run mode).

---

## 🚀 Setup (just once, the first time)

### Step 1: Check Python

OmniFuse requires **Python 3.10 or later**.

- **Mac**: Often pre-installed. Run `python3 --version` in the terminal to check.
- **Windows**: Download from [python.org](https://www.python.org/downloads/).
  ⚠️ Be sure to check "**Add Python to PATH**" on the installer screen.

### Step 2: Run the setup script

```
┌──────────────────────────────────────────────┐
│  On Mac / Linux                              │
│                                              │
│  1. Open a terminal                          │
│  2. Move to this folder and run:             │
│                                              │
│     bash setup.sh                            │
│                                              │
├──────────────────────────────────────────────┤
│  On Windows                                  │
│                                              │
│  1. Double-click setup.bat                   │
│     (or run setup.bat in Command Prompt)     │
└──────────────────────────────────────────────┘
```

The script does **everything automatically**:

```
 setup.sh / setup.bat processing flow

 [Check Python] → [Create virtual env] → [Install libraries at once]
        │                                      │
        │            pandas / matplotlib / openpyxl / requests ...
        ▼                                      ▼
 [Verify it works] ─────────────────→ [Create launch command] → 🎉 Done
```

If "🎉 Setup complete!" appears at the end, it succeeded.

### Step 3: Launch it

```bash
# Mac / Linux
./omnifuse.sh

# Windows
omnifuse
```

Running it with no arguments shows this **interactive menu**:

```
═══════════════════════════════════════════════
 What would you like to automate?
═══════════════════════════════════════════════
  1. Chart Purify   … Excel/CSV into beautiful charts (PDF/image)
  2. Doc Deploy     … Git log/Markdown to Notion/Confluence
  3. Tone Switcher  … Convert a report for Slack/Teams/email
  4. Multi Post     … Generate X/LinkedIn/Qiita posts from an article
  q. Quit
───────────────────────────────────────────────
 Enter a number >
```

Just enter a number and answer the on-screen prompts.

---

## 📖 How to Use Each Feature

### 1️⃣ Chart Purify

Convert Excel or CSV tables into presentation-ready charts.

```bash
./omnifuse.sh chart sales_data.csv
./omnifuse.sh chart sales_data.xlsx --title "Monthly Sales Trend" --type bar
```

```
 sales_data.csv                     output/charts/sales_data_xxxx.png
 ┌──────────────┐                 ┌──────────────────────┐
 │ Month,Sales..│                 │  Monthly Sales Trend  │
 │ Apr,1250,310 │   ──────────▶   │  ▇▇  ▂▂ (blue+gray)   │
 │ May,1380,355 │   auto-format   │  ▇▇▇ ▂▂▂ Yu Gothic    │
 │ ...          │                 │  Apr  May  Jun ...    │
 └──────────────┘                 └──────────────────────┘
                                   Saved as both PNG and PDF
```

- Colors use a **monochrome palette + a blue accent**; the font is **Yu Gothic** (falls back automatically if unavailable)
- Omitting `--type` auto-selects bar/line based on the amount of data
- Output: `output/charts/`

### 2️⃣ Doc Deploy

Auto-publish Git commit logs or Markdown as readable spec pages to Notion / Confluence.

```bash
# Build an update-history page from Git commit logs (run inside a Git repo)
./omnifuse.sh doc --source git

# Build a spec page from a Markdown file
./omnifuse.sh doc --source md --input spec.md --title "API Spec v2"
```

If no token is set, a preview and the payload to be sent are saved to `output/docs/`.

### 3️⃣ Tone Switcher

Generate three versions of a message from a single completion report, tailored to each recipient.

```
                              ┌──▶ 😊 Slack version (casual, with emoji)
 report.md ──[OmniFuse]────┼──▶ 📋 Teams version (business-memo format)
                              └──▶ ✉️  Email version (polite, client-facing)
```

```bash
./omnifuse.sh tone report.md
./omnifuse.sh tone report.md --clipboard email   # copy the email version
```

- All three versions are saved to `output/drafts/`
- The chosen version is **copied to the clipboard automatically**, ready to paste

### 4️⃣ Multi Post

Generate posts from a single article, tailored to each social platform's culture.

```bash
# Generate from an article URL (drafts only)
./omnifuse.sh post "https://example.com/blog/article"

# Schedule a post (when a token is configured)
./omnifuse.sh post article.md --when "2026-06-15 09:00"

# Run the scheduled queue (send posts past their scheduled time)
./omnifuse.sh post --run-queue
```

| Platform | Generated content |
|---|---|
| **X** | Announcement auto-trimmed to 140 characters |
| **LinkedIn** | Business-toned intro with hashtags |
| **Qiita** | Markdown draft for a technical article |

> ⏰ Scheduled posts are sent when you run `--run-queue`. To run it automatically every morning,
> register it with `crontab` on Mac or "Task Scheduler" on Windows.

---

## 🔑 How to Configure API Keys

All of these are optional. Configure **only the ones you need**.
All settings are written into `config.yaml`, which you can open in any text editor.

```
 Editing config.yaml

   anthropic:
     api_key: ""   ←  paste your key between the quotes
                       e.g. api_key: "sk-ant-api03-xxxx"
```

### 🤖 Claude API (better text quality, optional)

Generates the Tone Switcher and Multi Post text with AI, greatly improving quality.

1. Go to [https://console.anthropic.com/](https://console.anthropic.com/) and create an account
2. Click **API Keys** → **Create Key** in the left menu
3. Copy the displayed key (starts with `sk-ant-`)
4. Paste it into `anthropic:` → `api_key:` in `config.yaml`

### 📘 Notion

1. Create a "New integration" at [https://www.notion.so/my-integrations](https://www.notion.so/my-integrations)
2. Copy the displayed **secret** (starts with `secret_`) into `docdeploy:` → `notion:` → `token:`
3. Open the Notion page you want to deploy to, click "…" → "Connections" → add the integration you created
4. The last 32 characters (alphanumeric) of the page URL is the **parent_page_id**
   ```
   https://www.notion.so/My-Page-1234567890abcdef1234567890abcdef
                                └────────── this part ──────────┘
   ```

### 📗 Confluence

1. Create an API token at [https://id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Set the following under `confluence:` in `config.yaml`:
   - `base_url`: e.g. `https://yourcompany.atlassian.net/wiki`
   - `email`: your Atlassian login email
   - `api_token`: the token you created
   - `space_key`: the space key (the `/spaces/XXX/` part of the space URL)
3. Change `docdeploy:` → `target:` to `confluence`

### 🐦 X (formerly Twitter)

1. Register as a developer at [https://developer.x.com/](https://developer.x.com/) (the free plan works)
2. Create an app and enable the `tweet.write` scope in the **OAuth 2.0** settings
3. Obtain a user access token → put it in `multipost:` → `x:` → `access_token:`

### 💼 LinkedIn

1. Create an app at [https://developer.linkedin.com/](https://developer.linkedin.com/)
2. Obtain an access token with the **w_member_social** scope → put it in `linkedin:` → `access_token:`
3. Put your profile URN (`urn:li:person:xxxx`) in `author_urn:`

### 📝 Qiita

1. Log in to Qiita → [Settings → Applications](https://qiita.com/settings/applications)
2. Click "Generate new token", check **write_qiita**, and issue it
3. Put the displayed token in `qiita:` → `access_token:`

---

## ❓ Troubleshooting

| Symptom | Solution |
|---------|----------|
| `Python not found` | Install Python, restart your PC, then try again |
| Charts come out with garbled text | No Japanese font (e.g. Yu Gothic) is installed. Add a font name you have to `font_candidates` in `config.yaml` |
| CSV can't be read | Re-save it in Excel, or set the encoding to UTF-8 / Shift-JIS (both are supported) |
| `Notion API error (404)` | Wrong parent_page_id, or the integration isn't "connected" to the page |
| `X API error (403)` | The token lacks the `tweet.write` scope. Check the app settings |
| Clipboard copy doesn't work | On Linux, `xclip` must be installed: `sudo apt install xclip` |
| Other errors | Details are recorded in `logs/omnifuse.log` |

---

## 📁 Folder Structure

```
OmniFuse/
├── omnifuse.sh / omnifuse.bat   ← launch command (generated during setup)
├── setup.sh / setup.bat         ← environment setup scripts
├── config.yaml                  ← config file (API keys, etc.)
├── USER_GUIDE.md                ← this guide
├── samples/                     ← sample data to try
├── output/                      ← all generated files go here
│   ├── charts/                  …charts
│   ├── docs/                    …spec previews
│   ├── drafts/                  …text drafts
│   ├── posts/                   …social posts
│   └── post_queue.json          …scheduled-post queue
└── logs/omnifuse.log            ← check here when something goes wrong
```

When in doubt, first try the samples in `samples/` to confirm it works:

```bash
./omnifuse.sh chart samples/sample_sales.csv
./omnifuse.sh tone samples/sample_report.md
```
