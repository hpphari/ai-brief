#!/usr/bin/env python3
"""Fetch LinkedIn company posts via Voyager API using li_at cookie.

Uses /feed/updates with companyFeedByUniversalName — posts come back in the
'included' array (not 'elements'), which is parsed with extract_texts().
"""

import os, re, time
from datetime import datetime, timezone, timedelta

_LI_AT = lambda: os.environ.get("LI_AT", "").strip()

_COMPANY_SLUGS = [
    "openai", "deepmind", "microsoft", "meta", "nvidia",
    "huggingface", "perplexity-ai", "mistral-ai",
    "amazon-web-services", "google", "anthropic",
]

_COLORS = {
    "anthropic":           "#f97316",
    "openai":              "#10b981",
    "deepmind":            "#4285f4",
    "microsoft":           "#00bcf2",
    "meta":                "#0668e1",
    "nvidia":              "#76b900",
    "huggingface":         "#fbbf24",
    "perplexity-ai":       "#a78bfa",
    "mistral-ai":          "#818cf8",
    "amazon-web-services": "#ff9900",
    "google":              "#34a853",
}

_AI_KEYWORDS = [
    "ai", "llm", "gpt", "claude", "gemini", "machine learning", "deep learning",
    "neural", "model", "agent", "artificial intelligence", "generative",
    "openai", "anthropic", "automation", "copilot", "chatgpt", "reasoning",
]

# LinkedIn UI strings to ignore when extracting text from included items
_UI_STRINGS = {
    "Copy link to post", "Hide this post",
    "You'll no longer see this post in your feed.", "Post removed",
    "Report post", "We appreciate you letting us know",
    "Thank you for your report", "Follow", "Unfollow", "Connect",
    "Message", "Save", "Like", "Comment", "Share", "Send",
    "View post", "See translation",
}


def _is_ai_related(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in _AI_KEYWORDS)


def _get_session():
    """Build a curl_cffi Chrome-impersonating session with li_at + real JSESSIONID."""
    try:
        from curl_cffi import requests as cr
    except ImportError:
        return None, None
    li_at = _LI_AT()
    if not li_at:
        return None, None
    s = cr.Session(impersonate="chrome")
    s.get("https://www.linkedin.com/",
          cookies={"li_at": li_at},
          headers={"accept": "text/html,application/xhtml+xml"},
          allow_redirects=True, timeout=15)
    jsessionid = s.cookies.get("JSESSIONID", "")
    return s, jsessionid.strip('"')


def _extract_texts(obj, depth=0):
    """Recursively collect non-UI text strings from a LinkedIn response object."""
    results = []
    if depth > 12:
        return results
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "text" and isinstance(v, str) and len(v) > 40 and v not in _UI_STRINGS:
                results.append(v)
            else:
                results.extend(_extract_texts(v, depth + 1))
    elif isinstance(obj, list):
        for i in obj:
            results.extend(_extract_texts(i, depth + 1))
    return results


def _make_item(text: str, url: str, source: str, color: str) -> dict:
    display = text.strip().replace("\n", " ")
    title   = display[:140] + ("…" if len(display) > 140 else "")
    return {
        "title":          title,
        "link":           url,
        "summary_raw":    text[:600],
        "date":           "recent",
        "date_raw":       None,
        "source":         source,
        "color":          color,
        "type":           "article",
        "category":       "linkedin",
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
        "read_time":      "LinkedIn",
    }


def fetch_company_posts(slug: str, color: str = "#0a66c2",
                        session=None, csrf: str = "",
                        max_posts: int = 5,
                        ai_only: bool = True) -> list[dict]:
    """Fetch recent posts from one LinkedIn company page."""
    if not _LI_AT():
        return []
    try:
        import requests as req_fallback
        sess = session
        if sess is None:
            from curl_cffi import requests as cr
            sess = cr.Session(impersonate="chrome")

        li_at = _LI_AT()
        headers = {
            "csrf-token":                  csrf or "ajax:0000000000000000",
            "x-restli-protocol-version":   "2.0.0",
            "accept":                      "application/vnd.linkedin.normalized+json+2.1",
            "referer":                     f"https://www.linkedin.com/company/{slug}/posts/",
        }

        r = sess.get(
            "https://www.linkedin.com/voyager/api/feed/updates",
            params={
                "companyUniversalName": slug,
                "q":                    "companyFeedByUniversalName",
                "moduleKey":            "member-share",
                "count":                max_posts * 2,
                "start":                0,
            },
            headers=headers,
            timeout=15,
        )

        if r.status_code != 200:
            return []

        d        = r.json()
        included = d.get("included", [])
        items    = []

        for item in included:
            if len(items) >= max_posts:
                break
            urn = item.get("dashEntityUrn", "")
            if "fsd_update:" not in urn or "fsd_updateActions" in urn:
                continue
            share_url = (item.get("socialContent") or {}).get("shareUrl", "")
            if not share_url:
                continue
            texts = _extract_texts(item)
            long_texts = [t for t in texts if len(t) > 60 and not t.startswith("http")]
            if not long_texts:
                continue
            # Use the longest text as the post body
            post_text = max(long_texts, key=len)
            if ai_only and not _is_ai_related(post_text):
                continue
            items.append(_make_item(
                text   = post_text,
                url    = share_url,
                source = f"LinkedIn: {slug}",
                color  = color,
            ))

        return items

    except Exception as e:
        print(f"  LinkedIn @{slug} error: {e}")
        return []


def fetch_linkedin(max_total: int = 30, ai_only: bool = True) -> list[dict]:
    """Main entry point — fetch from key AI company pages."""
    if not _LI_AT():
        return []

    session, csrf = _get_session()
    if session is None:
        print("  LinkedIn: curl_cffi not available — install with: pip install curl_cffi")
        return []

    items = []
    for slug in _COMPANY_SLUGS:
        if len(items) >= max_total:
            break
        color   = _COLORS.get(slug, "#0a66c2")
        fetched = fetch_company_posts(
            slug     = slug,
            color    = color,
            session  = session,
            csrf     = csrf,
            max_posts= 3,
            ai_only  = ai_only,
        )
        items.extend(fetched)
        time.sleep(0.4)

    return items[:max_total]


if __name__ == "__main__":
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

    print("Testing LinkedIn fetcher...")
    items = fetch_linkedin(max_total=10)
    print(f"Got {len(items)} posts")
    for i in items[:5]:
        print(f"  [{i['source']}] {i['title'][:70]}")
