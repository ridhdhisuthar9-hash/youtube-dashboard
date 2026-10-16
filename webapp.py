"""A small web server: open the page, type a channel, get the dashboard.

Only Python's standard library is used for serving (``http.server``), so there is nothing extra
to install. Run it with:   python app.py

* Locally it listens on http://localhost:8000 and opens your browser.
* When a hosting service sets the PORT environment variable, it listens on all addresses.
* The YouTube API key comes from the YOUTUBE_API_KEY environment variable (or a .env file).
  If none is set, the page asks the visitor for one. The demo works without a key.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import secrets
import sys
import threading
import time
import webbrowser
from collections import OrderedDict, deque
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from . import config, service, webcharts, webpage

CACHE_SECONDS = 3600  # a repeat search within an hour is free (saves YouTube quota)
CACHE_MAX_ENTRIES = 60
RATE_LIMIT_EVENTS = 12  # real (non-cached) lookups per visitor ...
RATE_LIMIT_WINDOW = 600  # ... per 10 minutes
MAX_POST_BYTES = 8192


# --------------------------------------------------------------------------- state
class RateLimiter:
    """Allow at most ``limit`` events per ``window`` seconds for each visitor."""

    def __init__(self, limit: int = RATE_LIMIT_EVENTS, window: float = RATE_LIMIT_WINDOW):
        self.limit, self.window = limit, window
        self._events: dict[str, deque] = {}
        self._lock = threading.Lock()

    def allow(self, who: str, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        with self._lock:
            q = self._events.setdefault(who, deque())
            while q and now - q[0] > self.window:
                q.popleft()
            if len(q) >= self.limit:
                return False
            q.append(now)
            return True


@dataclass
class CacheEntry:
    result: service.DashboardResult
    charts: list  # chart descriptions; the pictures are drawn on request
    png: bytes | None = None
    svgs: dict = field(default_factory=dict)
    stored: float = field(default_factory=time.time)


@dataclass
class AppState:
    api_key: str | None = None
    loader: object = service.get_dashboard  # replaced by a fake in tests
    cache: OrderedDict = field(default_factory=OrderedDict)
    cache_lock: threading.Lock = field(default_factory=threading.Lock)
    limiter: RateLimiter = field(default_factory=RateLimiter)

    @property
    def need_key(self) -> bool:
        return not self.api_key

    def cache_id(self, ref: str, n: int, demo: bool) -> str:
        raw = f"{int(demo)}|{ref.strip().lower()}|{n}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def get_cached(self, cid: str) -> CacheEntry | None:
        with self.cache_lock:
            entry = self.cache.get(cid)
            if entry and time.time() - entry.stored > CACHE_SECONDS:
                del self.cache[cid]
                return None
            if entry:
                self.cache.move_to_end(cid)
            return entry

    def put_cached(self, cid: str, entry: CacheEntry) -> None:
        with self.cache_lock:
            self.cache[cid] = entry
            self.cache.move_to_end(cid)
            while len(self.cache) > CACHE_MAX_ENTRIES:
                self.cache.popitem(last=False)


# --------------------------------------------------------------------------- request handling
class Handler(BaseHTTPRequestHandler):
    server_version = "ChannelDashboard/1.0"
    protocol_version = "HTTP/1.1"

    @property
    def state(self) -> AppState:
        return self.server.state  # type: ignore[attr-defined]

    # -- small helpers
    def log_message(self, fmt, *args):  # quieter, and never prints form bodies
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _visitor(self) -> str:
        forwarded = self.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        return forwarded or self.client_address[0]

    def _send(self, status: int, body: bytes, content_type: str, extra: dict | None = None,
              nonce: str | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        if content_type.startswith("image/svg"):
            self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'")
            self.send_header("Cache-Control", "private, max-age=300")
        if content_type.startswith("text/html"):
            script = f"script-src 'nonce-{nonce}'" if nonce else "script-src 'none'"
            self.send_header(
                "Content-Security-Policy",
                f"default-src 'none'; img-src 'self'; style-src 'unsafe-inline'; {script}; "
                "form-action 'self'; base-uri 'none'; frame-ancestors 'none'",
            )
            self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _html(self, status: int, builder) -> None:
        nonce = secrets.token_urlsafe(16)
        self._send(status, builder(nonce).encode("utf-8"), "text/html; charset=utf-8", nonce=nonce)

    # -- routes
    def do_GET(self):  # noqa: N802
        url = urlsplit(self.path)
        query = {k: v[0] for k, v in parse_qs(url.query).items() if v}
        route = url.path.rstrip("/") or "/"
        if route == "/":
            self._html(200, lambda nonce: webpage.home_page(nonce, self.state.need_key))
        elif route == "/dashboard":
            self._dashboard(query)
        elif route == "/demo":
            self._dashboard({"channel": "demo", "n": query.get("n", "20")}, demo=True)
        elif route == "/chart.svg":
            self._chart(query)
        elif route == "/dashboard.png":
            self._download(query.get("id", ""), "png")
        elif route == "/data.csv":
            self._download(query.get("id", ""), "csv")
        elif route == "/health":
            self._send(200, b"ok", "text/plain; charset=utf-8")
        else:
            self._html(404, lambda nonce: webpage.not_found_page(
                nonce, self.state.need_key, "That page does not exist."))

    do_HEAD = do_GET  # noqa: N815

    def do_POST(self):  # noqa: N802
        if urlsplit(self.path).path.rstrip("/") != "/dashboard":
            self._html(404, lambda nonce: webpage.not_found_page(
                nonce, self.state.need_key, "That page does not exist."))
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length > MAX_POST_BYTES:
            self._send(413, b"Request too large", "text/plain; charset=utf-8")
            return
        raw = self.rfile.read(length).decode("utf-8", errors="replace")
        form = {k: v[0] for k, v in parse_qs(raw).items() if v}
        self._dashboard(form)

    def _dashboard(self, params: dict, demo: bool = False) -> None:
        channel = "".join(ch for ch in params.get("channel", "") if ch.isprintable()).strip()[:200]
        try:
            n = int(params.get("n", 20))
        except ValueError:
            n = 20
        n = max(1, min(n, service.MAX_VIDEOS_LIMIT))
        values = {"channel": "" if demo else channel, "n": n}
        # a visitor's own key is only honoured when the server has none of its own
        api_key = self.state.api_key or params.get("key", "").strip() or None

        cid = self.state.cache_id(channel, n, demo)
        entry = self.state.get_cached(cid)
        if entry is None:
            try:
                if not demo and channel and api_key and not self.state.limiter.allow(self._visitor()):
                    raise service.UserFacingError(
                        "That is a lot of searches in a short time.",
                        "Please wait a few minutes and try again.", 429)
                result = self.state.loader(channel, api_key, n, demo)
                entry = CacheEntry(result, webcharts.chart_meta(result.df))
                # only cache successful lookups; the key is never part of the cache id
                self.state.put_cached(cid, entry)
            except service.UserFacingError as err:
                self._html(err.status, lambda nonce: webpage.home_page(
                    nonce, self.state.need_key, err, values))
                return
            except Exception as exc:  # noqa: BLE001 - never show a stack trace to a visitor
                sys.stderr.write(f"Unexpected error: {exc!r}\n")
                err = service.UserFacingError(
                    "Something went wrong on our side.", "Please try again in a moment.", 500)
                self._html(500, lambda nonce: webpage.home_page(
                    nonce, self.state.need_key, err, values))
                return
        self._html(200, lambda nonce: webpage.dashboard_page(entry.result, entry.charts, cid, nonce))

    def _chart(self, query: dict) -> None:
        entry = self.state.get_cached(query.get("id", ""))
        key, variant = query.get("k", ""), query.get("v", "d")
        if entry is None or key not in webcharts.SPECS or variant not in webcharts.VARIANTS:
            self._send(404, b"Not found", "text/plain; charset=utf-8")
            return
        svg = entry.svgs.get((key, variant))
        if svg is None:
            svg = entry.svgs[(key, variant)] = webcharts.render_chart(entry.result.df, key, variant)
        self._send(200, svg, "image/svg+xml")

    def _download(self, cid: str, kind: str) -> None:
        entry = self.state.get_cached(cid)
        if entry is None:
            self._html(404, lambda nonce: webpage.not_found_page(
                nonce, self.state.need_key,
                "That download has expired. Go back, search again and use the download button."))
            return
        name = re.sub(r"[^A-Za-z0-9]+", "_", entry.result.channel_title).strip("_")[:40] or "channel"
        if kind == "png":
            if entry.png is None:
                entry.png = webcharts.render_png(entry.result)
            self._send(200, entry.png, "image/png",
                       {"Content-Disposition": f'attachment; filename="{name}_dashboard.png"'})
        else:
            df = entry.result.df.drop(columns=["short_title"], errors="ignore")
            df = df.round({"like_rate": 2, "comment_rate": 2, "engagement_rate": 2})
            csv = df.to_csv(index=False).encode("utf-8-sig")  # BOM so Excel reads it correctly
            self._send(200, csv, "text/csv; charset=utf-8",
                       {"Content-Disposition": f'attachment; filename="{name}_videos.csv"'})


# --------------------------------------------------------------------------- start-up
def make_server(address: tuple[str, int], state: AppState) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(address, Handler)
    server.daemon_threads = True
    server.state = state  # type: ignore[attr-defined]
    return server


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Channel Dashboard web app")
    on_host = "PORT" in os.environ
    parser.add_argument("--host", default="0.0.0.0" if on_host else "127.0.0.1")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8000)))
    parser.add_argument("--no-browser", action="store_true", help="do not open the browser")
    args = parser.parse_args(argv)

    api_key = config.get_api_key()
    state = AppState(api_key=api_key)

    server = None
    port = args.port
    for candidate in range(args.port, args.port + (1 if on_host else 10)):
        try:
            server = make_server((args.host, candidate), state)
            port = candidate
            break
        except OSError:
            continue
    if server is None:
        print(f"Could not start: port {args.port} is already in use. Close the other copy and retry.")
        return 1

    url = f"http://localhost:{port}"
    print("=" * 60)
    print(" Channel Dashboard is running")
    print(f" Open this address in your browser:  {url}")
    print(" To stop it, press Ctrl+C or close this window.")
    print(" API key: " + ("found, real channels will work" if api_key else
          "not set. The page will ask for one. Demo works without it."))
    print("=" * 60)
    if not args.no_browser and not on_host:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
