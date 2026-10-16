"""HTML for the web app. Plain Python string building, no template library needed.

Every piece of text that comes from outside (channel names, video titles, what the visitor
typed) goes through ``esc()`` before it is put in the page.
"""

from __future__ import annotations

import re
from datetime import datetime
from html import escape

from .processing import fmt_number

_VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
VIDEO_COUNT_CHOICES = (10, 20, 30, 50)

CSS = """
:root{
  --bg:#f6f5f2; --surface:#ffffff; --ink:#15171a; --ink-2:#464a50; --ink-3:#656970;
  --line:#e3e1db; --soft:#efede7; --btn:#15171a; --btn-ink:#ffffff; --focus:#2a78d6;
  --err-bg:#fdecea; --err-ink:#8a1f17; --err-line:#f1b9b2;
  --views:#2a78d6; --likes:#eb6834; --comments:#1baf7a; --eng:#eda100;
  color-scheme:light;
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);
  font:16px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif}
.wrap{max-width:1120px;margin:0 auto;padding-inline:max(16px,env(safe-area-inset-left,0px))}
.top{border-bottom:1px solid var(--line);background:var(--surface)}
.top .wrap{display:flex;align-items:baseline;gap:14px;flex-wrap:wrap;padding-block:14px}
.brand{font-weight:700;font-size:18px;color:var(--ink);text-decoration:none;letter-spacing:-.01em}
.tag{color:var(--ink-3);font-size:14px}
main{padding-block:28px 56px}
h1{font-size:clamp(26px,4.4vw,38px);line-height:1.15;margin:0 0 10px;letter-spacing:-.02em;text-wrap:balance}
h2{font-size:18px;margin:34px 0 12px;letter-spacing:-.005em}
p{margin:0 0 12px}
.lead{font-size:18px;color:var(--ink-2);max-width:60ch}
.muted{color:var(--ink-3)}
a{color:#1d5fb3}
.card{background:var(--surface);border:1px solid var(--line);border-radius:10px}
.finder{padding:20px;max-width:680px;margin-top:22px}
.finder label{display:block;font-weight:600;margin-bottom:6px}
.finder input[type=text],.finder input[type=password],.finder select{
  width:100%;font:inherit;padding:12px 13px;border:1px solid #b9b6ad;border-radius:8px;
  background:#fff;color:var(--ink)}
.finder select{width:auto;min-width:120px}
.finder .hint{font-size:14px;color:var(--ink-3);margin:6px 0 16px}
.finder .field{margin-bottom:14px}
.actions{display:flex;gap:12px;flex-wrap:wrap;align-items:center;margin-top:18px}
button,.btn-ghost{font:inherit;font-weight:600;border-radius:8px;padding:12px 20px;cursor:pointer;
  text-decoration:none;display:inline-block;line-height:1.2}
button{background:var(--btn);color:var(--btn-ink);border:1px solid var(--btn)}
button[disabled]{opacity:.65;cursor:progress}
.btn-ghost{background:transparent;color:var(--ink);border:1px solid #b9b6ad}
.btn-ghost:hover{background:var(--soft)}
:focus-visible{outline:3px solid var(--focus);outline-offset:2px}
.alert{border:1px solid var(--err-line);background:var(--err-bg);color:var(--err-ink);
  border-radius:10px;padding:14px 16px;max-width:680px;margin:18px 0 0}
.alert strong{display:block;margin-bottom:2px}
details{max-width:680px;margin-top:14px;border-top:1px solid var(--line);padding-top:12px}
details summary{cursor:pointer;font-weight:600}
details ol,details ul{margin:10px 0 4px;padding-left:22px}
details li{margin-bottom:6px}
.steps{display:grid;gap:12px;margin:26px 0 0;padding:0;list-style:none;max-width:680px}
.steps li{display:flex;gap:12px}
.steps b{flex:none;width:28px;height:28px;border-radius:50%;background:var(--ink);color:#fff;
  display:grid;place-items:center;font-size:14px}
.head{display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap;align-items:flex-end}
.meta{color:var(--ink-3);margin:0}
.badge{display:inline-block;background:#fff4d6;border:1px solid #ecd48a;color:#6b4e00;
  border-radius:999px;padding:2px 10px;font-size:13px;font-weight:600;margin-bottom:8px}
.kpis{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(min(100%,160px),1fr));margin-top:20px}
.kpi{padding:16px 18px}
.kpi .label{display:flex;align-items:center;gap:8px;color:var(--ink-2);font-size:14px;font-weight:600}
.kpi .key{width:10px;height:10px;border-radius:2px;flex:none}
.kpi .value{font-size:32px;font-weight:700;letter-spacing:-.02em;line-height:1.2;margin-top:4px}
.kpi .detail{color:var(--ink-3);font-size:13px}
.insights{padding:6px 20px;margin:0;list-style:none}
.insights li{padding:12px 0;border-bottom:1px solid var(--line)}
.insights li:last-child{border-bottom:0}
.charts{display:grid;gap:16px;grid-template-columns:repeat(auto-fit,minmax(min(100%,470px),1fr))}
.charts .wide{grid-column:1/-1}
.chart{margin:0;padding:12px 14px}
.chart img{display:block;width:100%;height:auto}
.tablewrap{overflow-x:auto;padding:0}
table{border-collapse:collapse;width:100%;font-size:14px;min-width:640px}
th,td{padding:10px 12px;border-bottom:1px solid var(--line);text-align:right;
  font-variant-numeric:tabular-nums}
th{background:var(--soft);color:var(--ink-2);font-weight:600;white-space:nowrap}
th:nth-child(-n+2),td:nth-child(-n+2){text-align:left}
td:nth-child(2){min-width:240px}
tr:last-child td{border-bottom:0}
.downloads{display:flex;gap:12px;flex-wrap:wrap;margin-top:16px}
footer{border-top:1px solid var(--line);color:var(--ink-3);font-size:13px;padding-block:18px 28px}
@media (prefers-reduced-motion:no-preference){button,.btn-ghost{transition:background .15s}}
"""

SUBMIT_JS = """
document.querySelectorAll('form.finder').forEach(function(f){
  f.addEventListener('submit',function(){
    var b=f.querySelector('button[type=submit]');
    if(b){setTimeout(function(){b.disabled=true;b.textContent='Getting the videos\\u2026 this takes a few seconds';},0);}
  });
});
"""


def esc(value) -> str:
    return escape("" if value is None else str(value), quote=True)


def _layout(title: str, body: str, nonce: str, with_js: bool = True) -> str:
    script = f'<script nonce="{esc(nonce)}">{SUBMIT_JS}</script>' if with_js else ""
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light">
<title>{esc(title)}</title>
<style>{CSS}</style></head>
<body>
<header class="top"><div class="wrap"><a class="brand" href="/">Channel Dashboard</a>
<span class="tag">How are a YouTube channel's recent videos doing?</span></div></header>
<main class="wrap">{body}</main>
<footer><div class="wrap">Uses public numbers from the YouTube Data API. A Python mini project
(pandas + matplotlib).</div></footer>
{script}
</body></html>"""


def _key_help() -> str:
    return """<details><summary>How do I get a free API key? (about 3 minutes)</summary>
<ol>
<li>Open <a href="https://console.cloud.google.com/" target="_blank" rel="noopener noreferrer">console.cloud.google.com</a> and sign in with a Google account.</li>
<li>Create a project, then open <b>APIs &amp; Services &rarr; Library</b>, search for <b>YouTube Data API v3</b> and click <b>Enable</b>.</li>
<li>Open <b>APIs &amp; Services &rarr; Credentials &rarr; Create credentials &rarr; API key</b> and copy the key.</li>
</ol></details>"""


def _channel_help() -> str:
    return """<details><summary>Where do I find a channel ID?</summary>
<ul>
<li>The easiest way: copy the <b>@name</b> shown under the channel name on its YouTube page (for example <code>@GoogleDevelopers</code>).</li>
<li>Or paste the channel's web address, for example <code>youtube.com/@GoogleDevelopers</code>.</li>
<li>The channel ID itself (it starts with <code>UC</code>): on a computer open the channel page, click the description text, then <b>Share channel &rarr; Copy channel ID</b>. Menu names change from time to time.</li>
<li>You can also type the channel's name, but a name can match the wrong channel, so an ID or @name is safer.</li>
</ul></details>"""


def _finder_form(values: dict, need_key: bool) -> str:
    method = "post" if need_key else "get"
    current_n = values.get("n", 20)
    options = "".join(
        f'<option value="{n}"{" selected" if n == current_n else ""}>{n} latest videos</option>'
        for n in VIDEO_COUNT_CHOICES
    )
    key_field = ""
    if need_key:
        key_field = """<div class="field"><label for="key">YouTube API key</label>
<input id="key" name="key" type="password" autocomplete="off" spellcheck="false"
 aria-describedby="key-hint">
<p class="hint" id="key-hint">Needed once for real channels. It is used for this request only and is not saved.</p></div>"""
    return f"""<form class="finder card" method="{method}" action="/dashboard">
<div class="field"><label for="channel">YouTube channel</label>
<input id="channel" name="channel" type="text" required maxlength="200" autocomplete="off"
 spellcheck="false" value="{esc(values.get('channel', ''))}" aria-describedby="channel-hint"
 placeholder="@GoogleDevelopers  or  UC_x5XG1OV2P6uZZ5FSM9Ttw">
<p class="hint" id="channel-hint">Paste a channel ID, an @name or a link to the channel.</p></div>
{key_field}
<div class="field" style="margin-bottom:0"><label for="n">How many videos</label>
<select id="n" name="n">{options}</select></div>
<div class="actions"><button type="submit">Show dashboard</button>
<a class="btn-ghost" href="/demo">Try it with demo data</a></div>
{_channel_help()}{_key_help() if need_key else ""}
</form>"""


def _error_banner(error) -> str:
    if not error:
        return ""
    return (f'<div class="alert" role="alert"><strong>{esc(error.title)}</strong>'
            f"{esc(error.tip)}</div>")


def home_page(nonce: str, need_key: bool, error=None, values: dict | None = None) -> str:
    body = f"""<h1>See how a channel's latest videos performed</h1>
<p class="lead">Type a YouTube channel and get views, likes and comments for its recent videos on one page.</p>
{_error_banner(error)}
{_finder_form(values or {}, need_key)}
<ol class="steps">
<li><b>1</b><span>Paste the channel ID, @name or link above.</span></li>
<li><b>2</b><span>Press <em>Show dashboard</em>. It takes a few seconds.</span></li>
<li><b>3</b><span>Read the headline numbers, charts and plain-English highlights. Download the image or the data if you need them.</span></li>
</ol>"""
    return _layout("Channel Dashboard", body, nonce)


def _kpi(key_var: str, label: str, value: str, detail: str) -> str:
    return (f'<div class="kpi card"><div class="label"><span class="key" '
            f'style="background:var({key_var})"></span>{esc(label)}</div>'
            f'<div class="value">{esc(value)}</div><div class="detail">{esc(detail)}</div></div>')


def _table(df, link_videos: bool) -> str:
    rows = []
    for _, r in df.sort_values("published_at", ascending=False).iterrows():
        title = esc(r["title"])
        if link_videos and _VIDEO_ID.match(str(r["video_id"])):
            title = (f'<a href="https://www.youtube.com/watch?v={esc(r["video_id"])}" '
                     f'target="_blank" rel="noopener noreferrer">{title}</a>')
        rows.append(
            f"<tr><td>{r['published_at']:%d %b %Y}</td><td>{title}</td>"
            f"<td>{r['views']:,}</td><td>{r['likes']:,}</td><td>{r['comments']:,}</td>"
            f"<td>{r['engagement_rate']:.2f}%</td></tr>"
        )
    return ('<div class="card tablewrap"><table><thead><tr><th>Published</th><th>Video</th>'
            "<th>Views</th><th>Likes</th><th>Comments</th><th>Engagement</th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table></div>")


def dashboard_page(result, charts, cache_id: str, nonce: str) -> str:
    s = result.summary
    subs = ""
    if not result.is_demo:
        subs = (f"{result.subscribers:,} subscribers · " if result.subscribers is not None
                else "subscribers hidden · ")
    badge = '<span class="badge">Demo data, not a real channel</span><br>' if result.is_demo else ""
    span = f"{s['first_date']:%d %b %Y} – {s['last_date']:%d %b %Y}"

    kpis = "".join([
        _kpi("--views", "Total views", fmt_number(s["total_views"]),
             f"{s['total_views']:,} · typical video {fmt_number(s['median_views'])}"),
        _kpi("--likes", "Total likes", fmt_number(s["total_likes"]),
             f"{s['like_rate']:.2f}% of views"),
        _kpi("--comments", "Total comments", fmt_number(s["total_comments"]),
             f"{s['comment_rate']:.2f}% of views"),
        _kpi("--eng", "Engagement rate", f"{s['engagement_rate']:.2f}%",
             "(likes + comments) ÷ views"),
    ])
    insights = "".join(f"<li>{esc(line)}</li>" for line in result.insights)
    cid = esc(cache_id)
    figures = "".join(
        f'<figure class="chart card{" wide" if c.wide else ""}"><picture>'
        f'<source media="(max-width: 640px)" srcset="/chart.svg?id={cid}&amp;k={c.key}&amp;v=m">'
        f'<img src="/chart.svg?id={cid}&amp;k={c.key}&amp;v=d" alt="{esc(c.alt)}" loading="lazy">'
        "</picture></figure>"
        for c in charts
    )
    body = f"""<div class="head"><div>{badge}<h1>{esc(result.channel_title)}</h1>
<p class="meta">{esc(subs)}last {s['videos']} videos · {esc(span)}</p></div>
<a class="btn-ghost" href="/">Check another channel</a></div>
<div class="kpis">{kpis}</div>
<h2>What stands out</h2><ul class="insights card">{insights}</ul>
<h2>Charts</h2><div class="charts">{figures}</div>
<h2>All videos</h2>{_table(result.df, not result.is_demo)}
<div class="downloads"><a class="btn-ghost" href="/dashboard.png?id={cid}" download="dashboard.png">Download dashboard image</a>
<a class="btn-ghost" href="/data.csv?id={cid}" download="videos.csv">Download data (CSV)</a></div>
<p class="muted" style="margin-top:18px;font-size:14px">Source: {esc(result.source_label)} · created {datetime.now():%d %b %Y, %H:%M}.
Engagement rate = (likes + comments) ÷ views. Numbers are what YouTube shows publicly; hidden like counts appear as 0.</p>"""
    return _layout(f"{result.channel_title} · Channel Dashboard", body, nonce, with_js=False)


def not_found_page(nonce: str, need_key: bool, message: str) -> str:
    body = f'<h1>Page not found</h1><p class="lead">{esc(message)}</p><p><a href="/">Back to the start</a></p>'
    return _layout("Not found", body, nonce, with_js=False)
