# Channel Dashboard: YouTube Video Performance

**Area:** Social Media Analytics & Visualization
**Goal:** Visualize views, likes and comment counts across a channel's recent videos.
**Key concepts:** multi-metric visualization, dashboards, API data → pandas → charts, a small web app.

Open the page, type a channel, get the dashboard. Nothing else to learn.

![dashboard](output/dashboard.png)

---

## Easiest way: the web app (no commands to type)

**Windows:** double-click **`START_WEB_APP.py`** (needs [Python](https://www.python.org/downloads/) installed once; tick
**"Add python.exe to PATH"** during setup).
**Mac / Linux:** run `python3 START_WEB_APP.py` in a terminal.

> **If Windows says the file is blocked or dangerous:** right-click the *zip file* → **Properties** → tick **Unblock** →
> **OK**, and only then extract it. Or open a terminal in the folder and type `python START_WEB_APP.py`.
> The project contains no `.exe` or `.bat` files, only readable Python code.

The first time it installs the libraries by itself (a few minutes, needs internet). Then your browser opens at
`http://localhost:8000`:

1. Type a channel: a **channel ID** (starts with `UC`), an **@name**, or a **link**.
2. Press **Show dashboard**.
3. Read the headline numbers, the plain-English highlights and the charts. Download the picture or the data.

**No API key yet?** Press **Try it with demo data**. It works immediately, with no key and no internet.

**For real channels** you need a free YouTube API key (section 4). Either paste it into the page, or save it once
so nobody has to: copy `.env.example` to `.env` and put `YOUTUBE_API_KEY=your_key` in it.

Want a public link anyone can open from a phone? See **`DEPLOY_ONLINE.md`** (optional).

---

## 1. Setup without the launcher

```bash
# Python 3.9+ required
pip install -r requirements.txt
python app.py            # web app, opens in your browser
```

## 2. Command-line version (for scripts and learning)

```bash
python main.py --demo                                   # demo data, no key needed
python main.py --channel @GoogleDevelopers --api-key YOUR_KEY
python main.py --channel UC_x5XG1OV2P6uZZ5FSM9Ttw --max-videos 30 --theme dark
python main.py --from-csv output/videos.csv             # redraw from a saved CSV, offline
```

| Option | Meaning |
|---|---|
| `--demo` | use built-in sample data |
| `--channel X` | channel ID (`UC...`), `@handle`, or a channel URL |
| `--api-key KEY` | API key (or set `YOUTUBE_API_KEY`, or put it in a `.env` file) |
| `--from-csv FILE` | load a CSV saved by an earlier run |
| `--max-videos N` | how many recent videos (default 20) |
| `--theme light\|dark` | colour theme |
| `--out DIR` | output folder (default `output`) |

It writes `output/dashboard.png`, `output/report.html` and `output/videos.csv`.

## 3. What the dashboard shows

| Part | Question it answers |
|---|---|
| Four headline tiles | How big is the channel overall? (views, likes, comments, engagement rate) |
| "What stands out" | The top video, the most engaging video, likes per comment, whether engagement is rising, posting rhythm. Every sentence is computed from the data. |
| Views / Likes / Comments per video | How does each metric change from video to video? Each has its own scale (see design note) |
| Most engaging videos | Which videos get the most reaction *relative to* their views? |
| Views vs likes bubble chart | Do more views mean more likes? Bubble size = comments |
| Engagement over time | Is the channel getting better or worse? |

**Engagement rate** = (likes + comments) ÷ views × 100.

**Design note: why separate charts for views, likes and comments?** They differ by orders of magnitude (tens of
thousands vs thousands vs hundreds). On one axis the comments would be invisible, and a two-axis chart can suggest
relationships that aren't there. So each metric gets its own chart ("small multiples"), with one consistent colour per
metric across the whole page.

**Phones:** the web app draws a second, narrower version of every chart for small screens so the text stays readable.

## 4. Getting a YouTube Data API key (free, about 3 minutes)

1. Open <https://console.cloud.google.com/> and create a project.
2. **APIs & Services → Library →** search **YouTube Data API v3 → Enable**.
3. **APIs & Services → Credentials → Create credentials → API key**.
4. Copy `.env.example` to `.env` and paste the key: `YOUTUBE_API_KEY=your_key`.

One channel costs about 4 of the free 10,000 units per day (searching by plain name costs 100). Keep your key
private and never upload `.env`.

## 5. Project structure

```
youtube_dashboard/
├── START_WEB_APP.py         # double-click launcher (sets up, then opens the web app)
├── app.py                   # starts the web app
├── main.py                  # command-line version
├── ytdash/
│   ├── webapp.py            # the web server (Python standard library only)
│   ├── webpage.py           # the HTML pages
│   ├── webcharts.py         # draws each chart as SVG (desktop + phone size)
│   ├── service.py           # one function: channel in, dashboard data out + friendly errors
│   ├── fetcher.py           # YouTube Data API v3 calls (urllib only)
│   ├── processing.py        # pandas cleaning + metrics + summary
│   ├── dashboard.py         # matplotlib chart panels and the single-image dashboard
│   ├── demo_data.py         # reproducible fake channel data
│   ├── config.py            # API key from CLI / env / .env
│   └── report.py            # HTML report for the command-line tool
├── tests/                   # 36 tests (no internet needed)
├── PROBLEM_BASED_LEARNING.md   # the guided problems, start here to learn
├── DEPLOY_ONLINE.md         # optional: get a public link
├── requirements.txt  .env.example  render.yaml
└── output/                  # generated files
```

Data flow: `fetcher` / `demo_data` → list of dicts → `processing.to_dataframe` → `add_metrics` → `summarize` →
`service.build_insights` → `webpage` + `webcharts` (web) or `dashboard` (image).

## 6. Run the tests

```bash
python -m unittest discover -s tests -v
```

## 7. Troubleshooting

| Problem | Fix |
|---|---|
| Double-clicking `START_WEB_APP.py` asks "how do you want to open this file?" or does nothing | Python is not installed. Install it from python.org, **tick "Add python.exe to PATH"**, then double-click again |
| Windows says the file is blocked | Right-click the zip → Properties → **Unblock** → OK, then extract again |
| Port 8000 is busy | The app picks the next free port and prints the address to open |
| "YouTube did not accept the API key" | Re-copy the key with no spaces; make sure *YouTube Data API v3* is enabled for its project |
| "The free daily YouTube limit has been used up" | It resets every day (midnight Pacific time). Use the demo meanwhile |
| "We couldn't find that channel" | Use the channel ID or the exact @name from the channel's page |
| Likes show 0 | The creator hid the like count; YouTube then sends no number |
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` |
