#!/usr/bin/env python3
"""Fetch X/Twitter bookmarks by searching saved posts using BookmarkSearchTimeline."""

import os, json, re, requests
from datetime import datetime, timezone

_BEARER = "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
_BM_SEARCH_QID = "vqy7GkKMR5TYk8_ysuhmfA"  # BookmarkSearchTimeline

# Search terms to pull AI/ML bookmarks — covers most of what you'd save
_SEARCH_QUERIES = ["AI", "LLM", "GPT", "Claude", "Gemini", "agent", "machine learning",
                   "startup", "OpenAI", "Anthropic", "deep learning", "productivity"]

_FEATURES = json.dumps({
    "rweb_tipjar_consumption_enabled": True,
    "responsive_web_graphql_exclude_directive_enabled": True,
    "verified_phone_label_enabled": False,
    "creator_subscriptions_tweet_preview_api_enabled": True,
    "responsive_web_graphql_timeline_navigation_enabled": True,
    "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
    "communities_web_enable_tweet_community_results_fetch": True,
    "c9s_tweet_anatomy_moderator_badge_enabled": True,
    "articles_preview_enabled": True,
    "responsive_web_edit_tweet_api_enabled": True,
    "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
    "view_counts_everywhere_api_enabled": True,
    "longform_notetweets_consumption_enabled": True,
    "responsive_web_twitter_article_tweet_consumption_enabled": True,
    "tweet_awards_web_tipping_enabled": False,
    "creator_subscriptions_quote_tweet_preview_enabled": False,
    "freedom_of_speech_not_reach_fetch_enabled": True,
    "standardized_nudges_misinfo": True,
    "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
    "rweb_video_timestamps_enabled": True,
    "longform_notetweets_rich_text_read_enabled": True,
    "longform_notetweets_inline_media_enabled": True,
    "responsive_web_enhance_cards_enabled": False,
})


def _cookie_str() -> str:
    auth  = os.environ.get("X_AUTH_TOKEN", "")
    ct0   = os.environ.get("X_CT0", "")
    twid  = os.environ.get("X_TWID", "")
    guest = os.environ.get("X_GUEST_ID", "")
    return f"auth_token={auth}; ct0={ct0}; twid={twid}; guest_id={guest}"


def _headers() -> dict:
    ct0 = os.environ.get("X_CT0", "")
    return {
        "authorization":             f"Bearer {_BEARER}",
        "x-csrf-token":              ct0,
        "cookie":                    _cookie_str(),
        "x-twitter-auth-type":       "OAuth2Session",
        "x-twitter-active-user":     "yes",
        "x-twitter-client-language": "en",
        "user-agent":                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "referer":                   "https://x.com/i/bookmarks",
    }


def _parse_tweets(instructions: list) -> list[dict]:
    tweets = []
    for inst in instructions:
        for entry in inst.get("entries", []):
            result = (entry.get("content", {})
                          .get("itemContent", {})
                          .get("tweet_results", {})
                          .get("result", {}))
            if result.get("__typename") == "TweetWithVisibilityResults":
                result = result.get("tweet", result)
            if result.get("__typename") != "Tweet":
                continue
            legacy = result.get("legacy", {})
            text   = legacy.get("full_text", "").strip()
            tid    = legacy.get("id_str") or result.get("rest_id", "")
            created = legacy.get("created_at", "")
            try:
                dt = datetime.strptime(created, "%a %b %d %H:%M:%S +0000 %Y").replace(tzinfo=timezone.utc)
                date_str = dt.strftime("%b %d, %H:%M")
            except Exception:
                dt, date_str = None, "recent"

            display = re.sub(r"\s*https://t\.co/\S+$", "", text).strip()
            tweets.append({
                "id":       tid,
                "text":     text,
                "display":  display,
                "dt":       dt,
                "date_str": date_str,
            })
    return tweets


def _search_bookmarks(query: str, count: int = 20) -> list[dict]:
    variables = json.dumps({"rawQuery": query, "count": count, "product": "Latest"})
    try:
        r = requests.get(
            f"https://x.com/i/api/graphql/{_BM_SEARCH_QID}/BookmarkSearchTimeline",
            headers=_headers(),
            params={"variables": variables, "features": _FEATURES},
            timeout=15,
        )
        data = r.json()
        instructions = (data["data"]["search_by_raw_query"]
                            ["bookmarks_search_timeline"]["timeline"]["instructions"])
        return _parse_tweets(instructions)
    except Exception:
        return []


def _make_item(tweet: dict) -> dict:
    display = tweet["display"]
    return {
        "title":          display[:140] + ("…" if len(display) > 140 else ""),
        "link":           f"https://x.com/i/web/status/{tweet['id']}",
        "summary_raw":    tweet["text"],
        "date":           tweet["date_str"],
        "date_raw":       tweet["dt"],
        "source":         "X: My Bookmarks",
        "color":          "#1d9bf0",
        "type":           "article",
        "category":       "x",
        "show_chip":      True,
        "ai_summary":     None,
        "plain_headline": "",
        "impact":         "",
        "story_type":     "general",
        "is_release":     False,
        "predecessor":    None,
        "score":          3,
        "trending":       False,
        "subjects":       [],
        "revolution":     "incremental",
        "hype_type":      "real",
        "area":           None,
        "read_time":      "tweet",
    }


def fetch_bookmarks(max_total: int = 40) -> list[dict]:
    """Fetch AI/ML bookmarks across multiple search queries, deduplicated."""
    if not os.environ.get("X_AUTH_TOKEN") or not os.environ.get("X_CT0"):
        return []

    seen   = set()
    items  = []

    for query in _SEARCH_QUERIES:
        if len(items) >= max_total:
            break
        tweets = _search_bookmarks(query, count=20)
        for t in tweets:
            if t["id"] in seen:
                continue
            seen.add(t["id"])
            items.append(_make_item(t))
            if len(items) >= max_total:
                break

    return items


if __name__ == "__main__":
    # Load .env
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

    print("Testing X bookmarks fetch...")
    items = fetch_bookmarks(20)
    print(f"Got {len(items)} bookmarks")
    for i in items[:5]:
        print(f"  - {i['title'][:80]}")
