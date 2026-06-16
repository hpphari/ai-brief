#!/usr/bin/env python3
"""
Fetch YouTube content via Data API v3.
Reads YOUTUBE_API_KEY from env.
Reads youtube_subscriptions.json for channel list (fills missing channel IDs).
Also supports fetching liked videos from authenticated user.
"""

import os, json, re, requests
from datetime import datetime, timezone, timedelta

_API_KEY  = lambda: os.environ.get("YOUTUBE_API_KEY", "").strip()
_BASE     = "https://www.googleapis.com/youtube/v3"
_SUB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "youtube_subscriptions.json")

_COLORS = [
    "#f97316","#eab308","#22c55e","#60a5fa","#e879f9",
    "#34d399","#a78bfa","#818cf8","#c084fc","#f43f5e",
    "#06b6d4","#0ea5e9","#fb923c","#fbbf24","#10b981",
]


def _color(i: int) -> str:
    return _COLORS[i % len(_COLORS)]


def _get(endpoint: str, **params) -> dict:
    params["key"] = _API_KEY()
    r = requests.get(f"{_BASE}/{endpoint}", params=params, timeout=15)
    r.raise_for_status()
    return r.json()


def _parse_iso(dt_str: str):
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except Exception:
        return None


def _make_item(video_id: str, title: str, description: str,
               published_at: str, channel_name: str, color: str, category: str = "creator") -> dict:
    dt      = _parse_iso(published_at)
    display = description[:400] if description else title
    return {
        "title":          title.strip(),
        "link":           f"https://www.youtube.com/watch?v={video_id}",
        "summary_raw":    display,
        "date":           dt.strftime("%b %d, %H:%M") if dt else "recent",
        "date_raw":       dt,
        "source":         channel_name,
        "color":          color,
        "type":           "video",
        "category":       category,
        "show_chip":      True,
        "ai_summary":     None,
        "plain_headline": "",
        "impact":         "",
        "story_type":     "general",
        "is_release":     False,
        "predecessor":    None,
        "score":          2,
        "trending":       False,
        "subjects":       [],
        "revolution":     "incremental",
        "hype_type":      "real",
        "area":           None,
        "read_time":      "YouTube",
    }


def resolve_channel_id(handle_or_url: str) -> str | None:
    """Resolve a @handle or youtube.com/@handle URL to a channel ID via API."""
    key = _API_KEY()
    if not key:
        return None
    handle = re.sub(r"https?://www\.youtube\.com/@?", "", handle_or_url).lstrip("@")
    try:
        data = _get("channels", forHandle=f"@{handle}", part="id")
        items = data.get("items", [])
        return items[0]["id"] if items else None
    except Exception:
        return None


def fill_missing_channel_ids() -> int:
    """Read youtube_subscriptions.json, fill blank channel_ids, write back. Returns count filled."""
    key = _API_KEY()
    if not key or not os.path.exists(_SUB_FILE):
        return 0
    with open(_SUB_FILE) as f:
        subs = json.load(f)

    filled = 0
    for sub in subs:
        if sub.get("channel_id"):
            continue
        url = sub.get("url", "")
        if not url:
            continue
        cid = resolve_channel_id(url)
        if cid:
            sub["channel_id"] = cid
            filled += 1

    if filled:
        with open(_SUB_FILE, "w") as f:
            json.dump(subs, f, indent=2)
    return filled


def fetch_subscriptions(categories: list[str] | None = None,
                        max_per_channel: int = 3,
                        window_hours: int = 336) -> list[dict]:
    """
    Fetch recent videos from channels listed in youtube_subscriptions.json.
    Filters to `categories` if provided (e.g. ['ai']).
    Uses API to get uploads if channel_id is present; skips if missing.
    """
    key = _API_KEY()
    if not key or not os.path.exists(_SUB_FILE):
        return []

    with open(_SUB_FILE) as f:
        subs = json.load(f)

    if categories:
        subs = [s for s in subs if s.get("category") in categories]

    cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    items  = []

    for i, sub in enumerate(subs):
        cid  = sub.get("channel_id", "").strip()
        name = sub.get("name", f"Channel {i+1}")
        if not cid:
            continue
        color = _color(i)
        try:
            # Get uploads playlist ID
            ch = _get("channels", id=cid, part="contentDetails")
            ch_items = ch.get("items", [])
            if not ch_items:
                continue
            uploads_pid = (ch_items[0]
                           .get("contentDetails", {})
                           .get("relatedPlaylists", {})
                           .get("uploads", ""))
            if not uploads_pid:
                continue

            # Get recent videos from uploads playlist
            pl = _get("playlistItems", playlistId=uploads_pid,
                      part="snippet", maxResults=max_per_channel)
            for entry in pl.get("items", []):
                snippet = entry.get("snippet", {})
                pub     = snippet.get("publishedAt", "")
                dt      = _parse_iso(pub)
                if dt and dt < cutoff:
                    continue
                vid = snippet.get("resourceId", {}).get("videoId", "")
                if not vid:
                    continue
                items.append(_make_item(
                    video_id    = vid,
                    title       = snippet.get("title", "(no title)"),
                    description = snippet.get("description", ""),
                    published_at= pub,
                    channel_name= name,
                    color       = color,
                ))
        except Exception:
            continue

    return items


def fetch_liked_videos(max_results: int = 20, window_hours: int = 168) -> list[dict]:
    """
    Fetch your liked videos via OAuth. Requires YOUTUBE_OAUTH_TOKEN in env.
    Falls back gracefully if not configured.
    """
    token = os.environ.get("YOUTUBE_OAUTH_TOKEN", "").strip()
    if not token:
        return []

    cutoff  = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    headers = {"Authorization": f"Bearer {token}"}
    items   = []
    try:
        r = requests.get(
            f"{_BASE}/videos",
            headers=headers,
            params={"part": "snippet", "myRating": "like", "maxResults": max_results},
            timeout=15,
        )
        r.raise_for_status()
        for entry in r.json().get("items", []):
            snippet = entry.get("snippet", {})
            pub     = snippet.get("publishedAt", "")
            dt      = _parse_iso(pub)
            if dt and dt < cutoff:
                continue
            items.append(_make_item(
                video_id     = entry["id"],
                title        = snippet.get("title", "(no title)"),
                description  = snippet.get("description", ""),
                published_at = pub,
                channel_name = "YouTube: My Likes",
                color        = "#ff0000",
                category     = "x",
            ))
    except Exception as e:
        print(f"  YouTube Likes error: {e}")
    return items


def fetch_my_subscriptions_live(max_per_channel: int = 3,
                                window_hours: int = 336) -> list[dict]:
    """
    Fetch from your actual YouTube subscriptions using OAuth.
    Requires YOUTUBE_OAUTH_TOKEN in env.
    """
    token = os.environ.get("YOUTUBE_OAUTH_TOKEN", "").strip()
    if not token:
        return []

    headers = {"Authorization": f"Bearer {token}"}
    cutoff  = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    channel_ids = []

    try:
        next_page = None
        while True:
            params = {"part": "snippet", "mine": "true", "maxResults": 50}
            if next_page:
                params["pageToken"] = next_page
            r = requests.get(f"{_BASE}/subscriptions", headers=headers,
                             params=params, timeout=15)
            r.raise_for_status()
            data = r.json()
            for item in data.get("items", []):
                cid  = item["snippet"]["resourceId"]["channelId"]
                name = item["snippet"]["title"]
                channel_ids.append((cid, name))
            next_page = data.get("nextPageToken")
            if not next_page:
                break
    except Exception as e:
        print(f"  YouTube Subs error: {e}")
        return []

    items = []
    for i, (cid, name) in enumerate(channel_ids):
        color = _color(i)
        try:
            ch = _get("channels", id=cid, part="contentDetails")
            uploads_pid = (ch.get("items", [{}])[0]
                           .get("contentDetails", {})
                           .get("relatedPlaylists", {})
                           .get("uploads", ""))
            if not uploads_pid:
                continue
            pl = _get("playlistItems", playlistId=uploads_pid,
                      part="snippet", maxResults=max_per_channel)
            for entry in pl.get("items", []):
                snippet = entry.get("snippet", {})
                pub     = snippet.get("publishedAt", "")
                dt      = _parse_iso(pub)
                if dt and dt < cutoff:
                    continue
                vid = snippet.get("resourceId", {}).get("videoId", "")
                if not vid:
                    continue
                items.append(_make_item(vid, snippet.get("title", ""),
                                        snippet.get("description", ""),
                                        pub, name, color))
        except Exception:
            continue
    return items


if __name__ == "__main__":
    print("Testing YouTube fetcher...")
    if _API_KEY():
        filled = fill_missing_channel_ids()
        if filled:
            print(f"  Filled {filled} missing channel IDs")
        vids = fetch_subscriptions(categories=["ai"], max_per_channel=2)
        print(f"  Got {len(vids)} videos from ai-category subscriptions")
        for v in vids[:3]:
            print(f"  - [{v['source']}] {v['title'][:70]}")
    else:
        print("  Set YOUTUBE_API_KEY in .env to test")
