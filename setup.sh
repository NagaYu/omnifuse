#!/usr/bin/env bash
# ============================================================
# OmniFuse 一括環境構築スクリプト (macOS / Linux)
# 使い方:  bash setup.sh
# ============================================================
set -u

cd "$(dirname "$0")"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
ok()   { printf "${GREEN}✅ %s${NC}\n" "$1"; }
warn() { printf "${YELLOW}⚠️  %s${NC}\n" "$1"; }
err()  { printf "${RED}❌ %s${NC}\n" "$1"; }

echo "============================================"
echo " OmniFuse セットアップを開始します"
echo "============================================"

# --- 1. Python の確認 ---------------------------------------
PYTHON=""
for cmd in python3 python; do
  if command -v "$cmd" >/dev/null 2>&1; then
    version=$("$cmd" -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")' 2>/dev/null)
    major=${version%%.*}; minor=${version##*.}
    if [ "$major" -ge 3 ] && [ "$minor" -ge 10 ]; then
      PYTHON="$cmd"
      ok "Python $version を検出しました ($cmd)"
      break
    fi
  fi
done
if [ -z "$PYTHON" ]; then
  err "Python 3.10 以上が見つかりません。"
  echo "   https://www.python.org/downloads/ からインストール後、再実行してください。"
  exit 1
fi

# --- 2. 仮想環境の作成 ---------------------------------------
# フォルダ名に ":" が含まれると venv を作成できないため、
# その場合はホームディレクトリ側に作成する
case "$(pwd)" in
  *:*) VENV_DIR="$HOME/.omnifuse/venv"
       warn "フォルダ名に ':' が含まれるため、仮想環境を $VENV_DIR に作成します" ;;
  *)   VENV_DIR="$(pwd)/.venv" ;;
esac

if [ ! -d "$VENV_DIR" ]; then
  echo "📦 仮想環境を作成しています..."
  mkdir -p "$(dirname "$VENV_DIR")"
  "$PYTHON" -m venv "$VENV_DIR" || { err "仮想環境の作成に失敗しました"; exit 1; }
  ok "仮想環境を作成しました: $VENV_DIR"
else
  ok "既存の仮想環境を使用します: $VENV_DIR"
fi

VENV_PY="$VENV_DIR/bin/python"

# --- 3. 依存ライブラリの一括インストール ----------------------
echo "📦 依存ライブラリをインストールしています（数分かかる場合があります）..."
"$VENV_PY" -m pip install --upgrade pip --quiet
if "$VENV_PY" -m pip install -r requirements.txt --quiet; then
  ok "依存ライブラリをインストールしました"
else
  err "ライブラリのインストールに失敗しました。ネットワーク接続を確認して再実行してください。"
  exit 1
fi

# --- 4. 依存関係の自動チェック --------------------------------
echo "🔍 動作チェックを実行しています..."
if "$VENV_PY" - <<'EOF'
import importlib, sys
missing = []
for mod in ("pandas", "openpyxl", "matplotlib", "requests", "yaml"):
    try:
        importlib.import_module(mod)
    except ImportError:
        missing.append(mod)
if missing:
    print("missing:", ", ".join(missing))
    sys.exit(1)
import omnifuse.cli  # CLI本体の読み込み確認
EOF
then
  ok "すべての依存ライブラリが正常に読み込めました"
else
  err "動作チェックに失敗しました。上記のエラー内容をご確認ください。"
  exit 1
fi

# --- 5. 設定ファイルと起動コマンドの準備 ----------------------
if [ ! -f "config.yaml" ] && [ -f "config.example.yaml" ]; then
  cp config.example.yaml config.yaml
  ok "config.example.yaml から config.yaml を作成しました"
elif [ -f "config.yaml" ]; then
  ok "設定ファイル config.yaml を確認しました"
else
  warn "config.yaml が見つかりません（既定設定で動作します）"
fi

cat > omnifuse.sh <<EOF
#!/usr/bin/env bash
DIR="\$(cd "\$(dirname "\$0")" && pwd)"
cd "\$DIR"
exec "$VENV_PY" -m omnifuse "\$@"
EOF
chmod +x omnifuse.sh
ok "起動コマンド ./omnifuse.sh を作成しました"

echo ""
echo "============================================"
echo " 🎉 セットアップが完了しました！"
echo "============================================"
echo ""
echo " 使い方:"
echo "   ./omnifuse.sh              … 対話メニューを起動"
echo "   ./omnifuse.sh chart data.csv   … グラフ整形"
echo "   ./omnifuse.sh tone report.md   … 文章3トーン生成"
echo ""
echo " APIキーの設定方法は USER_GUIDE.md をご覧ください。"
