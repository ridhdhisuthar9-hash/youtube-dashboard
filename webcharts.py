"""Charts for the web page.

Each panel is drawn as its own small SVG (crisp at any size) and served from its own URL.
Every chart exists in two sizes: a desktop one and a phone one. The phone one is drawn narrower,
with fewer date labels and shorter titles, so its text stays readable on a small screen
instead of being a shrunken copy of the desktop chart.

We reuse the panel functions from ``dashboard.py`` so the web charts and the PNG dashboard
always look the same. matplotlib's pyplot is not thread-safe and the web server handles
requests in threads, so all drawing happens under ``RENDER_LOCK``.
"""

from __future__ import annotations

import io
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # no window; must be chosen before anything draws

from matplotlib.figure import Figure  # noqa: E402

from . import dashboard  # noqa: E402
from .processing import fmt_number  # noqa: E402

RENDER_LOCK = threading.RLock()
THEME = dashboard.THEMES["light"]
_RC = {
    "font.family": "sans-serif",
    "font.sans-serif": dashboard.FONT,
    "svg.fonttype": "path",  # text becomes shapes: looks identical on every computer
}

# key -> (title, full-width on desktop?, desktop size (in), phone size (in))
SPECS = {
    "views": ("Views per video", True, (10.0, 3.2), (4.0, 3.0)),
    "likes": ("Likes per video", False, (5.4, 3.1), (4.0, 2.9)),
    "comments": ("Comments per video", False, (5.4, 3.1), (4.0, 2.9)),
    "engaging": ("Most engaging videos", False, (5.4, 4.4), (4.0, 4.6)),
    "scatter": ("Views and likes", False, (5.4, 4.4), (4.0, 4.1)),
    "trend": ("Engagement over time", True, (10.0, 3.4), (4.0, 3.1)),
}
VARIANTS = ("d", "m")  # desktop, mobile


@dataclass
class ChartMeta:
    key: str
    title: str
    alt: str
    wide: bool


def chart_meta(df) -> list[ChartMeta]:
    """Cheap description of every chart (title and a text alternative); nothing is drawn yet."""
    metas = []
    for key, (title, wide, _d, _m) in SPECS.items():
        if key in ("views", "likes", "comments"):
            top = df.loc[df[key].idxmax()]
            alt = (
                f"Bar chart of {key} for each of the last {len(df)} videos, oldest to newest. "
                f"The highest is {fmt_number(top[key])} for “{top['title']}”; "
                f"the median is {fmt_number(df[key].median())}."
            )
        elif key == "engaging":
            best = df.loc[df["engagement_rate"].idxmax()]
            alt = (
                f"Ranked bar chart of the most engaging videos. First place is "
                f"“{best['title']}” at {best['engagement_rate']:.2f}% "
                "(likes plus comments divided by views)."
            )
        elif key == "scatter":
            alt = (
                "Bubble chart with views on the horizontal axis and likes on the vertical axis. "
                "Each bubble is one video and a bigger bubble means more comments."
            )
        else:
            alt = (
                "Line chart of engagement rate for each video from oldest to newest. "
                f"The median is {df['engagement_rate'].median():.2f}%."
            )
        metas.append(ChartMeta(key, title, alt, wide))
    return metas


def render_chart(df, key: str, variant: str = "d") -> bytes:
    """Draw one chart and return it as SVG bytes. ``variant`` is "d" (desktop) or "m" (phone)."""
    if key not in SPECS or variant not in VARIANTS:
        raise KeyError(f"unknown chart {key!r}/{variant!r}")
    title, _wide, desktop, phone = SPECS[key]
    mobile = variant == "m"
    width, height = phone if mobile else desktop
    t = THEME

    with RENDER_LOCK, matplotlib.rc_context(_RC):
        fig = Figure(figsize=(width, height), facecolor=t["surface"], layout="constrained")
        ax = fig.add_subplot(111)
        if key in ("views", "likes", "comments"):
            dashboard._small_multiple(
                ax, df, key, title, t[key], t, True, dashboard._date_labels(df),
                max_ticks=6 if mobile else 12,
            )
        elif key == "engaging":
            dashboard._engagement_bars(ax, df, t, label_chars=30 if mobile else 46)
        elif key == "scatter":
            dashboard._scatter(ax, df, t)
        else:
            dashboard._engagement_trend(ax, df, t, max_ticks=6 if mobile else 12)
        buf = io.BytesIO()
        fig.savefig(buf, format="svg", bbox_inches="tight", pad_inches=0.12,
                    facecolor=fig.get_facecolor())
        return buf.getvalue()


def render_png(result) -> bytes:
    """The full single-image dashboard (same one the command-line tool saves)."""
    with RENDER_LOCK, tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "dashboard.png"
        dashboard.render_dashboard(
            result.df, result.summary, result.channel_title, str(out), "light", result.source_label
        )
        return out.read_bytes()
