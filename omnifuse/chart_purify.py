"""[ChartPurify] Excel/CSV をビジネス品質のグラフ (PDF/PNG) に自動整形する。

- 配色: モノトーン + 青のアクセント
- フォント: 游ゴシック（無ければ Hiragino Sans 等へ自動フォールバック)
- 余白・グリッド・凡例を自動で最適化
"""

import logging
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # GUI不要のバックエンド
import matplotlib.pyplot as plt
from matplotlib import font_manager

import pandas as pd

from .config import ensure_output_dir

logger = logging.getLogger("omnifuse")


def _resolve_font(candidates: list[str]) -> str:
    installed = {f.name for f in font_manager.fontManager.ttflist}
    for name in candidates:
        if name in installed:
            return name
    logger.warning("候補フォントが見つからないため既定フォントで描画します")
    return plt.rcParams["font.family"][0] if plt.rcParams["font.family"] else "sans-serif"


def load_table(input_path: str) -> pd.DataFrame:
    path = Path(input_path)
    if not path.is_file():
        raise FileNotFoundError(f"入力ファイルが見つかりません: {input_path}")
    suffix = path.suffix.lower()
    if suffix in (".xlsx", ".xlsm", ".xls"):
        df = pd.read_excel(path)
    elif suffix in (".csv", ".tsv"):
        sep = "\t" if suffix == ".tsv" else ","
        try:
            df = pd.read_csv(path, sep=sep, encoding="utf-8-sig")
        except UnicodeDecodeError:
            df = pd.read_csv(path, sep=sep, encoding="cp932")  # Excel由来のShift-JIS対策
    else:
        raise ValueError(f"未対応のファイル形式です（CSV/TSV/Excelに対応）: {suffix}")
    if df.empty:
        raise ValueError("データが空です。中身のあるファイルを指定してください。")
    return df


def _split_columns(df: pd.DataFrame) -> tuple[str, list[str]]:
    """ラベル列（最初の非数値列）と数値列を自動判定する。"""
    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    label_cols = [c for c in df.columns if c not in numeric_cols]
    if not numeric_cols:
        raise ValueError("グラフ化できる数値列が見つかりません。")
    label_col = label_cols[0] if label_cols else None
    return label_col, numeric_cols


def purify(
    input_path: str,
    config: dict,
    chart_type: str = "auto",
    title: str | None = None,
) -> list[Path]:
    """データを読み込み、整形済みグラフをPNG/PDFで出力する。生成ファイルのパスを返す。"""
    chart_cfg = config["chart"]
    df = load_table(input_path)
    label_col, numeric_cols = _split_columns(df)
    labels = df[label_col].astype(str) if label_col else df.index.astype(str)

    if chart_type == "auto":
        chart_type = "line" if len(df) > 12 else "bar"

    font_name = _resolve_font(chart_cfg["font_candidates"])
    plt.rcParams.update({
        "font.family": font_name,
        "axes.unicode_minus": False,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "axes.edgecolor": "#D1D5DB",
        "axes.linewidth": 0.8,
        "axes.grid": True,
        "grid.color": "#E5E7EB",
        "grid.linewidth": 0.6,
        "xtick.color": "#374151",
        "ytick.color": "#374151",
        "text.color": "#111827",
        "axes.labelcolor": "#374151",
    })

    accent = chart_cfg["accent_color"]
    monos = chart_cfg["mono_colors"]
    # 先頭の系列を青のアクセント、以降をモノトーンに
    colors = [accent] + [monos[i % len(monos)] for i in range(len(numeric_cols) - 1)]

    fig, ax = plt.subplots(figsize=(10, 5.6))

    if chart_type == "bar":
        n = len(numeric_cols)
        width = 0.8 / n
        x = range(len(df))
        for i, col in enumerate(numeric_cols):
            offset = (i - (n - 1) / 2) * width
            ax.bar([xi + offset for xi in x], df[col], width=width * 0.92,
                   label=str(col), color=colors[i], edgecolor="none")
        ax.set_xticks(list(x))
        ax.set_xticklabels(labels, rotation=0 if labels.str.len().max() <= 6 else 30,
                           ha="center" if labels.str.len().max() <= 6 else "right")
        ax.grid(axis="x", visible=False)
    else:
        for i, col in enumerate(numeric_cols):
            ax.plot(labels, df[col], label=str(col), color=colors[i],
                    linewidth=2.4 if i == 0 else 1.6,
                    marker="o", markersize=4.5 if i == 0 else 3.5)
        if len(df) > 15:
            step = max(1, len(df) // 12)
            ax.set_xticks(range(0, len(df), step))
        plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
        ax.grid(axis="x", visible=False)

    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)

    ax.set_title(title or Path(input_path).stem, fontsize=15, fontweight="bold",
                 pad=18, loc="left")
    if len(numeric_cols) > 1:
        ax.legend(frameon=False, loc="upper left", bbox_to_anchor=(0, -0.12),
                  ncol=min(len(numeric_cols), 4), fontsize=10)
    fig.subplots_adjust(left=0.09, right=0.97, top=0.88,
                        bottom=0.22 if len(numeric_cols) > 1 else 0.14)

    out_dir = ensure_output_dir(config) / "charts"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # ミリ秒まで（上書き防止）
    base = f"{Path(input_path).stem}_{stamp}"

    outputs = []
    for fmt in chart_cfg["formats"]:
        out_path = out_dir / f"{base}.{fmt}"
        fig.savefig(out_path, dpi=chart_cfg["dpi"], format=fmt)
        outputs.append(out_path)
        logger.info("グラフを出力しました: %s", out_path)
    plt.close(fig)
    return outputs
