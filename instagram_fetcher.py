#!/usr/bin/env python3
"""
Fetch Instagram posts using instaloader (cookie-based, no API key needed).
Reads IG_USERNAME and IG_SESSION_ID from env.
Fetches posts from accounts you follow that are tagged with AI/tech topics.
"""

import os, re
from datetime import datetime, timezone, timedelta

_IG_USER       = lambda: os.environ.get("IG_USERNAME", "").strip()
_IG_SESSION_ID = lambda: os.environ.get("IG_SESSION_ID", "").strip()

# Accounts to follow (fetched individually — add your own here or set IG_ACCOUNTS env var)
_DEFAULT_ACCOUNTS = [
    "anthropic_ai",
    "openai",
    "googledeepmind",
    "huggingface",
    "perplexity_ai",
    "nvidia_ai",
    "metaai",
]

_AI_KEYWORDS = [
    "ai", "llm", "gpt", "claude", "gemini", "machine learning", "deep learning",
    "neural", "model", "chatbot", "artificial intelligence", "generative",
    "openai", "anthropic", "agent", "automation", "ml",
]

_COLORS = {
    "anthropic_ai":   "#f97316",
    "openai":         "#10b981",
    "googledeepmind": "#4285f4",
    "huggingface":    "#fbbf24",
    "perplexity_ai":  "#a78bfa",
    "nvidia_ai":      "#76b900",
    "metaai":         "#0668e1",
}


def _is_ai_related(text: str) -> bool:
    text = text.lower()
    return any(kw in text for kw in _AI_KEYWORDS)


def _make_item(shortcode: str, caption: str, timestamp: datetime,
               account: str, color: str) -> dict:
    title   = (caption[:120] + "…") if len(caption) > 120 else caption
    title   = re.sub(r"\s+", " ", title.replace("\n", " ")).strip()
    return {
        "title":          title or f"Post by @{account}",
        "link":           f"https://www.instagram.com/p/{shortcode}/",
        "summary_raw":    caption[:600],
        "date":           timestamp.strftime("%b %d, %H:%M") if timestamp else "recent",
        "date_raw":       timestamp,
        "source":         f"IG: @{account}",
        "color":          color,
        "type":           "article",
        "category":       "instagram",
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
        "read_time":      "Instagram",
    }


def _get_loader():
    """Return an authenticated instaloader instance using saved session file."""
    import instaloader
    username = _IG_USER() or "hariprasadpottivel"
    L = instaloader.Instaloader(
        quiet=True,
        download_pictures=False,
        download_videos=False,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
    )
    session_file = os.path.expanduser(f"~/.config/instaloader/session-{username}")
    if os.path.exists(session_file):
        L.load_session_from_file(username)
    elif _IG_SESSION_ID():
        L.context._session.cookies.set("sessionid", _IG_SESSION_ID(), domain=".instagram.com")
        L.context.username = username
    else:
        return None
    return L


def fetch_account_posts(username: str, color: str = "#e1306c",
                        max_posts: int = 5, window_hours: int = 168,
                        ai_only: bool = True) -> list[dict]:
    """Fetch recent posts from a public Instagram account."""
    try:
        import instaloader
        L = _get_loader()
        if not L:
            return []

        cutoff  = datetime.now(timezone.utc) - timedelta(hours=window_hours)
        profile = instaloader.Profile.from_username(L.context, username)
        items   = []

        for post in profile.get_posts():
            if post.date_utc.replace(tzinfo=timezone.utc) < cutoff:
                break
            caption = post.caption or ""
            if ai_only and not _is_ai_related(caption):
                continue
            items.append(_make_item(
                shortcode = post.shortcode,
                caption   = caption,
                timestamp = post.date_utc.replace(tzinfo=timezone.utc),
                account   = username,
                color     = color,
            ))
            if len(items) >= max_posts:
                break
        return items

    except Exception as e:
        print(f"  IG @{username} error: {e}")
        return []


def fetch_instagram(accounts: list[str] | None = None,
                    max_per_account: int = 3,
                    window_hours: int = 168,
                    ai_only: bool = True) -> list[dict]:
    """
    Fetch posts from a list of Instagram accounts.
    Uses IG_ACCOUNTS env var (comma-separated) or the default AI accounts list.
    Requires IG_SESSION_ID in .env.
    """
    username = _IG_USER() or "hariprasadpottivel"
    session_file = os.path.expanduser(f"~/.config/instaloader/session-{username}")
    if not os.path.exists(session_file) and not _IG_SESSION_ID():
        return []

    # Allow override via env var
    env_accounts = os.environ.get("IG_ACCOUNTS", "")
    if env_accounts:
        accounts = [a.strip().lstrip("@") for a in env_accounts.split(",") if a.strip()]
    elif not accounts:
        accounts = _DEFAULT_ACCOUNTS

    items = []
    for account in accounts:
        color = _COLORS.get(account, "#e1306c")
        fetched = fetch_account_posts(
            username     = account,
            color        = color,
            max_posts    = max_per_account,
            window_hours = window_hours,
            ai_only      = ai_only,
        )
        items.extend(fetched)
    return items


if __name__ == "__main__":
    print("Testing Instagram fetcher...")
    if _IG_SESSION_ID():
        items = fetch_instagram(max_per_account=2)
        print(f"  Got {len(items)} posts")
        for i in items[:3]:
            print(f"  - [{i['source']}] {i['title'][:70]}")
    else:
        print("  Set IG_SESSION_ID (and optionally IG_USERNAME) in .env to test")
