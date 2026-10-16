"""Turn raw video records into a clean pandas DataFrame and compute the dashboard metrics."""

from __future__ import annotations

import numpy as np
import pandas as pd

COUNT_COLUMNS = ["views", "likes", "comments", "duration_sec"]
REQUIRED_COLUMNS = ["video_id", "title", "published_at", *COUNT_COLUMNS]


def to_dataframe(videos: list[dict]) -> pd.DataFrame:
    """Build a tidy DataFrame, oldest video first (so charts read left -> right in time)."""
    if not videos:
        raise ValueError("No videos to analyse.")
    df = pd.DataFrame(videos)
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {', '.join(missing)}")

    df["published_at"] = pd.to_datetime(df["published_at"], utc=True)
    for col in COUNT_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype("int64")
    df["title"] = df["title"].astype(str)
    return df.sort_values("published_at").reset_index(drop=True)


def fmt_number(value: float) -> str:
    """12345 -> '12.3K', 2500000 -> '2.5M'."""
    value = float(value)
    for divisor, suffix in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if abs(value) >= divisor:
            text = f"{value / divisor:.1f}"
            return (text[:-2] if text.endswith(".0") else text) + suffix
    return f"{value:,.0f}"


def short_title(title: str, limit: int = 28) -> str:
    """Shorten long titles for chart labels."""
    title = title.strip()
    return title if len(title) <= limit else title[: limit - 1].rstrip() + "…"


def add_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Add per-video rates (all in percent of views).

    * like_rate        = likes / views * 100
    * comment_rate     = comments / views * 100
    * engagement_rate  = (likes + comments) / views * 100

    A video with 0 views gets 0 rates instead of a division-by-zero error.
    """
    out = df.copy()
    safe_views = out["views"].replace(0, np.nan)
    out["like_rate"] = (out["likes"] / safe_views * 100).fillna(0.0)
    out["comment_rate"] = (out["comments"] / safe_views * 100).fillna(0.0)
    out["engagement_rate"] = ((out["likes"] + out["comments"]) / safe_views * 100).fillna(0.0)
    out["short_title"] = out["title"].map(short_title)
    return out


def summarize(df: pd.DataFrame) -> dict:
    """Headline numbers for the KPI tiles."""
    total_views = int(df["views"].sum())
    total_likes = int(df["likes"].sum())
    total_comments = int(df["comments"].sum())
    # weighted average (total likes+comments over total views), not the mean of per-video rates
    overall_engagement = (total_likes + total_comments) / total_views * 100 if total_views else 0.0

    best_views = df.loc[df["views"].idxmax()]
    best_engagement = df.loc[df["engagement_rate"].idxmax()]
    return {
        "videos": int(len(df)),
        "first_date": df["published_at"].min(),
        "last_date": df["published_at"].max(),
        "total_views": total_views,
        "total_likes": total_likes,
        "total_comments": total_comments,
        "median_views": float(df["views"].median()),
        "like_rate": total_likes / total_views * 100 if total_views else 0.0,
        "comment_rate": total_comments / total_views * 100 if total_views else 0.0,
        "engagement_rate": overall_engagement,
        "best_views_title": best_views["title"],
        "best_views_count": int(best_views["views"]),
        "best_engagement_title": best_engagement["title"],
        "best_engagement_rate": float(best_engagement["engagement_rate"]),
    }


def top_n(df: pd.DataFrame, metric: str, n: int = 5) -> pd.DataFrame:
    """Return the ``n`` best videos for a metric (highest first)."""
    if metric not in df.columns:
        raise KeyError(f"Unknown metric: {metric}")
    return df.nlargest(n, metric).reset_index(drop=True)
