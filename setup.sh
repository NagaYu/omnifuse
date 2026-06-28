#!/usr/bin/env bash
# ============================================================
# OmniFuse one-shot environment setup script (macOS / Linux)
# Usage:  bash setup.sh
# ============================================================
set -u

cd "$(dirname "$0")"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
ok()   { printf "${GREEN}✅ %s${NC}\n" "$1"; }
warn() { printf "${YELLOW}⚠️  %s${NC}\n" "$1"; }
err()  { printf "${RED}❌ %s${NC}\n" "$1"; }

echo "============================================"
echo " Starting OmniFuse setup"
echo "============================================"

# --- 1. Check Python ----------------------------------------
PYTHON=""
for cmd in python3 python; do
  if command -v "$cmd" >/dev/null 2>&1; then
    version=$("$cmd" -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")' 2>/dev/null)
    major=${version%%.*}; minor=${version##*.}
    if [ "$major" -ge 3 ] && [ "$minor" -ge 10 ]; then
      PYTHON="$cmd"
      ok "Detected Python $version ($cmd)"
      break
    fi
  fi
done
if [ -z "$PYTHON" ]; then
  err "Python 3.10 or later was not found."
  echo "   Install it from https://www.python.org/downloads/ and run this again."
  exit 1
fi

# --- 2. Create the virtual environment ----------------------
# A folder name containing ":" prevents venv creation, so in that case
# create it under the home directory instead.
case "$(pwd)" in
  *:*) VENV_DIR="$HOME/.omnifuse/venv"
       warn "Folder name contains ':', so the virtual environment will be created at $VENV_DIR" ;;
  *)   VENV_DIR="$(pwd)/.venv" ;;
esac

if [ ! -d "$VENV_DIR" ]; then
  echo "📦 Creating the virtual environment..."
  mkdir -p "$(dirname "$VENV_DIR")"
  "$PYTHON" -m venv "$VENV_DIR" || { err "Failed to create the virtual environment"; exit 1; }
  ok "Created the virtual environment: $VENV_DIR"
else
  ok "Using the existing virtual environment: $VENV_DIR"
fi

VENV_PY="$VENV_DIR/bin/python"

# --- 3. Install dependencies in one go ----------------------
echo "📦 Installing dependencies (this may take a few minutes)..."
"$VENV_PY" -m pip install --upgrade pip --quiet
if "$VENV_PY" -m pip install -r requirements.txt --quiet; then
  ok "Installed dependencies"
else
  err "Failed to install libraries. Check your network connection and try again."
  exit 1
fi

# --- 4. Auto-check the dependencies -------------------------
echo "🔍 Running a sanity check..."
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
import omnifuse.cli  # confirm the CLI itself imports
EOF
then
  ok "All dependencies imported successfully"
else
  err "The sanity check failed. Please review the error above."
  exit 1
fi

# --- 5. Prepare the config file and launch command ----------
if [ ! -f "config.yaml" ] && [ -f "config.example.yaml" ]; then
  cp config.example.yaml config.yaml
  ok "Created config.yaml from config.example.yaml"
elif [ -f "config.yaml" ]; then
  ok "Found the config file config.yaml"
else
  warn "config.yaml not found (running with default settings)"
fi

cat > omnifuse.sh <<EOF
#!/usr/bin/env bash
DIR="\$(cd "\$(dirname "\$0")" && pwd)"
cd "\$DIR"
exec "$VENV_PY" -m omnifuse "\$@"
EOF
chmod +x omnifuse.sh
ok "Created the launch command ./omnifuse.sh"

echo ""
echo "============================================"
echo " 🎉 Setup complete!"
echo "============================================"
echo ""
echo " Usage:"
echo "   ./omnifuse.sh              … launch the interactive menu"
echo "   ./omnifuse.sh chart data.csv   … format a chart"
echo "   ./omnifuse.sh tone report.md   … generate 3 tones of text"
echo ""
echo " See USER_GUIDE.md for how to configure API keys."
