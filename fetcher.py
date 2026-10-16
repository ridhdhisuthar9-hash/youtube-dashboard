"""Fetch a channel's recent videos from the YouTube Data API v3.

Only the Python standard library is used (urllib), so there is nothing extra to install.

API quota note: this uses ``channels.list`` (1 unit), ``playlistItems.list`` (1 unit per
page) and ``videos.list`` (1 unit per batch of 50). A 50-video fetch costs ~4 units out of
the free 10,000 units/day - far cheaper than ``search.list`` (100 units per call).
"""

from __future__ import annotations

import json
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

API_BASE = "https://www.googleapis.com/youtube/v3"
TIMEOUT_SECONDS = 20


class YouTubeAPIError(RuntimeError):
    """Raised for any problem talking to the YouTube Data API.

    ``status`` holds the HTTP status code when there was one (None for network problems).
    """

    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


class ChannelNotFoundError(YouTubeAPIError):
    """The channel ID / handle / name did not match any channel."""


# --------------------------------------------------------------------------- helpers
def _get(endpoint: str, params: dict) -> dict:
    url = f"{API_BASE}/{endpoint}?{urlencode(params)}"
    request = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return json.load(response)
    except HTTPError as err:
        message = err.reason
        try:
            message = json.load(err)["error"]["message"]
        except Exception:  # noqa: BLE001 - best effort only
            pass
        # never include the URL here: it contains the API key
        raise YouTubeAPIError(f"YouTube API error {err.code}: {message}", status=err.code) from None
    except URLError as err:
        raise YouTubeAPIError(f"Network problem: {err.reason}") from None


_DURATION_RE = re.compile(r"^P(?:(?P<d>\d+)D)?T?(?:(?P<h>\d+)H)?(?:(?P<m>\d+)M)?(?:(?P<s>\d+)S)?$")


def parse_duration(iso_duration: str) -> int:
    """Convert an ISO-8601 duration such as ``PT1H2M10S`` to seconds."""
    match = _DURATION_RE.match(iso_duration or "")
    if not match:
        return 0
    parts = {k: int(v) if v else 0 for k, v in match.groupdict().items()}
    return parts["d"] * 86400 + parts["h"] * 3600 + parts["m"] * 60 + parts["s"]


def parse_channel_ref(reference: str) -> tuple[str, str]:
    """Work out what the user typed.

    Returns ``("id", "UCxxxx")`` or ``("handle", "@name")``.
    Accepts a channel ID, an @handle, or a channel URL.
    """
    ref = reference.strip()
    if not ref:
        raise YouTubeAPIError("Empty channel reference.")

    if ref.lower().startswith(("http://", "https://", "www.", "youtube.com", "m.youtube.com")):
        if not ref.lower().startswith("http"):
            ref = "https://" + ref
        path = urlparse(ref).path.strip("/")
        segments = path.split("/")
        if segments and segments[0].startswith("@"):
            return "handle", segments[0]
        if len(segments) >= 2 and segments[0] == "channel":
            return "id", segments[1]
        raise YouTubeAPIError(
            "Unsupported URL. Use a youtube.com/@handle or youtube.com/channel/UC... link."
        )

    if re.fullmatch(r"UC[\w-]{22}", ref):
        return "id", ref
    return "handle", ref if ref.startswith("@") else f"@{ref}"


# --------------------------------------------------------------------------- public API
def _channel_info(item: dict) -> dict:
    return {
        "channel_id": item["id"],
        "title": item["snippet"]["title"],
        "uploads_playlist": item["contentDetails"]["relatedPlaylists"]["uploads"],
        # hidden subscriber counts come back without the key -> None (shown as "hidden")
        "subscribers": (
            None
            if item["statistics"].get("hiddenSubscriberCount")
            else int(item["statistics"].get("subscriberCount", 0))
        ),
    }


def _lookup_channel(api_key: str, param: str, value: str) -> dict | None:
    """channels.list by ``id`` or ``forHandle``. Returns None when nothing matches."""
    data = _get(
        "channels",
        {"part": "snippet,contentDetails,statistics", "key": api_key, param: value},
    )
    items = data.get("items", [])
    return _channel_info(items[0]) if items else None


def search_channel_id(api_key: str, query: str) -> str:
    """Find a channel ID by its name (search.list costs 100 quota units, so it's a fallback)."""
    data = _get(
        "search",
        {"part": "snippet", "type": "channel", "q": query, "maxResults": 1, "key": api_key},
    )
    items = data.get("items", [])
    if not items:
        raise ChannelNotFoundError(f"Channel not found: {query!r}")
    item = items[0]
    channel_id = item.get("id", {}).get("channelId") or item.get("snippet", {}).get("channelId")
    if not channel_id:
        raise ChannelNotFoundError(f"Channel not found: {query!r}")
    return channel_id


def resolve_channel(api_key: str, reference: str, allow_search: bool = True) -> dict:
    """Look up a channel and return its title, uploads playlist ID and subscriber count.

    ``reference`` may be a channel ID, an @handle, a channel URL or - as a last resort, when
    ``allow_search`` is True - a plain channel name such as "Google Developers".
    """
    ref = reference.strip()
    is_url = ref.lower().startswith(("http://", "https://", "www.", "youtube.com", "m.youtube.com"))

    if " " in ref and not is_url:  # a spaced name can never be a handle or an ID
        if not allow_search:
            raise ChannelNotFoundError(f"Channel not found: {reference!r}")
        found = _lookup_channel(api_key, "id", search_channel_id(api_key, ref))
    else:
        kind, value = parse_channel_ref(ref)
        found = _lookup_channel(api_key, "id" if kind == "id" else "forHandle", value)
        if found is None and kind == "handle" and allow_search:
            found = _lookup_channel(api_key, "id", search_channel_id(api_key, value.lstrip("@")))

    if found is None:
        raise ChannelNotFoundError(f"Channel not found: {reference!r}")
    return found


def _recent_video_ids(api_key: str, playlist_id: str, max_videos: int) -> list[str]:
    ids: list[str] = []
    page_token = None
    while len(ids) < max_videos:
        params = {
            "part": "contentDetails",
            "playlistId": playlist_id,
            "maxResults": min(50, max_videos - len(ids)),
            "key": api_key,
        }
        if page_token:
            params["pageToken"] = page_token
        data = _get("playlistItems", params)
        ids.extend(item["contentDetails"]["videoId"] for item in data.get("items", []))
        page_token = data.get("nextPageToken")
        if not page_token:
            break
    return ids[:max_videos]


def fetch_recent_videos(api_key: str, playlist_id: str, max_videos: int = 20) -> list[dict]:
    """Return the channel's most recent uploads with view / like / comment counts."""
    video_ids = _recent_video_ids(api_key, playlist_id, max_videos)
    videos: list[dict] = []
    for start in range(0, len(video_ids), 50):
        batch = video_ids[start : start + 50]
        data = _get(
            "videos",
            {"part": "snippet,statistics,contentDetails", "id": ",".join(batch), "key": api_key},
        )
        for item in data.get("items", []):
            stats = item.get("statistics", {})
            # likes/comments can be hidden or disabled -> key is missing -> treat as 0
            videos.append(
                {
                    "video_id": item["id"],
                    "title": item["snippet"]["title"],
                    "published_at": item["snippet"]["publishedAt"],
                    "views": int(stats.get("viewCount", 0)),
                    "likes": int(stats.get("likeCount", 0)),
                    "comments": int(stats.get("commentCount", 0)),
                    "duration_sec": parse_duration(item["contentDetails"].get("duration", "")),
                }
            )
    return videos
