#!/usr/bin/env python3
"""Fetch X/Twitter bookmarks and enrich them by following URLs to extract
article text, PDF content, and YouTube metadata."""

import os, json, re, requests, io
from datetime import datetime, timezone

_BEARER = "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
_BM_SEARCH_QID = "vqy7GkKMR5TYk8_ysuhmfA"  # BookmarkSearchTimeline

_SEARCH_QUERIES = [
    "AI", "LLM", "GPT", "Claude", "Gemini", "agent", "machine learning",
    "startup", "OpenAI", "Anthropic", "deep learning", "productivity",
    "paper", "research", "model", "inference", "reasoning",
]

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

_HEADERS_BROWSER = {
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "accept-language": "en-US,en;q=0.9",
}


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
        "user-agent":                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "referer":                   "https://x.com/i/bookmarks",
    }


# ── URL resolution & content extraction ───────────────────────────────────────

def _resolve_url(tco_url: str) -> str:
    """Follow t.co short-link redirect to get the real destination URL.
    Requires X cookies — t.co only redirects for authenticated sessions."""
    auth = os.environ.get("X_AUTH_TOKEN", "")
    ct0  = os.environ.get("X_CT0", "")
    twid = os.environ.get("X_TWID", "")
    h = {**_HEADERS_BROWSER,
         "cookie": f"auth_token={auth}; ct0={ct0}; twid={twid}"}
    try:
        r = requests.get(tco_url, allow_redirects=True, headers=h, timeout=10)
        return r.url
    except Exception:
        return tco_url


def _is_x_tweet(url: str) -> bool:
    return "x.com" in url or "twitter.com" in url


def _is_youtube(url: str) -> bool:
    return "youtube.com/watch" in url or "youtu.be/" in url


def _is_pdf(url: str) -> bool:
    return url.lower().endswith(".pdf") or "arxiv.org/pdf" in url or "/pdf/" in url.lower()


def _extract_youtube(url: str) -> tuple[str, str]:
    """Return (resolved_url, content_text) for a YouTube link using oEmbed (no API key)."""
    try:
        oe = requests.get(
            "https://www.youtube.com/oembed",
            params={"url": url, "format": "json"},
            headers=_HEADERS_BROWSER, timeout=8,
        ).json()
        title  = oe.get("title", "")
        author = oe.get("author_name", "")
        text   = f"YouTube video: {title}\nChannel: {author}"
        return url, text
    except Exception:
        return url, ""


def _extract_pdf(url: str) -> tuple[str, str]:
    """Download up to 150 KB of a PDF and extract the first ~2,000 chars of text."""
    try:
        r = requests.get(url, headers=_HEADERS_BROWSER, timeout=15, stream=True)
        content = b""
        for chunk in r.iter_content(chunk_size=8192):
            content += chunk
            if len(content) > 150_000:
                break
        import pypdf, io
        reader = pypdf.PdfReader(io.BytesIO(content))
        pages_text = []
        for page in reader.pages[:6]:  # first 6 pages
            t = page.extract_text() or ""
            pages_text.append(t)
            if sum(len(p) for p in pages_text) > 3000:
                break
        text = "\n".join(pages_text)[:3000]
        return url, f"PDF content:\n{text}"
    except Exception as e:
        return url, ""


def _extract_article(url: str) -> tuple[str, str]:
    """Extract article body text using trafilatura."""
    try:
        import trafilatura
        html = trafilatura.fetch_url(url)
        if not html:
            return url, ""
        text = trafilatura.extract(
            html,
            include_tables=False,
            include_comments=False,
            no_fallback=False,
        ) or ""
        return url, text[:3000]
    except Exception:
        return url, ""


def _enrich_tweet(tweet_text: str) -> tuple[str, str, str]:
    """
    Given full tweet text, find t.co URLs, resolve them, extract content.
    Returns (resolved_url, content_text, url_type).
    url_type: 'youtube' | 'pdf' | 'article' | 'tweet'
    """
    tco_urls = re.findall(r"https://t\.co/\S+", tweet_text)
    if not tco_urls:
        return "", "", "tweet"

    first_x_link = ""   # fallback: linked X tweet (video/post)

    # Try each t.co URL until we get useful external content
    for tco in tco_urls:
        final_url = _resolve_url(tco)
        if not final_url or final_url == tco:
            continue
        if _is_x_tweet(final_url):
            if not first_x_link:
                first_x_link = final_url  # save to use as link destination
            continue  # no external content to extract from another tweet
        if _is_youtube(final_url):
            resolved, content = _extract_youtube(final_url)
            return resolved, content, "youtube"
        if _is_pdf(final_url):
            resolved, content = _extract_pdf(final_url)
            if content:
                return resolved, content, "pdf"
        # Default: treat as article
        resolved, content = _extract_article(final_url)
        if content:
            return resolved, content, "article"
        return final_url, "", "article"

    # All links pointed to other X tweets — use the linked tweet as destination
    if first_x_link:
        return first_x_link, "", "x-video"

    return "", "", "tweet"


# ── Tweet parsing ──────────────────────────────────────────────────────────────

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
            legacy  = result.get("legacy", {})
            text    = legacy.get("full_text", "").strip()
            tid     = legacy.get("id_str") or result.get("rest_id", "")
            created = legacy.get("created_at", "")
            try:
                dt = datetime.strptime(created, "%a %b %d %H:%M:%S +0000 %Y").replace(tzinfo=timezone.utc)
                date_str = dt.strftime("%b %d, %H:%M")
            except Exception:
                dt, date_str = None, "recent"

            # Display text without trailing t.co URL
            display = re.sub(r"\s*https://t\.co/\S+$", "", text).strip()

            # Also grab card/URL metadata from the tweet payload (preview cards)
            card_title = ""
            card_desc  = ""
            card_url   = ""
            card = result.get("card", {}).get("legacy", {})
            if card:
                bvals = {b["key"]: b["value"] for b in card.get("binding_values", [])}
                card_title = (bvals.get("title", {}).get("string_value", "") or
                              bvals.get("app_name", {}).get("string_value", ""))
                card_desc  = bvals.get("description", {}).get("string_value", "")
                card_url   = bvals.get("card_url", {}).get("scribe_value", {}).get("value", "") or \
                             bvals.get("card_url", {}).get("string_value", "")

            tweets.append({
                "id":         tid,
                "text":       text,
                "display":    display,
                "dt":         dt,
                "date_str":   date_str,
                "card_title": card_title,
                "card_desc":  card_desc,
                "card_url":   card_url,
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


def _make_item(tweet: dict, resolved_url: str = "",
               content: str = "", url_type: str = "tweet") -> dict:
    display = tweet["display"]

    # Build a rich summary_raw: tweet text + extracted content
    # This feeds into Ollama for plain-English summarisation
    parts = [f"Tweet: {tweet['text']}"]
    if tweet.get("card_title"):
        parts.append(f"Linked content title: {tweet['card_title']}")
    if tweet.get("card_desc"):
        parts.append(f"Description: {tweet['card_desc']}")
    if content:
        parts.append(f"\n--- Content ({url_type}) ---\n{content[:2000]}")
    summary_raw = "\n".join(parts)

    # Use the resolved URL as the link (article, YouTube, PDF, or linked X video)
    # Fall back to the original tweet if nothing resolved
    if resolved_url:
        link = resolved_url
    else:
        link = f"https://x.com/i/web/status/{tweet['id']}"

    # For x-video and tweet types, the tweet text IS the content — keep the display
    title = display
    if tweet.get("card_title") and len(tweet["card_title"]) > 20 and url_type not in ("tweet", "x-video"):
        title = tweet["card_title"]

    return {
        "title":          title[:140] + ("…" if len(title) > 140 else ""),
        "link":           link,
        "summary_raw":    summary_raw,
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
        "read_time":      url_type,
        "url_type":       url_type,
    }


def fetch_bookmarks(max_total: int = 40, enrich: bool = True) -> list[dict]:
    """Fetch AI/ML bookmarks, optionally enriching by following links to
    extract article text, PDF content, or YouTube metadata."""
    if not os.environ.get("X_AUTH_TOKEN") or not os.environ.get("X_CT0"):
        return []

    seen  = set()
    items = []

    for query in _SEARCH_QUERIES:
        if len(items) >= max_total:
            break
        tweets = _search_bookmarks(query, count=20)
        for t in tweets:
            if t["id"] in seen:
                continue
            seen.add(t["id"])

            resolved_url = content = ""
            url_type = "tweet"
            if enrich:
                try:
                    resolved_url, content, url_type = _enrich_tweet(t["text"])
                except Exception:
                    pass

            items.append(_make_item(t, resolved_url, content, url_type))
            if len(items) >= max_total:
                break

    return items


if __name__ == "__main__":
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

    print("Testing X bookmarks fetch (with content enrichment)...")
    items = fetch_bookmarks(max_total=5, enrich=True)
    print(f"Got {len(items)} bookmarks")
    for i in items:
        print(f"\n[{i['url_type'].upper()}] {i['title'][:70]}")
        print(f"  Link: {i['link'][:80]}")
        print(f"  Content preview: {i['summary_raw'][7:200]}...")
