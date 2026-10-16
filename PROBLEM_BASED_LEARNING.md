# Problem-Based Learning Guide

**Project:** YouTube Video Performance Dashboard
**Concepts:** multi-metric visualization · dashboards · API → DataFrame → chart · a small web app

The project is already built. Learn it the problem-based way: read the problem, try to
solve it yourself, then open the file named under **Where** to compare with the working solution.

## The big problem

> A YouTube creator uploads a video every week. Looking at each video's page one by one is slow.
> **Build a single dashboard that shows how views, likes and comments changed across the channel's
> recent videos, and which videos performed best.**

## Problems to solve (in order)

### Problem 1 - Where does the data come from?
*Task:* Find out how a program can get video statistics from YouTube. What must you ask for?
*Hint:* A channel has an "uploads playlist"; each video has a `statistics` block.
*Where:* `ytdash/fetcher.py` → `resolve_channel`, `fetch_recent_videos`
*You learn:* REST API, API keys, JSON, pagination (max 50 items per request), quota.

### Problem 2 - What if I have no API key?
*Task:* Make the project run anyway, with realistic numbers.
*Hint:* Real view counts are skewed - a few videos get far more than the rest (log-normal).
*Where:* `ytdash/demo_data.py`
*You learn:* random data with a seed (reproducible), the `numpy` generator, simulating real distributions.

### Problem 3 - Messy data
*Task:* The API can omit likes (hidden) or comments (disabled), sends numbers as text, and dates as strings.
How do you clean it? What if a video has 0 views?
*Where:* `ytdash/processing.py` → `to_dataframe`, `add_metrics`
*You learn:* `pandas` DataFrames, `to_datetime`, `to_numeric`, `fillna`, avoiding division by zero.

### Problem 4 - What does "performed well" mean?
*Task:* A video with 90,000 views is not necessarily the most loved. Define a fair measure.
*Hint:* Compare reactions to audience size.
*Where:* `add_metrics` - engagement rate = (likes + comments) ÷ views × 100
*You learn:* derived metrics, weighted vs simple average (see `summarize`: why total ÷ total, not mean of rates).

### Problem 5 - Three metrics, three scales
*Task:* Plot views, likes and comments together. Try one chart first - what goes wrong?
*Hint:* Comments (hundreds) vanish next to views (tens of thousands). Is a second y-axis a good fix?
*Where:* `ytdash/dashboard.py` → `_small_multiple`
*You learn:* **multi-metric visualization** - small multiples, shared time axis, consistent colour per metric, why dual-axis charts mislead.

### Problem 6 - Put it all on one page
*Task:* Arrange KPI tiles, 3 bar charts, a ranked bar chart, a scatter plot and a trend line on one canvas.
*Where:* `render_dashboard` - `GridSpec` (3 rows × 6 columns) and `subgridspec`
*You learn:* **dashboard layout**, visual hierarchy (headline numbers first, detail below), matching each question to a chart type:

| Question | Chart |
|---|---|
| How much in total? | KPI tile |
| How does a value change over time? | bar / line |
| Which are best? | ranked horizontal bars |
| Are two things related? | scatter (bubble size = 3rd variable) |

### Problem 7 - Make it readable
*Task:* Add a dark theme, label only what matters, show the typical (median) level, keep colours consistent.
*Where:* `THEMES`, `_median_note`, direct label on the best bar only
*You learn:* design for readability - less ink, direct labels, never colour-only meaning.

### Problem 8 - Make it usable by others
*Task:* Add a command-line interface and save the results (PNG, HTML, CSV).
*Where:* `main.py` (argparse), `ytdash/report.py`
*You learn:* CLI design, file I/O, base64-embedding an image in HTML, `html.escape` (never put raw titles into HTML).

### Problem 9 - How do I know it works?
*Task:* Write tests for the maths and the parsing.
*Where:* `tests/test_project.py`
*You learn:* `unittest`, testing edge cases (0 views, empty list, 1 video), reproducible test data.

### Problem 10 - Make it usable by anyone
*Task:* A classmate who has never used Python wants the result. They should open a page, type a channel and see the dashboard. What must the program do for them?
*Hint:* A web page is just text sent over HTTP. Python can send it with the standard library, no framework needed.
*Where:* `ytdash/webapp.py` (server), `ytdash/webpage.py` (HTML), `ytdash/service.py` (one function that does all the work)
*You learn:* HTTP GET vs POST, routes, status codes (200, 400, 404, 429), why the page must work on a phone (a second, narrower chart), and plain-language error messages instead of stack traces.

### Problem 11 - Keep it safe and cheap
*Task:* Anyone can type anything into the page, and every search costs YouTube quota. What can go wrong?
*Where:* `webpage.esc()` (escaping), `webapp.RateLimiter`, the cache in `AppState`, the `Content-Security-Policy` header
*You learn:* **never put outside text into HTML unescaped** (a video titled `<script>...` must show as text), caching to save quota, rate limiting, keeping secrets (the API key) on the server and out of the page.

## Challenges (extend the project)

1. **Easy:** add a "dislikes-free" *like rate* chart or show `duration_sec` on a new panel.
2. **Easy:** add `--sort views|engagement` for the data table in `report.py`.
3. **Medium:** does video length affect views? Add a scatter of `duration_sec` vs `views`.
4. **Medium:** add day-of-week analysis - which upload day gets the most views? (`df["published_at"].dt.day_name()`)
5. **Medium:** compare two channels side by side (run twice, concatenate DataFrames, colour by channel).
6. **Hard:** store each run in SQLite with a date, then plot how a video's views grow over days.
7. **Hard:** turn it into a Streamlit web app with a channel text box.

## Viva / interview questions (with short answers)


1. **Why is the API key not hard-coded?** Secrets in code leak when shared; we read it from CLI / env / `.env`.
2. **Why `playlistItems` instead of `search`?** `search` costs 100 quota units per call, `playlistItems` costs 1.
3. **What is engagement rate and why not just use likes?** Likes depend on audience size; dividing by views makes videos comparable.
4. **Why median lines, not average lines?** One viral video drags the average up; the median shows the typical video.
5. **Why not a dual-axis chart?** The two scales are arbitrary, so the crossing points and slopes mean nothing and can mislead.
6. **What does `matplotlib.use("Agg")` do?** Draws to files without needing a display window.
7. **What happens if a video has 0 views?** Rates become 0 instead of crashing (`replace(0, nan)` then `fillna(0)`).
8. **How is the demo data reproducible?** A fixed random seed.
9. **Why does the web app draw charts as SVG, and why two sizes?** SVG stays sharp at any size; a shrunken desktop chart is unreadable on a phone, so a narrower one is drawn for small screens.
10. **What stops a video title like `<script>alert(1)</script>` from running in the page?** Every outside string goes through `html.escape` before it is put in the HTML (and the page's security policy blocks inline scripts anyway). There is a test for it.
11. **Why is there a cache and a rate limit?** YouTube gives only 10,000 free units a day. A repeat search within an hour is served from memory, and each visitor can make only 12 new searches per 10 minutes.
12. **Why can't the page call the YouTube API directly from the browser?** The API key would be visible to every visitor. The Python server makes the call, so the key stays private.

## Suggested report outline (for your submission)

1. Problem statement · 2. Objectives · 3. Tools (Python, pandas, matplotlib, YouTube Data API)
4. System design (data-flow diagram from the README) · 5. Implementation (one paragraph per module)
6. Results (dashboard screenshot + 3 observations) · 7. Testing · 8. Limitations (API quota, hidden likes, only recent videos) · 9. Future scope (challenges above) · 10. References
