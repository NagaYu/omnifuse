"""[ChartPurify] Auto-format Excel/CSV into business-quality charts (PDF/PNG).

- Colors: a monochrome palette with a blue accent
- Font: Yu Gothic (falls back automatically to Hiragino Sans, etc. if unavailable)
- Margins, gridlines, and legend are optimized automatically
"""

import logging
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless backend (no GUI required)
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
    logger.warning("None of the candidate fonts were found; using the default font")
    return plt.rcParams["font.family"][0] if plt.rcParams["font.family"] else "sans-serif"


def load_table(input_path: str) -> pd.DataFrame:
    path = Path(input_path)
    if not path.is_file():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    suffix = path.suffix.lower()
    if suffix in (".xlsx", ".xlsm", ".xls"):
        df = pd.read_excel(path)
    elif suffix in (".csv", ".tsv"):
        sep = "\t" if suffix == ".tsv" else ","
        try:
            df = pd.read_csv(path, sep=sep, encoding="utf-8-sig")
        except UnicodeDecodeError:
            df = pd.read_csv(path, sep=sep, encoding="cp932")  # fallback for legacy Shift-JIS from Excel
    else:
        raise ValueError(f"Unsupported file format (CSV/TSV/Excel supported): {suffix}")
    if df.empty:
        raise ValueError("The data is empty. Please provide a file with content.")
    return df


def _split_columns(df: pd.DataFrame) -> tuple[str, list[str]]:
    """Auto-detect the label column (first non-numeric) and the numeric columns."""
    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    label_cols = [c for c in df.columns if c not in numeric_cols]
    if not numeric_cols:
        raise ValueError("No numeric columns to chart were found.")
    label_col = label_cols[0] if label_cols else None
    return label_col, numeric_cols


def purify(
    input_path: str,
    config: dict,
    chart_type: str = "auto",
    title: str | None = None,
) -> list[Path]:
    """Load the data and output formatted charts as PNG/PDF. Returns the generated file paths."""
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
    # First series gets the blue accent; the rest get the monochrome palette
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
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # millisecond precision (avoid overwrites)
    base = f"{Path(input_path).stem}_{stamp}"

    outputs = []
    for fmt in chart_cfg["formats"]:
        out_path = out_dir / f"{base}.{fmt}"
        fig.savefig(out_path, dpi=chart_cfg["dpi"], format=fmt)
        outputs.append(out_path)
        logger.info("Chart written: %s", out_path)
    plt.close(fig)
    return outputs
