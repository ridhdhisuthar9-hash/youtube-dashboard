"""Build the multi-metric dashboard image with matplotlib.

Design choices (so you can explain them in your viva):

* Views, likes and comments live on very different scales (e.g. 40,000 vs 1,500 vs 120).
  Putting them on one y-axis hides the small ones, and a dual-axis chart is misleading.
  So each metric gets its OWN small chart ("small multiples") that shares the time axis.
* One colour per metric, used consistently on every chart: views = blue, likes = orange,
  comments = teal, engagement rate = amber.
* KPI tiles on top give the headline numbers; the scatter shows how views relate to
  likes; the bar + line show which videos engage best and how engagement changes over time.
* Light and dark themes are both available (``--theme dark``).
"""

from __future__ import annotations

from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyBboxPatch
from matplotlib.ticker import FuncFormatter

from .processing import fmt_number  # noqa: F401  (re-exported: dashboard.fmt_number)

THEMES = {
    "light": {
        "surface": "#fcfcfb",
        "primary": "#0b0b0b",
        "secondary": "#52514e",
        "muted": "#898781",
        "grid": "#e1e0d9",
        "baseline": "#c3c2b7",
        "views": "#2a78d6",
        "likes": "#eb6834",
        "comments": "#1baf7a",
        "engagement": "#eda100",
    },
    "dark": {
        "surface": "#1a1a19",
        "primary": "#f0efec",
        "secondary": "#c3c2b7",
        "muted": "#898781",
        "grid": "#2c2c2a",
        "baseline": "#383835",
        "views": "#3987e5",
        "likes": "#d95926",
        "comments": "#199e70",
        "engagement": "#c98500",
    },
}

FONT = ["Inter", "Segoe UI", "DejaVu Sans", "Arial"]


# --------------------------------------------------------------------------- helpers
def _axis_formatter() -> FuncFormatter:
    return FuncFormatter(lambda v, _pos: fmt_number(v))


def _style_axis(ax, t: dict, grid_axis: str = "y") -> None:
    ax.set_facecolor(t["surface"])
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(t["baseline"])
    ax.tick_params(colors=t["muted"], labelcolor=t["secondary"], labelsize=8, length=0)
    ax.grid(axis=grid_axis, color=t["grid"], linewidth=0.8)
    ax.set_axisbelow(True)


def _panel_title(ax, title: str, subtitle: str, t: dict) -> None:
    ax.set_title(title, loc="left", fontsize=10.5, fontweight="bold", color=t["primary"], pad=20)
    ax.annotate(
        subtitle, xy=(0, 1), xycoords="axes fraction", xytext=(0, 6), textcoords="offset points",
        fontsize=8, color=t["secondary"], va="bottom", ha="left",
    )


def _median_note(ax, text: str, t: dict) -> None:
    """Small note above the top-right of a panel explaining the dashed median line."""
    ax.annotate(
        f"- - -  {text}", xy=(1, 1), xycoords="axes fraction", xytext=(0, 5),
        textcoords="offset points", fontsize=8, color=t["secondary"], va="bottom", ha="right",
    )


def _date_labels(df: pd.DataFrame) -> list[str]:
    return [d.strftime("%d %b") for d in df["published_at"]]


def _tick_step(n: int, target: int = 12) -> int:
    return max(1, int(np.ceil(n / target)))


def _kpi_tile(ax, t: dict, label: str, value: str, detail: str) -> None:
    ax.set_axis_off()
    ax.add_patch(
        FancyBboxPatch(
            (0, 0), 1, 1,
            boxstyle="round,pad=0,rounding_size=0.06",
            transform=ax.transAxes,
            facecolor=t["surface"],
            edgecolor=t["grid"],
            linewidth=1.2,
            clip_on=False,
        )
    )
    ax.text(0.07, 0.78, label, transform=ax.transAxes, fontsize=9.5, color=t["secondary"])
    ax.text(0.07, 0.36, value, transform=ax.transAxes, fontsize=24, fontweight="bold",
            color=t["primary"])
    ax.text(0.07, 0.10, detail, transform=ax.transAxes, fontsize=8, color=t["secondary"])


# --------------------------------------------------------------------------- panels
def _small_multiple(ax, df, column, label, color, t, show_dates, dates, max_ticks=12) -> None:
    x = np.arange(len(df))
    values = df[column].to_numpy()
    ax.bar(x, values, width=0.62, color=color, zorder=2)
    _style_axis(ax, t)
    ax.yaxis.set_major_formatter(_axis_formatter())
    ax.set_ylim(0, max(values.max(), 1) * 1.25)
    ax.set_xlim(-0.7, len(df) - 0.3)

    median = float(np.median(values))
    ax.axhline(median, color=t["muted"], linewidth=1, linestyle=(0, (4, 3)), zorder=3)
    _median_note(ax, f"median {fmt_number(median)}", t)

    # direct label on the best video only (never a number on every bar)
    best = int(values.argmax())
    ax.annotate(
        fmt_number(values[best]), (best, values[best]), xytext=(0, 3),
        textcoords="offset points", ha="center", fontsize=8.5, fontweight="bold",
        color=t["primary"],
    )

    step = _tick_step(len(df), max_ticks)
    ax.set_xticks(x[::step])
    if show_dates:
        ax.set_xticklabels([dates[i] for i in x[::step]], rotation=35, ha="right")
    else:
        ax.tick_params(axis="x", labelbottom=False)
    ax.set_title(label, loc="left", fontsize=10.5, fontweight="bold", color=t["primary"], pad=8)


def _engagement_bars(ax, df, t, label_chars=46) -> None:
    top = df.nlargest(8, "engagement_rate").sort_values("engagement_rate")
    y = np.arange(len(top))
    ax.barh(y, top["engagement_rate"], height=0.36, color=t["engagement"], zorder=2)
    _style_axis(ax, t, grid_axis="x")
    ax.set_yticks([])  # titles are written above each bar instead (long titles need room)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _p: f"{v:g}%"))
    ax.set_xlim(0, top["engagement_rate"].max() * 1.15)
    ax.set_ylim(-0.4, len(top) - 0.35)
    for yi, title, rate in zip(y, top["title"], top["engagement_rate"]):
        label = title if len(title) <= label_chars else title[: label_chars - 1].rstrip() + "…"
        ax.text(0, yi + 0.22, label, va="bottom", fontsize=8.5, color=t["primary"])
        ax.text(rate, yi, f"  {rate:.2f}%", va="center", fontsize=8.5, fontweight="bold",
                color=t["primary"])
    _panel_title(ax, "Most engaging videos", "Engagement = (likes + comments) ÷ views", t)


def _scatter(ax, df, t) -> None:
    sizes = 40 + 520 * df["comments"] / max(df["comments"].max(), 1)
    ax.scatter(
        df["views"], df["likes"], s=sizes, color=t["views"], alpha=0.85,
        edgecolor=t["surface"], linewidth=1.5, zorder=3,
    )
    _style_axis(ax, t, grid_axis="both")
    ax.xaxis.set_major_formatter(_axis_formatter())
    ax.yaxis.set_major_formatter(_axis_formatter())
    ax.set_xlabel("Views", fontsize=8.5, color=t["secondary"])
    ax.set_ylabel("Likes", fontsize=8.5, color=t["secondary"])
    ax.set_xlim(0, max(df["views"].max(), 1) * 1.08)
    ax.set_ylim(bottom=0, top=max(df["likes"].max(), 1) * 1.15)
    right_edge = df["views"].max() * 0.7
    for _, row in df.nlargest(2, "views").iterrows():
        near_right = row["views"] > right_edge
        ax.annotate(
            row["short_title"], (row["views"], row["likes"]),
            xytext=(-14, 4) if near_right else (12, 4), textcoords="offset points",
            ha="right" if near_right else "left", fontsize=8, color=t["primary"],
        )
    _panel_title(ax, "Do more views mean more likes?", "Each bubble is a video; bigger = more comments", t)


def _engagement_trend(ax, df, t, max_ticks=12) -> None:
    x = np.arange(len(df))
    ax.plot(x, df["engagement_rate"], color=t["engagement"], linewidth=2, marker="o",
            markersize=6, markeredgecolor=t["surface"], markeredgewidth=1.5, zorder=3)
    _style_axis(ax, t)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _p: f"{v:g}%"))
    ax.set_ylim(0, df["engagement_rate"].max() * 1.3)
    median = float(df["engagement_rate"].median())
    ax.axhline(median, color=t["muted"], linewidth=1, linestyle=(0, (4, 3)), zorder=2)
    _median_note(ax, f"median {median:.2f}%", t)
    last = len(df) - 1
    ax.annotate(f"{df['engagement_rate'].iloc[last]:.2f}%", (last, df["engagement_rate"].iloc[last]),
                xytext=(0, 9), textcoords="offset points", ha="center", fontsize=8.5,
                fontweight="bold", color=t["primary"])
    dates = _date_labels(df)
    step = _tick_step(len(df), max_ticks)
    ax.set_xticks(x[::step])
    ax.set_xticklabels([dates[i] for i in x[::step]], rotation=35, ha="right")
    _panel_title(ax, "Is engagement improving?", "Engagement rate per video, oldest to newest", t)


# --------------------------------------------------------------------------- main entry
def render_dashboard(
    df: pd.DataFrame,
    summary: dict,
    channel_title: str,
    out_path: str,
    theme: str = "light",
    source_label: str = "YouTube Data API",
    show: bool = False,
) -> str:
    """Draw the whole dashboard and save it as a PNG. Returns the output path."""
    t = THEMES[theme]
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["font.sans-serif"] = FONT

    fig = plt.figure(figsize=(16, 12.5), facecolor=t["surface"])
    outer = fig.add_gridspec(
        3, 6, height_ratios=[0.85, 4.7, 3.5],
        left=0.05, right=0.97, top=0.885, bottom=0.075, hspace=0.45, wspace=0.75,
    )

    # --- header
    fig.text(0.05, 0.955, channel_title, fontsize=21, fontweight="bold", color=t["primary"])
    first = summary["first_date"].strftime("%d %b %Y")
    last = summary["last_date"].strftime("%d %b %Y")
    fig.text(
        0.05, 0.925,
        f"YouTube video performance  ·  last {summary['videos']} videos  ·  {first} – {last}",
        fontsize=10.5, color=t["secondary"],
    )

    # --- KPI tiles
    tiles = outer[0, :].subgridspec(1, 4, wspace=0.07)
    _kpi_tile(fig.add_subplot(tiles[0]), t, "Total views", fmt_number(summary["total_views"]),
              f"median {fmt_number(summary['median_views'])} per video")
    _kpi_tile(fig.add_subplot(tiles[1]), t, "Total likes", fmt_number(summary["total_likes"]),
              f"{summary['like_rate']:.2f}% of views")
    _kpi_tile(fig.add_subplot(tiles[2]), t, "Total comments", fmt_number(summary["total_comments"]),
              f"{summary['comment_rate']:.2f}% of views")
    _kpi_tile(fig.add_subplot(tiles[3]), t, "Engagement rate", f"{summary['engagement_rate']:.2f}%",
              "(likes + comments) ÷ views")

    # --- three stacked small multiples (shared time axis, separate y-scales)
    inner = outer[1, 0:3].subgridspec(3, 1, hspace=0.75)
    dates = _date_labels(df)
    axes = [fig.add_subplot(inner[i]) for i in range(3)]
    for i, (col, label) in enumerate(
        [("views", "Views per video"), ("likes", "Likes per video"), ("comments", "Comments per video")]
    ):
        _small_multiple(axes[i], df, col, label, t[col], t, show_dates=(i == 2), dates=dates)

    # --- right column + bottom row
    _engagement_bars(fig.add_subplot(outer[1, 3:6]), df, t)
    _scatter(fig.add_subplot(outer[2, 0:3]), df, t)
    _engagement_trend(fig.add_subplot(outer[2, 3:6]), df, t)

    fig.text(0.97, 0.018, f"Source: {source_label}  ·  generated {datetime.now():%d %b %Y}",
             ha="right", fontsize=8, color=t["muted"])
    fig.text(0.05, 0.018, f"Top video: {summary['best_views_title']} "
             f"({fmt_number(summary['best_views_count'])} views)",
             ha="left", fontsize=8, color=t["muted"])

    fig.savefig(out_path, dpi=150, facecolor=fig.get_facecolor())
    if show:
        plt.show()
    plt.close(fig)
    return out_path
