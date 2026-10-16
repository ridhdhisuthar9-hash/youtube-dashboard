"""Synthetic channel data so the project runs without an API key.

The numbers are random but *realistic*: view counts are log-normal (a few videos do
much better than the rest), likes are roughly 2-6 % of views and comments roughly
0.1-0.5 % of views. A fixed seed makes the output reproducible.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np

DEMO_CHANNEL_TITLE = "Code & Circuits (demo channel)"

_TITLES = [
    "Blink an LED with Arduino in 5 minutes",
    "Python for Beginners: Variables and Loops",
    "How a transistor really works",
    "Build a Digital Clock with 7-Segment Display",
    "ARM Cortex-M explained simply",
    "Pandas in 10 minutes",
    "VLSI Basics: What is CMOS?",
    "Top 5 Mini Projects for ECE Students",
    "Matplotlib Dashboard Tutorial",
    "UART vs SPI vs I2C",
    "LPC2148 Getting Started Guide",
    "Sensors & Transducers Revision",
    "Python File Handling Made Easy",
    "Op-Amp Circuits You Must Know",
    "GTU Exam Prep: Study Plan That Works",
    "Build a Weather Station with Raspberry Pi",
    "Data Structures in Python: Lists vs Tuples",
    "PCB Design for Absolute Beginners",
    "Intro to Embedded C",
    "Thermocouple vs RTD vs Thermistor",
    "Web Scraping with Python",
    "Internship Tips for Engineering Students",
    "Object Oriented Programming in Python",
    "Digital Electronics: Flip-Flops Explained",
    "IoT Home Automation Project",
    "Linux Commands Every Student Needs",
    "Resume Tips for Fresh Graduates",
    "Soldering Tutorial: Do's and Don'ts",
    "Machine Learning in 15 Minutes",
    "Q&A: Your Engineering Questions Answered",
]


def generate_demo_videos(n: int = 20, seed: int = 42) -> list[dict]:
    """Return ``n`` fake video records in the same shape the real API fetcher returns."""
    rng = np.random.default_rng(seed)
    n = max(1, min(n, len(_TITLES)))

    today = datetime.now(timezone.utc).replace(hour=12, minute=0, second=0, microsecond=0)
    # one upload every 3-8 days, newest first
    gaps = rng.integers(3, 9, size=n)
    ages = np.cumsum(gaps)

    base_views = rng.lognormal(mean=9.6, sigma=0.75, size=n)  # median ~15k views
    viral_index = int(rng.integers(0, n))
    base_views[viral_index] *= 4.5  # one breakout video

    videos = []
    for i in range(n):
        views = int(base_views[i])
        like_rate = rng.uniform(0.02, 0.06)
        comment_rate = rng.uniform(0.001, 0.005)
        published = today - timedelta(days=int(ages[i]))
        videos.append(
            {
                "video_id": f"demo{i:03d}",
                "title": _TITLES[i],
                "published_at": published.isoformat(),
                "views": views,
                "likes": int(views * like_rate),
                "comments": int(views * comment_rate),
                "duration_sec": int(rng.integers(240, 1500)),
            }
        )
    return videos
