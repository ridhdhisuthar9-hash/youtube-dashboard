#!/usr/bin/env python3
"""YouTube Video Performance Dashboard - command line entry point.

Examples
--------
Demo data (no API key needed):
    python main.py --demo

A real channel (needs a free YouTube Data API v3 key):
    python main.py --channel @GoogleDevelopers --api-key YOUR_KEY
    python main.py --channel UC_x5XG1OV2P6uZZ5FSM9Ttw --max-videos 30 --theme dark

Re-draw from a CSV saved earlier (works offline):
    python main.py --from-csv output/videos.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib
import pandas as pd

from ytdash import config, demo_data, fetcher, processing


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Visualise views, likes and comments of recent videos.")
    src = p.add_argument_group("data source (pick one; default is demo data)")
    src.add_argument("--demo", action="store_true", help="use built-in sample data")
    src.add_argument("--channel", help="channel ID (UC...), @handle or channel URL")
    src.add_argument("--from-csv", metavar="FILE", help="load a CSV saved by a previous run")
    p.add_argument("--api-key", help="YouTube Data API key (or set YOUTUBE_API_KEY / .env)")
    p.add_argument("--max-videos", type=int, default=20, help="how many recent videos (default 20)")
    p.add_argument("--theme", choices=("light", "dark"), default="light")
    p.add_argument("--out", default="output", help="output folder (default: output)")
    p.add_argument("--show", action="store_true", help="also open the chart in a window")
    return p


def load_data(args: argparse.Namespace) -> tuple[pd.DataFrame, str, str]:
    """Return (raw dataframe, channel title, source label)."""
    if args.from_csv:
        df = pd.read_csv(args.from_csv)
        title = Path(args.from_csv).stem.replace("_", " ").title()
        return processing.to_dataframe(df.to_dict("records")), title, f"CSV file ({args.from_csv})"

    if args.channel and not args.demo:
        api_key = config.get_api_key(args.api_key)
        if not api_key:
            sys.exit(
                "A channel was given but no API key was found.\n"
                "Pass --api-key, set YOUTUBE_API_KEY, or create a .env file (see .env.example).\n"
                "Or run with --demo to try the dashboard on sample data."
            )
        try:
            info = fetcher.resolve_channel(api_key, args.channel)
            videos = fetcher.fetch_recent_videos(api_key, info["uploads_playlist"], args.max_videos)
        except fetcher.YouTubeAPIError as err:
            sys.exit(f"Could not fetch data: {err}")
        return processing.to_dataframe(videos), info["title"], "YouTube Data API v3"

    if not args.demo:
        print("No --channel given, so using demo data. (Use --channel to analyse a real channel.)")
    videos = demo_data.generate_demo_videos(args.max_videos)
    return processing.to_dataframe(videos), demo_data.DEMO_CHANNEL_TITLE, "Demo data (synthetic)"


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.max_videos < 1:
        sys.exit("--max-videos must be at least 1")
    if not args.show:
        matplotlib.use("Agg")  # draw to files only; no window needed

    from ytdash import dashboard, report  # imported after the backend is chosen

    raw, channel_title, source = load_data(args)
    df = processing.add_metrics(raw)
    summary = processing.summarize(df)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "videos.csv"
    png_path = out_dir / "dashboard.png"
    html_path = out_dir / "report.html"

    df.drop(columns=["short_title"]).round(
        {"like_rate": 2, "comment_rate": 2, "engagement_rate": 2}
    ).to_csv(csv_path, index=False)
    dashboard.render_dashboard(df, summary, channel_title, str(png_path), args.theme, source, args.show)
    report.write_report(df, str(png_path), channel_title, str(html_path))

    print(f"Channel : {channel_title}")
    print(f"Videos  : {summary['videos']}   Views: {summary['total_views']:,}   "
          f"Likes: {summary['total_likes']:,}   Comments: {summary['total_comments']:,}")
    print(f"Engagement rate: {summary['engagement_rate']:.2f}%")
    print(f"Best video     : {summary['best_views_title']} ({summary['best_views_count']:,} views)")
    print(f"Saved          : {png_path}, {html_path}, {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
