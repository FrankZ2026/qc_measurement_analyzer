from __future__ import annotations

import io
import os
import tempfile

os.environ.setdefault("MPLCONFIGDIR", os.path.join(tempfile.gettempdir(), "qc_measurement_matplotlib"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats


def _clean(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").dropna()


def _empty_figure(title: str, message: str):
    fig, ax = plt.subplots(figsize=(7, 4), constrained_layout=True)
    ax.set_title(title)
    ax.text(0.5, 0.5, message, ha="center", va="center", transform=ax.transAxes)
    ax.set_axis_off()
    return fig


def histogram_with_normal_curve(series: pd.Series, item_name: str, lsl=None, usl=None):
    data = _clean(series)
    if data.empty:
        return _empty_figure(f"Histogram - {item_name}", "No numeric data")

    fig, ax = plt.subplots(figsize=(7.2, 4.3), constrained_layout=True)
    bins = min(max(int(np.sqrt(len(data))), 8), 40)
    ax.hist(data, bins=bins, density=True, alpha=0.72, color="#4C78A8", edgecolor="white", label="Data")

    mean = data.mean()
    std = data.std(ddof=1) if len(data) >= 2 else np.nan
    if np.isfinite(std) and std > 0:
        limits = [data.min(), data.max()]
        if lsl is not None:
            limits.append(float(lsl))
        if usl is not None:
            limits.append(float(usl))
        x = np.linspace(min(limits), max(limits), 300)
        ax.plot(x, stats.norm.pdf(x, mean, std), color="#F58518", linewidth=2, label="Normal Curve")

    ax.axvline(mean, color="#111827", linestyle="--", linewidth=1.6, label=f"Mean = {mean:.4f}")
    if lsl is not None:
        ax.axvline(float(lsl), color="#D62728", linestyle="-.", linewidth=1.5, label="LSL")
    if usl is not None:
        ax.axvline(float(usl), color="#D62728", linestyle="-.", linewidth=1.5, label="USL")

    ax.set_title(f"Histogram with Normal Curve - {item_name}")
    ax.set_xlabel("Measurement Value")
    ax.set_ylabel("Density")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8)
    return fig


def box_plot(series: pd.Series, item_name: str):
    data = _clean(series)
    if data.empty:
        return _empty_figure(f"Box Plot - {item_name}", "No numeric data")

    fig, ax = plt.subplots(figsize=(5.5, 3.7), constrained_layout=True)
    ax.boxplot(data, vert=False, patch_artist=True, boxprops={"facecolor": "#72B7B2", "color": "#1F2937"})
    ax.set_title(f"Box Plot - {item_name}")
    ax.set_xlabel("Measurement Value")
    ax.grid(axis="x", alpha=0.25)
    return fig


def qq_plot(series: pd.Series, item_name: str):
    data = _clean(series)
    if len(data) < 3:
        return _empty_figure(f"Q-Q Plot - {item_name}", "At least 3 numeric values are required")

    fig, ax = plt.subplots(figsize=(5.5, 4.2), constrained_layout=True)
    stats.probplot(data, dist="norm", plot=ax)
    ax.get_lines()[0].set_markerfacecolor("#4C78A8")
    ax.get_lines()[0].set_markeredgecolor("#4C78A8")
    ax.get_lines()[1].set_color("#D62728")
    ax.set_title(f"Q-Q Plot - {item_name}")
    ax.grid(alpha=0.25)
    return fig


def fig_to_png_bytes(fig) -> bytes:
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=160, bbox_inches="tight")
    plt.close(fig)
    return buffer.getvalue()
