# OmniFuse

ビジネス自動化コアCLIツール。コマンド一発（または対話メニュー）で4つの定型業務を自動化します。

| コマンド | 機能 |
|---|---|
| `omnifuse chart <file>` | **ChartPurify** — Excel/CSVをビジネス品質のグラフ（PNG/PDF）に整形 |
| `omnifuse doc` | **DocDeploy** — Gitログ/MarkdownをNotion/Confluenceへ自動デプロイ |
| `omnifuse tone <md>` | **ToneSwitcher** — 完了報告をSlack/Teams/メールの3トーンで同時生成 |
| `omnifuse post <src>` | **MultiPost** — 記事からX/LinkedIn/Qiita投稿文を一括生成・予約投稿 |

## クイックスタート

```bash
# 1. セットアップ（依存関係の自動チェック＆一括インストール）
bash setup.sh          # Mac / Linux
setup.bat              # Windows

# 2. 起動（引数なしで対話メニュー）
./omnifuse.sh

# 3. サンプルで試す
./omnifuse.sh chart samples/sample_sales.csv
./omnifuse.sh tone samples/sample_report.md
```

- APIキーなしでも全機能がドライラン（`output/` への下書き保存）で動作します
- 詳しいセットアップ手順・APIキーの設定方法は **[USER_GUIDE.md](USER_GUIDE.md)** を参照
- Claude APIキーを `config.yaml` に設定すると、文章生成がAIによる高品質モードになります

## 動作環境

- Python 3.10+
- macOS / Linux / Windows
