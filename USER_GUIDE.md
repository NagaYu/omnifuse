# OmniFuse ユーザーガイド

**OmniFuse（オムニフューズ）** は、面倒なビジネス作業をコマンド一発で自動化するツールです。
プログラミングの知識は不要です。このガイドの順番どおりに進めれば、誰でも使い始められます。

---

## 📌 OmniFuseでできること

```
                        ┌─────────────────────────────┐
                        │         OmniFuse            │
                        │   （対話メニューで選ぶだけ）   │
                        └──────────────┬──────────────┘
        ┌────────────────┬─────────────┼─────────────────┐
        ▼                ▼             ▼                 ▼
 ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
 │ 1.グラフ整形 │ │ 2.仕様書    │ │ 3.文章作成   │ │ 4.SNS投稿   │
 │             │ │   デプロイ   │ │             │ │             │
 │ Excel/CSV   │ │ Gitログ/MD  │ │ 報告MD      │ │ 記事URL等   │
 │   ↓        │ │   ↓        │ │   ↓        │ │   ↓        │
 │ 美しいPDF/  │ │ Notion/    │ │ Slack/Teams │ │ X/LinkedIn/ │
 │ PNGグラフ   │ │ Confluence │ │ /メール3種   │ │ Qiita下書き │
 └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
```

| 機能 | 入力 | 出力 |
|------|------|------|
| **1. グラフ整形** | Excel / CSV | ビジネス品質のグラフ（PNG・PDF） |
| **2. 仕様書デプロイ** | Gitログ / Markdown | Notion・Confluenceのページ |
| **3. 文章作成** | 完了報告のMarkdown | Slack・Teams・メール用の3文面 |
| **4. SNS一括投稿** | 記事URL・テキスト | X・LinkedIn・Qiita用の投稿文（予約投稿対応） |

> 💡 **APIキーを設定しなくても使えます。** その場合、結果はすべて `output/` フォルダに
> 下書きとして保存されます（ドライランモード）。

---

## 🚀 セットアップ（最初に1回だけ）

### 手順1: Pythonの確認

OmniFuseには **Python 3.10以上** が必要です。

- **Mac**: 最初から入っていることが多いです。ターミナルで `python3 --version` と打って確認。
- **Windows**: [python.org](https://www.python.org/downloads/) からダウンロード。
  ⚠️ インストール画面で「**Add Python to PATH**」に必ずチェックを入れてください。

### 手順2: セットアップスクリプトを実行

```
┌──────────────────────────────────────────────┐
│  Mac / Linux の場合                           │
│                                              │
│  1. ターミナルを開く                           │
│  2. このフォルダに移動して以下を実行：           │
│                                              │
│     bash setup.sh                            │
│                                              │
├──────────────────────────────────────────────┤
│  Windows の場合                               │
│                                              │
│  1. setup.bat をダブルクリック                 │
│     （または コマンドプロンプトで setup.bat）    │
└──────────────────────────────────────────────┘
```

スクリプトが**すべて自動で**やってくれます：

```
 setup.sh / setup.bat の処理フロー

 [Pythonチェック] → [仮想環境を作成] → [ライブラリを一括インストール]
        │                                      │
        │            pandas / matplotlib / openpyxl / requests ...
        ▼                                      ▼
 [動作チェック] ──────────────────→ [起動コマンドを作成] → 🎉完了
```

最後に「🎉 セットアップが完了しました！」と表示されれば成功です。

### 手順3: 起動してみる

```bash
# Mac / Linux
./omnifuse.sh

# Windows
omnifuse
```

引数なしで実行すると、このような**対話メニュー**が表示されます：

```
═══════════════════════════════════════════════
 何を自動化しますか？
═══════════════════════════════════════════════
  1. グラフ整形      … Excel/CSVを美しいグラフ(PDF/画像)に
  2. 仕様書デプロイ  … Gitログ/MarkdownをNotion/Confluenceへ
  3. 文章作成        … 完了報告をSlack/Teams/メール用に変換
  4. SNS一括投稿     … 記事からX/LinkedIn/Qiita投稿文を生成
  q. 終了
───────────────────────────────────────────────
 番号を選んでください >
```

番号を入力して、画面の質問に答えるだけです。

---

## 📖 各機能の使い方

### 1️⃣ グラフ整形（ChartPurify）

ExcelやCSVの表を、そのまま会議資料に使える品質のグラフに変換します。

```bash
./omnifuse.sh chart 売上データ.csv
./omnifuse.sh chart 売上データ.xlsx --title "月次売上推移" --type bar
```

```
 売上データ.csv                     output/charts/売上データ_xxxx.png
 ┌──────────────┐                 ┌──────────────────────┐
 │ 月, 売上, 利益 │                 │  月次売上推移          │
 │ 4月,1250,310 │   ──────────▶   │  ▇▇  ▂▂ （青+グレー）  │
 │ 5月,1380,355 │    自動整形      │  ▇▇▇ ▂▂▂ 游ゴシック   │
 │ ...          │                 │  4月  5月  6月 ...     │
 └──────────────┘                 └──────────────────────┘
                                   PNG と PDF の2形式で保存
```

- 配色は **モノトーン＋青のアクセント**、フォントは **游ゴシック**（無い場合は自動代替）
- `--type` を省略すると、データ量に応じて棒/折れ線を自動選択
- 出力先: `output/charts/`

### 2️⃣ 仕様書デプロイ（DocDeploy）

GitのコミットログやMarkdownを、読みやすい仕様書ページとしてNotion/Confluenceに自動投稿します。

```bash
# Gitのコミットログから更新履歴ページを作る（Gitリポジトリ内で実行）
./omnifuse.sh doc --source git

# Markdownファイルから仕様書ページを作る
./omnifuse.sh doc --source md --input 仕様書.md --title "API仕様書 v2"
```

トークン未設定の場合は `output/docs/` にプレビューと送信予定データが保存されます。

### 3️⃣ 文章作成（ToneSwitcher）

1つの完了報告から、送り先に合わせた3種類の文章を同時生成します。

```
                              ┌──▶ 😊 Slack版（フランク・絵文字つき）
 完了報告.md ──[OmniFuse]──┼──▶ 📋 Teams版（業務連絡フォーマット）
                              └──▶ ✉️  メール版（クライアント向け敬語）
```

```bash
./omnifuse.sh tone 完了報告.md
./omnifuse.sh tone 完了報告.md --clipboard email   # メール版をコピー
```

- 3種類すべて `output/drafts/` に保存
- 指定した版が**クリップボードに自動コピー**されるので、すぐ貼り付けられます

### 4️⃣ SNS一括投稿（MultiPost）

1つの記事から、各SNSの文化に合わせた投稿文を一括生成します。

```bash
# 記事URLから生成（下書きのみ）
./omnifuse.sh post "https://example.com/blog/article"

# 予約投稿（トークン設定済みの場合）
./omnifuse.sh post 記事.md --when "2026-06-15 09:00"

# 予約キューの実行（時刻を過ぎた投稿を送信）
./omnifuse.sh post --run-queue
```

| プラットフォーム | 生成される文面 |
|---|---|
| **X** | 140文字以内に自動調整した告知文 |
| **LinkedIn** | ビジネス調の紹介文＋ハッシュタグ |
| **Qiita** | 技術記事のMarkdown下書き |

> ⏰ 予約投稿は `--run-queue` 実行時に送信されます。毎朝自動実行したい場合は
> Macなら `crontab`、Windowsなら「タスクスケジューラ」に登録してください。

---

## 🔑 APIキーの設定方法

すべて任意です。**使いたい機能のぶんだけ**設定してください。
設定はすべて `config.yaml` をメモ帳などで開いて書き込みます。

```
 config.yaml の編集イメージ

   anthropic:
     api_key: ""   ←  この "" の間にキーを貼り付ける
                       例: api_key: "sk-ant-api03-xxxx"
```

### 🤖 Claude API（文章の品質アップ・任意）

文章作成とSNS投稿文の生成をAIで行い、品質を大幅に向上させます。

1. [https://console.anthropic.com/](https://console.anthropic.com/) にアクセスしてアカウント作成
2. 左メニューの **API Keys** → **Create Key** をクリック
3. 表示されたキー（`sk-ant-` で始まる）をコピー
4. `config.yaml` の `anthropic:` → `api_key:` に貼り付け

### 📘 Notion

1. [https://www.notion.so/my-integrations](https://www.notion.so/my-integrations) で「新しいインテグレーション」を作成
2. 表示された **シークレット**（`secret_` で始まる）をコピー → `docdeploy:` → `notion:` → `token:` へ
3. デプロイ先にしたいNotionページを開き、右上「…」→「接続」→ 作成したインテグレーションを追加
4. ページURLの末尾32文字（英数字）が **parent_page_id** です
   ```
   https://www.notion.so/My-Page-1234567890abcdef1234567890abcdef
                                └────────── この部分 ──────────┘
   ```

### 📗 Confluence

1. [https://id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens) で「APIトークンを作成」
2. `config.yaml` の `confluence:` に以下を設定：
   - `base_url`: 例 `https://あなたの会社.atlassian.net/wiki`
   - `email`: Atlassianのログインメールアドレス
   - `api_token`: 作成したトークン
   - `space_key`: スペースのキー（スペースURLの `/spaces/XXX/` 部分）
3. `docdeploy:` → `target:` を `confluence` に変更

### 🐦 X（旧Twitter）

1. [https://developer.x.com/](https://developer.x.com/) でデベロッパー登録（無料プランで可）
2. アプリを作成し、**OAuth 2.0** の設定で `tweet.write` 権限を有効化
3. ユーザーアクセストークンを取得 → `multipost:` → `x:` → `access_token:` へ

### 💼 LinkedIn

1. [https://developer.linkedin.com/](https://developer.linkedin.com/) でアプリ作成
2. **w_member_social** 権限のアクセストークンを取得 → `linkedin:` → `access_token:` へ
3. 自分のプロフィールURN（`urn:li:person:xxxx`）を `author_urn:` へ

### 📝 Qiita

1. Qiitaにログイン → [設定 → アプリケーション](https://qiita.com/settings/applications)
2. 「新しくトークンを発行する」で **write_qiita** にチェックして発行
3. 表示されたトークンを `qiita:` → `access_token:` へ

---

## ❓ よくあるトラブル

| 症状 | 解決方法 |
|------|---------|
| `Python が見つかりません` | Pythonをインストール後、PCを再起動して再実行 |
| 文字化けしたグラフが出る | 游ゴシック等の日本語フォントが無い環境です。`config.yaml` の `font_candidates` に手持ちのフォント名を追加 |
| CSVが読めない | Excelで保存し直すか、文字コードを UTF-8 / Shift-JIS にしてください（両対応） |
| `Notion APIエラー (404)` | parent_page_id の誤り、またはページにインテグレーションが「接続」されていません |
| `X APIエラー (403)` | トークンに `tweet.write` 権限がありません。アプリ設定を確認 |
| クリップボードにコピーされない | Linuxでは `xclip` のインストールが必要です: `sudo apt install xclip` |
| その他のエラー | `logs/omnifuse.log` に詳細が記録されています |

---

## 📁 フォルダ構成

```
OmniFuse/
├── omnifuse.sh / omnifuse.bat   ← 起動コマンド（セットアップ時に生成）
├── setup.sh / setup.bat         ← 環境構築スクリプト
├── config.yaml                  ← 設定ファイル（APIキー等）
├── USER_GUIDE.md                ← このガイド
├── samples/                     ← お試し用サンプルデータ
├── output/                      ← 生成物はすべてここ
│   ├── charts/                  …グラフ
│   ├── docs/                    …仕様書プレビュー
│   ├── drafts/                  …文章下書き
│   ├── posts/                   …SNS投稿文
│   └── post_queue.json          …予約投稿キュー
└── logs/omnifuse.log            ← トラブル時はここを確認
```

困ったときはまず `samples/` のサンプルで動作確認してみてください：

```bash
./omnifuse.sh chart samples/sample_sales.csv
./omnifuse.sh tone samples/sample_report.md
```
