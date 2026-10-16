"""Optional HTML report: the dashboard image plus a sortable-looking data table."""

from __future__ import annotations

import base64
from datetime import datetime
from html import escape
from pathlib import Path

import pandas as pd

_STYLE = """
body{font-family:system-ui,-apple-system,"Segoe UI",sans-serif;margin:0;background:#f9f9f7;color:#0b0b0b}
main{max-width:1180px;margin:0 auto;padding:24px 16px 48px}
h1{margin:0 0 4px;font-size:24px} p.sub{margin:0 0 20px;color:#52514e}
img{width:100%;height:auto;border:1px solid #e1e0d9;border-radius:10px;background:#fcfcfb}
h2{margin:32px 0 10px;font-size:17px}
table{width:100%;border-collapse:collapse;background:#fcfcfb;border:1px solid #e1e0d9;font-size:13px}
th,td{padding:8px 10px;border-bottom:1px solid #e1e0d9;text-align:right}
th{background:#f0efec;color:#52514e;font-weight:600}
th:first-child,td:first-child,th:nth-child(2),td:nth-child(2){text-align:left}
"""


def write_report(df: pd.DataFrame, image_path: str, channel_title: str, out_path: str) -> str:
    """Write a self-contained HTML file (the PNG is embedded, so it can be shared alone)."""
    image_b64 = base64.b64encode(Path(image_path).read_bytes()).decode("ascii")
    rows = []
    for _, r in df.sort_values("published_at", ascending=False).iterrows():
        rows.append(
            "<tr>"
            f"<td>{r['published_at']:%d %b %Y}</td>"
            f"<td>{escape(r['title'])}</td>"
            f"<td>{r['views']:,}</td><td>{r['likes']:,}</td><td>{r['comments']:,}</td>"
            f"<td>{r['engagement_rate']:.2f}%</td>"
            "</tr>"
        )
    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(channel_title)} - Video Performance</title><style>{_STYLE}</style></head>
<body><main>
<h1>{escape(channel_title)}</h1>
<p class="sub">YouTube video performance dashboard · generated {datetime.now():%d %b %Y}</p>
<img alt="Dashboard with KPI tiles, views, likes and comments per video, engagement charts" src="data:image/png;base64,{image_b64}">
<h2>Data table</h2>
<table><thead><tr><th>Published</th><th>Title</th><th>Views</th><th>Likes</th><th>Comments</th><th>Engagement</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>
</main></body></html>"""
    Path(out_path).write_text(html, encoding="utf-8")
    return out_path
