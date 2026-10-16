"""The one function the web app needs: channel reference in, everything for a page out.

It also turns technical API failures into short, plain-language messages
(``UserFacingError``) so a non-technical visitor always knows what to do next.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import pandas as pd

from . import demo_data, fetcher, processing
from .processing import fmt_number

MAX_VIDEOS_LIMIT = 50


class UserFacingError(Exception):
    """An error whose ``title`` and ``tip`` are safe and useful to show to any visitor."""

    def __init__(self, title: str, tip: str, status: int = 400):
        super().__init__(title)
        self.title = title
        self.tip = tip
        self.status = status


@dataclass
class DashboardResult:
    channel_title: str
    subscribers: int | None
    source_label: str
    is_demo: bool
    df: pd.DataFrame
    summary: dict
    insights: list[str]
    created: float = field(default_factory=time.time)


# --------------------------------------------------------------------------- errors
def friendly_error(exc: Exception) -> UserFacingError:
    """Translate any failure from the fetch step into a ``UserFacingError``."""
    if isinstance(exc, UserFacingError):
        return exc

    text = str(exc).lower()
    status = getattr(exc, "status", None)

    if isinstance(exc, fetcher.ChannelNotFoundError):
        return UserFacingError(
            "We couldn't find that channel.",
            "Check the spelling. The most reliable input is the channel ID (it starts with UC) "
            "or the @name shown on the channel's YouTube page.",
            404,
        )
    if "playlistnotfound" in text or (isinstance(exc, ValueError) and "no videos" in text):
        return UserFacingError(
            "This channel has no public videos yet.",
            "Try a channel that has uploaded videos, or use the demo data.",
            404,
        )
    if "quota" in text:
        return UserFacingError(
            "The free daily YouTube limit has been used up.",
            "It resets every day (midnight Pacific time). Try again tomorrow, or use the demo data.",
            503,
        )
    if "api key not valid" in text or "keyinvalid" in text or "api_key_invalid" in text:
        return UserFacingError(
            "YouTube did not accept the API key.",
            "Check that the key was copied completely, with no spaces, and that it belongs to a "
            "project where 'YouTube Data API v3' is enabled.",
            502,
        )
    if "has not been used" in text or "is disabled" in text or "accessnotconfigured" in text:
        return UserFacingError(
            "The YouTube Data API is not switched on for this key.",
            "In Google Cloud Console, open 'APIs & Services', search for 'YouTube Data API v3' "
            "and click Enable. It can take a minute to start working.",
            502,
        )
    if "network problem" in text or "timed out" in text:
        return UserFacingError(
            "We couldn't reach YouTube.",
            "Check your internet connection and try again.",
            502,
        )
    if status in (401, 403):
        return UserFacingError(
            "YouTube refused the request.",
            "The API key may be restricted or not allowed to read channel data.",
            502,
        )
    return UserFacingError(
        "Something went wrong while getting the data.",
        "Please try again in a moment. If it keeps happening, try the demo data.",
        502,
    )


# --------------------------------------------------------------------------- insights
def build_insights(df: pd.DataFrame, summary: dict) -> list[str]:
    """A few plain-English observations, computed (never guessed) from the data."""
    notes: list[str] = []

    top = df.loc[df["views"].idxmax()]
    median = summary["median_views"]
    if median > 0 and len(df) > 1:
        notes.append(
            f"Most viewed: “{top['title']}” with {fmt_number(top['views'])} views, "
            f"about {top['views'] / median:.1f}× the typical video ({fmt_number(median)})."
        )
    else:
        notes.append(f"Most viewed: “{top['title']}” with {fmt_number(top['views'])} views.")

    best = df.loc[df["engagement_rate"].idxmax()]
    if best["views"] > 0:
        notes.append(
            f"Most engaging: “{best['title']}”. Its likes and comments add up to "
            f"{best['engagement_rate']:.2f}% of its views (channel average "
            f"{summary['engagement_rate']:.2f}%)."
        )

    if summary["total_comments"] > 0 and summary["total_likes"] > 0:
        per_comment = summary["total_likes"] / summary["total_comments"]
        notes.append(f"On average there is 1 comment for every {per_comment:.0f} likes.")

    if len(df) >= 8:
        half = len(df) // 2
        older = df.head(len(df) - half)["engagement_rate"].mean()
        recent = df.tail(half)["engagement_rate"].mean()
        gap = recent - older
        if abs(gap) < 0.15:
            trend = "about the same as"
        elif gap > 0:
            trend = "higher than"
        else:
            trend = "lower than"
        notes.append(
            f"Engagement on the newest {half} videos ({recent:.2f}%) is {trend} the older "
            f"{len(df) - half} ({older:.2f}%)."
        )

    if len(df) >= 3:
        days = df["published_at"].diff().dt.total_seconds().dropna() / 86400
        if len(days) and days.median() > 0:
            notes.append(f"The channel posts a video about every {days.median():.0f} days.")

    return notes


# --------------------------------------------------------------------------- main entry
def get_dashboard(
    channel_ref: str,
    api_key: str | None,
    max_videos: int = 20,
    demo: bool = False,
) -> DashboardResult:
    """Fetch (or fake, in demo mode) the channel's videos and compute everything a page needs."""
    max_videos = max(1, min(int(max_videos), MAX_VIDEOS_LIMIT))

    if demo:
        videos = demo_data.generate_demo_videos(max_videos)
        title, subscribers = demo_data.DEMO_CHANNEL_TITLE, None
        source = "Demo data (synthetic)"
    else:
        if not channel_ref or not channel_ref.strip():
            raise UserFacingError(
                "Please enter a channel.",
                "Paste a channel ID (starts with UC), an @name, or a link to the channel.",
            )
        if not api_key:
            raise UserFacingError(
                "A YouTube API key is needed for real channels.",
                "Add a free API key (see the steps on this page), or try the demo data.",
                400,
            )
        try:
            info = fetcher.resolve_channel(api_key, channel_ref)
            videos = fetcher.fetch_recent_videos(api_key, info["uploads_playlist"], max_videos)
            if not videos:
                raise ValueError("No videos to analyse.")
        except Exception as exc:  # noqa: BLE001 - every failure becomes a friendly message
            raise friendly_error(exc) from None
        title, subscribers = info["title"], info["subscribers"]
        source = "YouTube Data API v3"

    df = processing.add_metrics(processing.to_dataframe(videos))
    summary = processing.summarize(df)
    return DashboardResult(
        channel_title=title,
        subscribers=subscribers,
        source_label=source,
        is_demo=demo,
        df=df,
        summary=summary,
        insights=build_insights(df, summary),
    )
