#!/usr/bin/env python3
"""AI News Dashboard — global AI news, plain English, magazine layout."""

import feedparser
import requests
import os
import re
import sys
import webbrowser
import calendar
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

# Self-host RSSHub (https://docs.rsshub.app/deploy/) and set this env var for
# reliable X/Twitter feeds. Without it, rsshub.app public instance is used
# but may be rate-limited or require an X session cookie to work.
_RSSHUB = os.environ.get("RSSHUB_URL", "https://rsshub.app")

# ── Feeds ─────────────────────────────────────────────────────────────────────

FEEDS = {
    # Newsletters — no filter chip (show_chip:False); content absorbed into main feed
    "TLDR AI":          {"url": "https://bullrich.dev/tldr-rss/ai.rss",                                            "color": "#818cf8", "type": "newsletter", "category": "newsletter", "window_hours": 48,  "max_items": 5, "show_chip": False},
    "The Rundown AI":   {"url": "https://rss.beehiiv.com/feeds/2R3C6Bt5wj.xml",                                    "color": "#38bdf8", "type": "newsletter", "category": "newsletter", "window_hours": 48,  "max_items": 3, "show_chip": False},
    "Ben's Bites":      {"url": "https://bensbites.beehiiv.com/feed",                                              "color": "#34d399", "type": "newsletter", "category": "newsletter", "window_hours": 48,  "max_items": 3, "show_chip": False},
    # AI Labs — 14-day window so we capture current + previous releases
    # Anthropic removed their RSS feed — covered via HN (every Claude release hits front page)
    "Anthropic":        {"url": "https://hnrss.org/newest?q=Anthropic+OR+Claude+AI+OR+Claude+Fable+OR+Claude+Sonnet+OR+Claude+Opus+OR+MCP+Anthropic&points=20", "color": "#f97316", "type": "article", "category": "lab", "window_hours": 168, "max_items": 10},
    "OpenAI":           {"url": "https://openai.com/news/rss.xml",                                                 "color": "#10b981", "type": "article",    "category": "lab",        "window_hours": 336, "max_items": 10},
    "Google AI":        {"url": "https://blog.google/technology/ai/rss/",                                          "color": "#4285f4", "type": "article",    "category": "lab",        "window_hours": 336, "max_items": 10},
    "DeepMind":         {"url": "https://deepmind.google/discover/blog/rss/",                                      "color": "#1a73e8", "type": "article",    "category": "lab",        "window_hours": 336, "max_items": 10},
    "Microsoft AI":     {"url": "https://blogs.microsoft.com/ai/feed/",                                            "color": "#00bcf2", "type": "article",    "category": "lab",        "window_hours": 336, "max_items": 10},
    "Meta AI":          {"url": "https://engineering.fb.com/category/ai-research/feed/",                           "color": "#0668e1", "type": "article",    "category": "lab",        "window_hours": 336, "max_items": 10},
    "Apple ML":         {"url": "https://machinelearning.apple.com/rss.xml",                                       "color": "#8e8e93", "type": "article",    "category": "lab",        "window_hours": 336, "max_items": 10},
    # xAI/Grok and Perplexity block all bots (403) — HN community feed is the only reliable source.
    # Stories from TechCrunch/Verge will also carry their news tagged via re: badge.
    "xAI / Grok":       {"url": "https://hnrss.org/newest?q=Grok+OR+xAI+OR+%22x.ai%22+OR+%22Grok+4%22+OR+%22Grok+3%22&points=15", "color": "#60a5fa", "type": "article", "category": "lab", "window_hours": 168, "max_items": 8},
    "Perplexity":       {"url": "https://hnrss.org/newest?q=%22Perplexity+AI%22+OR+%22Perplexity+search%22+OR+%22Sonar+model%22&points=15", "color": "#a78bfa", "type": "article", "category": "lab", "window_hours": 168, "max_items": 8},
    "Google Research":  {"url": "https://research.google/blog/rss/",                                               "color": "#34a853", "type": "article",    "category": "lab",        "window_hours": 168, "max_items": 7},
    "Hugging Face":     {"url": "https://huggingface.co/blog/feed.xml",                                            "color": "#fbbf24", "type": "article",    "category": "lab",        "window_hours": 168, "max_items": 7},
    "NVIDIA AI":        {"url": "https://blogs.nvidia.com/blog/category/generative-ai/feed/",                      "color": "#76b900", "type": "article",    "category": "lab",        "window_hours": 168, "max_items": 7},
    # Industry news
    "VentureBeat AI":   {"url": "https://venturebeat.com/feed",                                                    "color": "#c084fc", "type": "article",    "category": "news",       "window_hours": 120, "max_items": 7},
    "TechCrunch AI":    {"url": "https://techcrunch.com/category/artificial-intelligence/feed/",                   "color": "#0d9488", "type": "article",    "category": "news",       "window_hours": 72,  "max_items": 7},
    "Hacker News":      {"url": "https://hnrss.org/newest?q=AI+OR+LLM+OR+Claude+OR+GPT+OR+Gemini+OR+Grok&points=100", "color": "#fb923c", "type": "article", "category": "news",    "window_hours": 48,  "max_items": 7},
    # YouTube AI creators — free native RSS, no API key needed
    # To add more channels run: python3 sync_youtube.py
    "Varun Mayya":          {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCsQoiOrh7jzKmE8NBofhTnQ", "color": "#f97316", "type": "video", "category": "creator", "window_hours": 336, "max_items": 5},
    "Vaibhav Sisinty":      {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=UClXAalunTPaX1YV185DWUeg", "color": "#eab308", "type": "video", "category": "creator", "window_hours": 336, "max_items": 5},
    "Dan Martell":          {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCA-mWX9CvCTVFWRMb9bKc9w", "color": "#22c55e", "type": "video", "category": "creator", "window_hours": 336, "max_items": 5},
    "Alberta Tech":         {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCkdgAA0rfK7lG5dv4o__Paw", "color": "#60a5fa", "type": "video", "category": "creator", "window_hours": 336, "max_items": 5},
    "Doctor AI":            {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCOJp1lsu9vCF-TllwMzcCLg", "color": "#e879f9", "type": "video", "category": "creator", "window_hours": 336, "max_items": 5},
    "AI Adventurer":        {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=UC0VVp_uuSWvrfRPZ6HKiKqw", "color": "#34d399", "type": "video", "category": "creator", "window_hours": 336, "max_items": 5},
    "Underfitted":          {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCgLxmJ8xER7Y7sywMN5SfWg", "color": "#a78bfa", "type": "video", "category": "creator", "window_hours": 336, "max_items": 5},
    "AI Explained":         {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCNJ1Ymd5yFuUPtn21xtRbbw", "color": "#818cf8", "type": "video", "category": "creator", "window_hours": 336, "max_items": 5},
    "Matt Wolfe":           {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=UChpleBmo18P08aKCIgti38g", "color": "#c084fc", "type": "video", "category": "creator", "window_hours": 336, "max_items": 5},
    "Fireship":             {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=UC2Xd-TjJByJyK2w1zNwY0zQ", "color": "#f43f5e", "type": "video", "category": "creator", "window_hours": 336, "max_items": 5},
    "Lex Fridman":          {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCJIfeSCssxSC_Dhc5s7woww", "color": "#64748b", "type": "video", "category": "creator", "window_hours": 336, "max_items": 3},
    "Two Minute Papers":    {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCbfYPyITQ-7l4upoX8nvctg", "color": "#06b6d4", "type": "video", "category": "creator", "window_hours": 336, "max_items": 5},
    "DeepLearning.AI":      {"url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCcIXc5mJsHVYTZR1maL5l9w", "color": "#0ea5e9", "type": "video", "category": "creator", "window_hours": 336, "max_items": 5},
    # X / Twitter accounts — via RSSHub (set RSSHUB_URL env var for self-hosted instance)
    "X: ai_rohitt":      {"url": f"{_RSSHUB}/twitter/user/ai_rohitt",      "color": "#f43f5e", "type": "article", "category": "x", "window_hours": 48, "max_items": 8},
    "X: vaibhavsisinty": {"url": f"{_RSSHUB}/twitter/user/vaibhavsisinty", "color": "#38bdf8", "type": "article", "category": "x", "window_hours": 48, "max_items": 5},
    "X: VarunMayya":     {"url": f"{_RSSHUB}/twitter/user/VarunMayya",     "color": "#818cf8", "type": "article", "category": "x", "window_hours": 48, "max_items": 5},
    "X: danmartell":     {"url": f"{_RSSHUB}/twitter/user/danmartell",     "color": "#34d399", "type": "article", "category": "x", "window_hours": 48, "max_items": 5},
    "X: AnthropicAI":    {"url": f"{_RSSHUB}/twitter/user/AnthropicAI",    "color": "#f97316", "type": "article", "category": "x", "window_hours": 48, "max_items": 5},
    "X: OpenAI":         {"url": f"{_RSSHUB}/twitter/user/openai",         "color": "#10b981", "type": "article", "category": "x", "window_hours": 48, "max_items": 5},
    "X: GoogleDeepMind": {"url": f"{_RSSHUB}/twitter/user/GoogleDeepMind", "color": "#1a73e8", "type": "article", "category": "x", "window_hours": 48, "max_items": 5},
    "X: LangChain":      {"url": f"{_RSSHUB}/twitter/user/LangChainAI",    "color": "#a78bfa", "type": "article", "category": "x", "window_hours": 48, "max_items": 5},
    "X: googlegemini":   {"url": f"{_RSSHUB}/twitter/user/googlegemini",   "color": "#4285f4", "type": "article", "category": "x", "window_hours": 48, "max_items": 5},
    "X: perplexity_ai":  {"url": f"{_RSSHUB}/twitter/user/perplexity_ai",  "color": "#c084fc", "type": "article", "category": "x", "window_hours": 48, "max_items": 5},
    "X: claudeai":       {"url": f"{_RSSHUB}/twitter/user/claudeai",       "color": "#fb923c", "type": "article", "category": "x", "window_hours": 48, "max_items": 5},
    "X: karpathy":       {"url": f"{_RSSHUB}/twitter/user/karpathy",       "color": "#fbbf24", "type": "article", "category": "x", "window_hours": 48, "max_items": 8},
    "X: sama":           {"url": f"{_RSSHUB}/twitter/user/sama",           "color": "#10b981", "type": "article", "category": "x", "window_hours": 48, "max_items": 5},
    "X: DarioAmodei":    {"url": f"{_RSSHUB}/twitter/user/DarioAmodei",    "color": "#f97316", "type": "article", "category": "x", "window_hours": 48, "max_items": 5},
    "X: swyx":           {"url": f"{_RSSHUB}/twitter/user/swyx",           "color": "#34d399", "type": "article", "category": "x", "window_hours": 48, "max_items": 8},
    "X: rowancheung":    {"url": f"{_RSSHUB}/twitter/user/rowancheung",    "color": "#38bdf8", "type": "article", "category": "x", "window_hours": 48, "max_items": 8},
    "X: emollick":       {"url": f"{_RSSHUB}/twitter/user/emollick",       "color": "#e879f9", "type": "article", "category": "x", "window_hours": 48, "max_items": 8},
}

MAX_PER_SOURCE = 7  # fallback if max_items not set
OLLAMA_URL     = "http://localhost:11434/api/generate"
OLLAMA_MODEL   = "llama3.2:1b"

# ── Story classification ───────────────────────────────────────────────────────

STORY_TYPE_CONFIG = {
    "release":    {"label": "New Release",        "emoji": "🚀", "color": "#f59e0b", "bg": "#451a03"},
    "investment": {"label": "Funding & Deals",    "emoji": "💰", "color": "#10b981", "bg": "#052e16"},
    "research":   {"label": "Research",           "emoji": "🔬", "color": "#a78bfa", "bg": "#2e1065"},
    "product":    {"label": "Product Update",     "emoji": "📦", "color": "#38bdf8", "bg": "#082f49"},
    "policy":     {"label": "Policy & Safety",    "emoji": "🏛️", "color": "#fb7185", "bg": "#4c0519"},
    "enterprise": {"label": "Enterprise AI",      "emoji": "🏢", "color": "#818cf8", "bg": "#1e1b4b"},
    "general":    {"label": "Industry News",      "emoji": "📰", "color": "#94a3b8", "bg": "#1e293b"},
    "video":      {"label": "YouTube Video",      "emoji": "▶️",  "color": "#ef4444", "bg": "#1a0000"},
}

def classify_story(item):
    if item.get("is_release"):
        return "release"
    text = (item["title"] + " " + item["summary_raw"]).lower()
    if any(k in text for k in ["billion", "million", "invest", "fund", "raises", "valuation", "ipo", "s-1", "acquisition", "deal"]):
        return "investment"
    if any(k in text for k in ["regulat", "law", "policy", "ban", "congress", "eu ai act", "senate", "ruling", "court", "safety", "harm"]):
        return "policy"
    if any(k in text for k in ["research paper", "arxiv", "study finds", "benchmark", "university", "scientists", "published"]):
        return "research"
    if any(k in text for k in ["enterprise", "business deploy", "customer", "partnership", "integration", "workflow"]):
        return "enterprise"
    if any(k in text for k in ["update", "new feature", "improves", "new version", "upgraded", "redesign"]):
        return "product"
    return "general"

# ── Subject detection — what company/topic is this story actually ABOUT ───────

COMPANY_SUBJECTS = {
    # Order matters: more specific patterns first
    "Anthropic":   ["anthropic", "claude", "fable", "mythos", "claude code"],
    "OpenAI":      ["openai", "chatgpt", "gpt-4", "gpt-5", "gpt4", "codex", "dall-e", "sora", "o1", "o3", "o4"],
    "Google":      ["google", "gemini", "deepmind", "bard", "vertex ai", "google ai", "google search"],
    "Microsoft":   ["microsoft", "copilot", "azure ai", "bing ai", "phi-4", "phi-3"],
    "Meta":        ["meta ai", "llama 4", "llama4", "llama 3", " llama ", "facebook ai"],
    "Apple":       ["apple intelligence", "apple's ai", "apple ai", "siri ai", "apple ml", "foundation model"],
    "xAI":         ["grok 4", "grok 3", "grok 2", " grok ", "xai ", "x.ai", "elon's ai", "elon musk's ai"],
    "Perplexity":  ["perplexity ai", "perplexity search", "perplexity's", "sonar model", "perplexity pro"],
    "NVIDIA":      ["nvidia", " nemo", "cuda ai"],
    "Hugging Face":["hugging face", "huggingface"],
    "Mistral":     ["mistral", "le chat"],
    "DeepSeek":    ["deepseek"],
    "Cohere":      ["cohere", "command r"],
}

def detect_about(item):
    """Return the company this story is primarily about, or None."""
    # Weight title 3× more than body snippet
    text = (item["title"] + " ") * 3 + item["summary_raw"][:400]
    text = text.lower()
    scores = {}
    for company, patterns in COMPANY_SUBJECTS.items():
        score = sum(text.count(p) for p in patterns)
        if score:
            scores[company] = score
    if not scores:
        return None
    return max(scores, key=scores.get)

# ── Trending detection ─────────────────────────────────────────────────────────

TRENDING_ENTITIES = [
    "claude", "fable", "anthropic", "openai", "gpt", "chatgpt", "codex",
    "gemini", "google", "deepmind", "microsoft", "copilot", "meta", "llama",
    "apple", "siri", "grok", "xai", "perplexity", "hugging face",
    "nvidia", "mistral", "cohere", "deepseek",
]

def detect_trending(items):
    entity_map = defaultdict(list)
    for item in items:
        t = item["title"].lower()
        for entity in TRENDING_ENTITIES:
            if entity in t:
                entity_map[entity].append(item)
    for entity, matched in entity_map.items():
        if len({i["source"] for i in matched}) >= 2:
            for item in matched:
                item["trending"] = True
                if not item.get("trending_for"):
                    item["trending_for"] = entity.title()

# ── Release detection ──────────────────────────────────────────────────────────

RELEASE_TITLE_SIGNALS = [
    "introduc", "announc", "launch", "now available",
    "new model", "new api", "next-gen", "next gen", "unveil", "debut",
]
RELEASE_BODY_SIGNALS = [
    "model", "api", "version", "claude", "gpt", "gemini", "grok",
    "llama", "mistral", "phi", " v1", " v2", " v3", " v4",
    "2.0", "3.0", "4.0", "5.0", "turbo", "ultra", "pro", "mini",
]
RELEASE_NEGATIVES = [
    r"\(\d{4}\)", r"^\s*why\b", r"^\s*how\b", r"^\s*what\b",
    r"\bexplained\b", r"\bcase study\b", r"\bhistory of\b", r"\bretrospective\b",
]
MODEL_PREDECESSORS = {
    "fable":         ("Claude Opus 4.8",           "Anthropic"),
    "opus 4.8":      ("Claude 3 Opus",             "Anthropic"),
    "sonnet 4.6":    ("Claude 3.5 Sonnet",         "Anthropic"),
    "haiku 4.5":     ("Claude 3.5 Haiku",          "Anthropic"),
    "claude 4":      ("Claude 3.5",                "Anthropic"),
    "claude 3.7":    ("Claude 3.5",                "Anthropic"),
    "gpt-5":         ("GPT-4o",                    "OpenAI"),
    "o4":            ("o3",                        "OpenAI"),
    "o3":            ("o1",                        "OpenAI"),
    "gpt-4.5":       ("GPT-4o",                    "OpenAI"),
    "gemini 2.5":    ("Gemini 2.0",                "Google"),
    "gemini 2.0":    ("Gemini 1.5 Pro",            "Google"),
    "grok 4":        ("Grok 3",                    "xAI"),
    "grok 3":        ("Grok 2",                    "xAI"),
    "llama 4":       ("Llama 3.3",                 "Meta"),
    "phi-4":         ("Phi-3",                     "Microsoft"),
    "phi 4":         ("Phi-3",                     "Microsoft"),
    "deepseek v3":   ("DeepSeek V2",               "DeepSeek"),
    "mistral large": ("Mistral Medium",            "Mistral"),
}

def detect_release(item):
    title = item["title"].lower()
    combined = title + " " + item["summary_raw"].lower()
    if not (any(s in title for s in RELEASE_TITLE_SIGNALS)
            and any(s in combined for s in RELEASE_BODY_SIGNALS)):
        return False, None
    for pat in RELEASE_NEGATIVES:
        if re.search(pat, item["title"], re.IGNORECASE):
            return False, None
    for key, (prev, company) in MODEL_PREDECESSORS.items():
        if key in combined:
            return True, (prev, company)
    return True, None

# ── Scoring ────────────────────────────────────────────────────────────────────

INTEREST_KW   = ["claude", "anthropic", "mcp", "model context protocol", "langgraph",
                  "langchain", "agent", "agents", "agentic", "enterprise", "llm",
                  "tool use", "multi-agent", "orchestration", "gpt", "openai", "gemini",
                  "deployment", "microsoft", "grok", "perplexity"]
HIGH_INTEREST = ["claude", "mcp", "model context protocol", "langgraph", "agents",
                 "agentic", "multi-agent", "tool use"]

def score_item(item):
    text = (item["title"] + " " + item["summary_raw"]).lower()
    s = 1.0
    if item.get("is_release"):  s += 2.0
    if item.get("trending"):    s += 1.0
    for kw in INTEREST_KW:
        if kw in text: s += 0.4
    for kw in HIGH_INTEREST:
        if kw in text: s += 0.6
    return min(5, round(s))

# ── Feed fetching ──────────────────────────────────────────────────────────────

def parse_date(entry):
    for attr in ("published", "updated"):
        raw = getattr(entry, attr, None)
        if raw:
            try:
                dt = parsedate_to_datetime(raw)
                return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
            except Exception:
                pass
    for attr in ("published_parsed", "updated_parsed"):
        s = getattr(entry, attr, None)
        if s:
            try:
                return datetime.fromtimestamp(calendar.timegm(s), tz=timezone.utc)
            except Exception:
                pass
    return None

def clean_html(text):
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def fetch_feed(name, config):
    cutoff   = datetime.now(timezone.utc) - timedelta(hours=config.get("window_hours", 48))
    max_n    = config.get("max_items", MAX_PER_SOURCE)
    items    = []
    try:
        try:
            resp = requests.get(config["url"], allow_redirects=True, timeout=15,
                                headers={"User-Agent": "feedparser/6.0"})
            feed = feedparser.parse(resp.content)
        except Exception:
            feed = feedparser.parse(config["url"])
        for entry in feed.entries:
            dt = parse_date(entry)
            if dt and dt < cutoff:
                continue
            title   = getattr(entry, "title", "(no title)").strip()
            link    = getattr(entry, "link", "")
            raw     = getattr(entry, "summary", "") or getattr(entry, "description", "") or ""
            summary = clean_html(raw)[:2500]
            items.append({
                "title":               title,
                "link":                link,
                "summary_raw":         summary,
                "date":                dt.strftime("%b %d, %H:%M") if dt else "recent",
                "date_raw":            dt,          # raw datetime for timeline sorting
                "source":              name,
                "color":               config["color"],
                "type":                config["type"],
                "category":            config.get("category", "news"),
                "show_chip":           config.get("show_chip", True),
                "ai_summary":          None,
                "story_type":          "general",
                "is_release":          False,
                "predecessor":         None,
                "release_order_label": None,        # "Latest Release", "Previous", etc.
                "about":               None,         # primary company this story is about
                "trending":            False,
                "trending_for":        None,
                "score":               1,
            })
            if len(items) >= max_n:
                break
    except Exception as e:
        print(f"  [warn] {name}: {e}", file=sys.stderr)
    return items

# ── Ollama ─────────────────────────────────────────────────────────────────────

def ollama_available():
    try:
        return requests.get("http://localhost:11434/api/tags", timeout=3).status_code == 200
    except Exception:
        return False

def ollama_generate(prompt, timeout=120):
    try:
        r = requests.post(OLLAMA_URL,
                          json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
                          timeout=timeout)
        if r.status_code == 200:
            return r.json().get("response", "").strip()
    except Exception:
        pass
    return None

def summarize_newsletter(item):
    prompt = (
        "Summarize these AI news updates for someone who uses AI tools daily but is NOT a developer.\n"
        "Write 3 bullet points. Each bullet must:\n"
        "  - Use plain everyday language (no jargon like 'inference', 'parameters', 'tokens')\n"
        "  - Say what happened AND why it matters to regular AI users\n"
        "  - Be under 20 words\n"
        "Skip ads, sponsor content, job listings, and promotions.\n\n"
        f"Title: {item['title']}\nContent: {item['summary_raw']}\n\n"
        "Output ONLY the 3 bullets, each starting with •"
    )
    return ollama_generate(prompt)

def summarize_article(item):
    prompt = (
        "Explain this AI news story in 1–2 simple sentences for someone who uses AI tools "
        "like ChatGPT or Claude but is not a developer.\n"
        "- Use everyday language. Replace jargon: 'responds faster' not 'low latency', "
        "'reads long documents' not 'large context window'.\n"
        "- Say what happened and why it matters to people who use AI.\n\n"
        f"Title: {item['title']}\nContent: {item['summary_raw']}\n\n"
        "Output only the 1–2 sentences. No bullet points."
    )
    return ollama_generate(prompt)

def summarize_release(item):
    pred = item.get("predecessor")
    ctx = f"The previous version was {pred[0]} by {pred[1]}. " if pred else ""

    prompt = (
        f"Explain this new AI product launch in plain English for someone who uses AI tools daily.\n"
        f"{ctx}"
        "Translate ALL technical terms into real-world meaning:\n"
        "  - 'faster response time' → 'replies to you faster'\n"
        "  - 'larger context window' → 'can read much longer documents at once'\n"
        "  - 'improved benchmark scores' → 'makes fewer mistakes and reasons better'\n"
        "  - 'lower cost per token' → 'cheaper to use'\n\n"
        f"Title: {item['title']}\nContent: {item['summary_raw']}\n\n"
        "Respond in this EXACT format:\n"
        "WHAT: [one sentence — what was released and by whom]\n"
        "• [real-world improvement #1 vs the old version]\n"
        "• [real-world improvement #2]\n"
        "• [real-world improvement #3]\n"
        "WHO: [one sentence — what kind of person or team benefits most]\n"
    )
    return ollama_generate(prompt, timeout=150)

def summarize_video(item):
    prompt = (
        "Based on this YouTube video title, write 1 sentence explaining what AI topic this video covers "
        "and why someone who uses AI tools daily should watch it. Plain English only.\n\n"
        f"Channel: {item['source']}\nTitle: {item['title']}\n\n"
        "Output only the 1 sentence."
    )
    return ollama_generate(prompt)

def top3_summary(items):
    top = sorted(items, key=lambda x: x["score"], reverse=True)[:8]
    lines = "\n".join(f"- {i['title']}" for i in top)
    prompt = (
        "Write a 3-sentence morning briefing about AI news for someone who uses AI at work "
        "but is not a developer. Plain English only.\n\n"
        "1. The biggest thing that happened today in AI (new product, big announcement, etc.)\n"
        "2. The most interesting trend or competitive move between the big AI companies\n"
        "3. One practical takeaway — something useful for someone who relies on AI tools daily\n\n"
        f"Today's headlines:\n{lines}\n\n"
        "Output only the 3 sentences, numbered 1. 2. 3."
    )
    return ollama_generate(prompt, timeout=120)

# ── HTML ───────────────────────────────────────────────────────────────────────

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI Today — {date}</title>
<style>
:root{{
  --bg:#0d0f1a;--s1:#13152a;--s2:#1a1d35;--s3:#212540;
  --border:#2a2d4a;--text:#e8eaf6;--muted:#7986cb;
  --r:12px;
  --amber:#f59e0b;--amber-bg:#1c1202;
  --blue:#60a5fa;--green:#34d399;--red:#f87171;
  --purple:#c084fc;--cyan:#67e8f9;
}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,sans-serif;font-size:15px;line-height:1.6;min-height:100vh}}

/* ── Sticky nav ── */
nav{{position:sticky;top:0;z-index:100;background:rgba(13,15,26,.92);backdrop-filter:blur(12px);border-bottom:1px solid var(--border);padding:12px 28px;display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}}
.nav-brand{{display:flex;align-items:center;gap:10px}}
.nav-brand h1{{font-size:1.1rem;font-weight:800;letter-spacing:-.02em;background:linear-gradient(135deg,#818cf8,#c084fc);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
.nav-meta{{font-size:.75rem;color:var(--muted)}}
.stat-pills{{display:flex;gap:6px}}
.stat-pill{{padding:3px 10px;border-radius:999px;font-size:.72rem;font-weight:700;border:1px solid var(--border)}}

/* ── Filter bar ── */
.filter-bar{{padding:8px 28px;display:flex;flex-direction:column;gap:7px;border-bottom:1px solid var(--border);background:var(--s1)}}
.filter-row{{display:flex;flex-wrap:wrap;gap:6px;align-items:center}}
.filter-label{{font-size:.68rem;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);width:80px;flex-shrink:0}}
.chip{{padding:4px 12px;border-radius:999px;font-size:.75rem;font-weight:600;cursor:pointer;border:1.5px solid transparent;transition:all .15s;user-select:none;white-space:nowrap}}
.chip.on{{border-color:rgba(255,255,255,.55);opacity:1}}
.chip.off{{opacity:.28}}
.chip-sep{{width:1px;background:var(--border);margin:0 4px;align-self:stretch}}

/* ── Page body ── */
.page{{max-width:1320px;margin:0 auto;padding:28px 28px 60px}}

/* ── Morning brief ── */
.brief{{background:linear-gradient(135deg,#1a1b2e,#1e1b3a);border:1px solid #3730a3;border-radius:var(--r);padding:24px 28px;margin-bottom:28px;border-left:4px solid #818cf8}}
.brief-label{{font-size:.7rem;font-weight:800;text-transform:uppercase;letter-spacing:.1em;color:#818cf8;margin-bottom:10px}}
.brief-text{{font-size:1rem;line-height:1.85;color:#c7d2fe}}
.brief-text p{{margin-bottom:.5em}}

/* ── Section headers ── */
.section-head{{display:flex;align-items:center;gap:10px;margin-bottom:16px;margin-top:32px}}
.section-head h2{{font-size:.8rem;font-weight:800;text-transform:uppercase;letter-spacing:.1em}}
.section-head .dot{{width:6px;height:6px;border-radius:50%;flex-shrink:0}}
.section-count{{font-size:.72rem;color:var(--muted);padding:1px 8px;background:var(--s2);border-radius:999px;border:1px solid var(--border)}}
.section-divider{{flex:1;height:1px;background:var(--border)}}

/* ── Grids ── */
.grid-releases{{display:grid;grid-template-columns:repeat(auto-fill,minmax(380px,1fr));gap:16px;margin-bottom:8px}}
.grid-trending{{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:14px;margin-bottom:8px}}
.grid-all{{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:14px}}

/* ── Cards ── */
.card{{background:var(--s1);border:1px solid var(--border);border-radius:var(--r);padding:18px 20px;transition:transform .12s,box-shadow .12s;cursor:default;display:flex;flex-direction:column;gap:10px}}
.card:hover{{transform:translateY(-3px);box-shadow:0 8px 32px rgba(0,0,0,.4)}}

/* Release card */
.card-release{{background:var(--amber-bg);border-color:#78350f;box-shadow:0 0 0 1px #92400e33}}
.card-release:hover{{box-shadow:0 8px 32px rgba(245,158,11,.15)}}

/* Trending card */
.card-trending{{background:#0f1a2e;border-color:#1e3a5f}}
.card-trending:hover{{box-shadow:0 8px 32px rgba(96,165,250,.12)}}

/* Card internals */
.card-top{{display:flex;justify-content:space-between;align-items:flex-start;gap:10px}}
.card-title{{font-size:.95rem;font-weight:700;line-height:1.4;flex:1}}
.card-title a{{color:var(--text);text-decoration:none}}
.card-title a:hover{{color:#818cf8}}
.card-score{{flex-shrink:0;font-size:.72rem;font-weight:700;padding:3px 8px;border-radius:6px;background:var(--s2);border:1px solid var(--border);white-space:nowrap}}
.score-5{{color:#34d399;border-color:#064e3b}}
.score-4{{color:#a3e635;border-color:#1a2e05}}
.score-3{{color:#fbbf24;border-color:#451a03}}
.score-low{{color:var(--muted)}}

.card-badges{{display:flex;flex-wrap:wrap;gap:5px;align-items:center}}
.badge{{display:inline-flex;align-items:center;gap:3px;padding:2px 9px;border-radius:999px;font-size:.68rem;font-weight:700;white-space:nowrap}}
.badge-trending{{background:#1e3a5f;color:#93c5fd;border:1px solid #1d4ed8}}
.badge-type{{border:1px solid currentColor;background:transparent;opacity:.85}}

.card-meta{{font-size:.73rem;color:var(--muted);display:flex;gap:8px;align-items:center}}
.card-meta-dot{{opacity:.4}}

.card-summary{{font-size:.875rem;color:#c7d2fe;line-height:1.7;background:var(--s2);border-radius:8px;padding:12px 14px}}
.card-summary ul{{padding-left:14px;display:flex;flex-direction:column;gap:4px}}
.card-summary li{{list-style:none;padding-left:0}}
.card-summary li::before{{content:"→ ";color:var(--muted)}}

/* Release summary */
.rel-what{{font-size:.83rem;color:#fef3c7;margin-bottom:8px;font-style:italic}}
.rel-bullets{{display:flex;flex-direction:column;gap:5px;margin-bottom:8px}}
.rel-bullet{{font-size:.83rem;color:#e8eaf6;display:flex;gap:7px}}
.rel-bullet::before{{content:"✓";color:#f59e0b;font-weight:700;flex-shrink:0}}
.rel-who{{font-size:.78rem;color:#6ee7b7;padding-top:6px;border-top:1px solid #78350f}}

.no-summary{{font-size:.78rem;color:var(--muted);font-style:italic}}

/* ── Ollama warning ── */
.ollama-warn{{background:#1c0a00;border:1px solid #7c2d12;border-radius:var(--r);padding:14px 18px;font-size:.85rem;color:#fcd34d;margin-bottom:24px;display:flex;gap:10px;align-items:flex-start}}

/* ── Empty state ── */
.empty{{color:var(--muted);font-size:.85rem;padding:20px;text-align:center;background:var(--s1);border-radius:var(--r);border:1px dashed var(--border)}}
</style>
</head>
<body>

<nav>
  <div class="nav-brand">
    <h1>AI Today</h1>
    <span class="nav-meta">{date}</span>
  </div>
  <div class="stat-pills">
    <span class="stat-pill" style="color:#f59e0b;border-color:#78350f">{releases} releases</span>
    <span class="stat-pill" style="color:#60a5fa;border-color:#1e3a5f">{trending_count} trending</span>
    <span class="stat-pill" style="color:var(--muted)">{count} stories · {sources} sources</span>
  </div>
</nav>

<div class="filter-bar">
  <div class="filter-row">
    <span class="filter-label">View</span>
    <span class="chip on"  data-f="all"      style="background:#1e293b;color:#e2e8f0">All</span>
    <span class="chip off" data-f="__rel__"  style="background:#78350f22;color:#fef3c7;border-color:#78350f">🚀 Releases</span>
    <span class="chip off" data-f="__trend__" style="background:#1e3a5f22;color:#bfdbfe;border-color:#1e3a5f">🔥 Trending</span>
  </div>
  <div class="filter-row">
    <span class="filter-label">Companies</span>
    {lab_chips}
  </div>
  <div class="filter-row">
    <span class="filter-label">News</span>
    {news_chips}
  </div>
  {creator_row}
  {x_row}
</div>

<div class="page">

{brief_block}
{warn_block}

<!-- What's New Today -->
<div id="sec-releases">{releases_block}</div>

<!-- Trending Now -->
<div id="sec-trending">{trending_block}</div>

<!-- All Stories -->
<div id="sec-all">
<div class="section-head">
  <span class="dot" style="background:var(--muted)"></span>
  <h2 style="color:var(--muted)">All Stories</h2>
  <span class="section-count">{count} items</span>
  <span class="section-divider"></span>
</div>
<div class="grid-all" id="all-grid">
  {all_cards}
</div>
</div>

</div><!-- /page -->

<script>
(function(){{
  const chips     = document.querySelectorAll('.chip[data-f]');
  const allCards  = Array.from(document.querySelectorAll('.card[data-src]'));
  const secRel    = document.getElementById('sec-releases');
  const secTrend  = document.getElementById('sec-trending');
  const secAll    = document.getElementById('sec-all');

  function show(el)  {{ if(el) el.style.display = ''; }}
  function hide(el)  {{ if(el) el.style.display = 'none'; }}
  function hasVisible(sec) {{
    return sec && [...sec.querySelectorAll('.card')].some(c => c.style.display !== 'none');
  }}

  function applyFilter(f) {{
    // Update chip styles
    chips.forEach(c => {{
      c.classList.toggle('on',  c.dataset.f === f);
      c.classList.toggle('off', c.dataset.f !== f);
    }});

    if (f === 'all') {{
      // Show every section and every card
      show(secRel); show(secTrend); show(secAll);
      allCards.forEach(c => c.style.display = '');

    }} else if (f === '__rel__') {{
      // Releases section only — hide trending + all-stories
      show(secRel); hide(secTrend); hide(secAll);
      // Inside releases section show all cards
      allCards.forEach(c => c.style.display = '');

    }} else if (f === '__trend__') {{
      // Trending section only — show ONLY trending cards, hide releases + all-stories
      hide(secRel); show(secTrend); hide(secAll);
      allCards.forEach(c => {{
        c.style.display = c.dataset.trend === '1' ? '' : 'none';
      }});
      // Hide trending section if empty (no trending items exist)
      if (!hasVisible(secTrend)) hide(secTrend);

    }} else {{
      // Source filter — show all sections, filter cards to that source
      show(secRel); show(secTrend); show(secAll);
      allCards.forEach(c => {{
        c.style.display = c.dataset.src === f ? '' : 'none';
      }});
      // Hide sections that have no visible cards for this source
      if (!hasVisible(secRel))    hide(secRel);
      if (!hasVisible(secTrend))  hide(secTrend);
      // Re-sort all-grid by date (newest first) when source selected
      const grid = document.getElementById('all-grid');
      if (grid) {{
        const visible = [...grid.querySelectorAll('.card')].filter(c => c.style.display !== 'none');
        visible.sort((a,b) => parseInt(b.dataset.ts||0) - parseInt(a.dataset.ts||0));
        visible.forEach(c => grid.appendChild(c));
      }}
    }}
  }}

  chips.forEach(c => c.addEventListener('click', () => applyFilter(c.dataset.f)));
}})();
</script>
</body>
</html>"""


# ── Render helpers ─────────────────────────────────────────────────────────────

def score_cls(s):
    if s >= 5: return "score-5"
    if s >= 4: return "score-4"
    if s >= 3: return "score-3"
    return "score-low"

def star_str(s):
    return "★" * s + "☆" * (5 - s)

def esc(t):
    return t.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")

def render_summary(item):
    s = item.get("ai_summary")
    if not s:
        return '<p class="no-summary">Summary unavailable — Ollama offline</p>'
    if item.get("is_release"):
        return _render_release(s, item)
    if item["type"] == "newsletter":
        return _render_bullets(s)
    return f'<div class="card-summary">{esc(s)}</div>'

def _render_bullets(s):
    lines = [l.strip().lstrip("•-").strip() for l in s.split("\n") if l.strip().startswith(("•", "-"))]
    if not lines:
        lines = [l.strip() for l in s.split("\n") if l.strip()][:3]
    items_html = "".join(f"<li>{esc(l)}</li>" for l in lines[:3])
    return f'<div class="card-summary"><ul>{items_html}</ul></div>'

def _render_release(s, item):
    what = who = ""
    bullets = []
    for line in s.split("\n"):
        l = line.strip()
        if l.upper().startswith("WHAT:"):
            what = l[5:].strip()
        elif l.upper().startswith("WHO:"):
            who = l[4:].strip()
        elif l.startswith("•") or l.startswith("-"):
            bullets.append(l.lstrip("•-").strip())
    if not what and not bullets:
        return f'<div class="card-summary">{esc(s)}</div>'
    what_h = f'<div class="rel-what">{esc(what)}</div>' if what else ""
    bul_h = ""
    if bullets:
        bul_h = '<div class="rel-bullets">' + "".join(
            f'<div class="rel-bullet">{esc(b)}</div>' for b in bullets[:3]
        ) + "</div>"
    who_h = f'<div class="rel-who">Best for: {esc(who)}</div>' if who else ""
    return f'<div class="card-summary">{what_h}{bul_h}{who_h}</div>'


def make_card(item, extra_class=""):
    st   = STORY_TYPE_CONFIG.get(item["story_type"], STORY_TYPE_CONFIG["general"])
    sc   = item["score"]
    is_r = item.get("is_release", False)
    is_t = item.get("trending", False)
    pred = item.get("predecessor")
    order_label = item.get("release_order_label")

    # Determine order badge colour
    order_colors = {
        "Latest Release":   ("background:#064e3b;color:#6ee7b7;border:1px solid #065f46", "🆕 Latest Release"),
        "Previous Release": ("background:#451a03;color:#fcd34d;border:1px solid #78350f", "⏮ Previous Release"),
        "Earlier Release":  ("background:#1e1b4b;color:#a5b4fc;border:1px solid #3730a3", "📅 Earlier"),
        "Archive":          ("background:#1e293b;color:#94a3b8;border:1px solid #334155", "🗂 Archive"),
    }

    type_badge  = (f'<span class="badge badge-type" style="color:{st["color"]}">'
                   f'{st["emoji"]} {st["label"]}</span>')
    src_badge   = (f'<span class="badge" style="background:{item["color"]}22;'
                   f'color:{item["color"]};border:1px solid {item["color"]}44">'
                   f'via {esc(item["source"])}</span>')
    trend_badge = '<span class="badge badge-trending">🔥 Trending</span>' if is_t else ""
    pred_badge  = ""
    if is_r and pred:
        pred_badge = (f'<span class="badge" style="background:#78350f44;color:#fbbf24;'
                      f'border:1px solid #92400e">replaces {esc(pred[0])}</span>')

    # "re: Company" badge — shown when subject != source (catches misattributed HN stories)
    about       = item.get("about")
    about_badge = ""
    if about:
        # Only show if the source doesn't already make the subject obvious
        src_lower = item["source"].lower().replace(" ai", "").replace(" ml", "")
        if about.lower() not in src_lower:
            about_badge = (f'<span class="badge" style="background:#0f2240;color:#93c5fd;'
                           f'border:1px solid #1e40af;font-weight:800">re: {esc(about)}</span>')
    order_badge = ""
    if order_label and order_label in order_colors:
        style, label_text = order_colors[order_label]
        order_badge = f'<span class="badge" style="{style}">{label_text}</span>'

    card_cls = "card"
    if is_r:   card_cls += " card-release"
    elif is_t: card_cls += " card-trending"
    if extra_class: card_cls += f" {extra_class}"

    summary_html = render_summary(item)
    ts = int(item["date_raw"].timestamp()) if item.get("date_raw") else 0

    return f"""<div class="{card_cls}" data-src="{esc(item['source'])}" data-rel="{'1' if is_r else '0'}" data-trend="{'1' if is_t else '0'}" data-ts="{ts}">
  <div class="card-top">
    <div class="card-title"><a href="{item['link']}" target="_blank" rel="noopener">{esc(item['title'])}</a></div>
    <span class="card-score {score_cls(sc)}">{star_str(sc)}</span>
  </div>
  <div class="card-badges">{order_badge}{about_badge}{type_badge}{src_badge}{trend_badge}{pred_badge}</div>
  <div class="card-meta"><span>{item['date']}</span></div>
  {summary_html}
</div>"""


def build_html(items, top3, ollama_ok, date_str):
    releases  = [i for i in items if i.get("is_release")]
    trending  = [i for i in items if i.get("trending") and not i.get("is_release")]
    all_items = sorted(items, key=lambda x: x["score"], reverse=True)

    # Morning brief
    brief_block = ""
    if top3:
        lines = [l.strip() for l in top3.split("\n") if l.strip()]
        paras = "".join(f"<p>{esc(l)}</p>" for l in lines)
        brief_block = f'<div class="brief"><div class="brief-label">Morning Brief</div><div class="brief-text">{paras}</div></div>'
    else:
        brief_block = '<div class="brief"><div class="brief-label">Morning Brief</div><div class="brief-text"><p style="color:var(--muted)">Start Ollama to generate your daily briefing.</p></div></div>'

    # Ollama warning
    warn_block = ""
    if not ollama_ok:
        warn_block = ('<div class="ollama-warn"><span>⚠️</span><span>Ollama is offline — '
                      'showing headlines and scores only. Run <code>ollama serve</code> '
                      'in a terminal, then re-run this script for plain-English summaries.</span></div>')

    # Releases section — sorted by date desc so Latest Release appears first
    releases_block = ""
    if releases:
        epoch = datetime.min.replace(tzinfo=timezone.utc)
        sorted_rels = sorted(releases, key=lambda x: x.get("date_raw") or epoch, reverse=True)
        cards_html = "\n".join(make_card(i) for i in sorted_rels)
        releases_block = f"""<div class="section-head">
  <span class="dot" style="background:#f59e0b"></span>
  <h2 style="color:#f59e0b">What's New</h2>
  <span class="section-count">{len(releases)} release{"s" if len(releases)!=1 else ""} detected</span>
  <span class="section-divider"></span>
</div>
<div class="grid-releases">{cards_html}</div>"""

    # Trending section — only items marked trending and not already a release
    trending_block = ""
    if trending:
        sorted_trend = sorted(trending, key=lambda x: x["score"], reverse=True)
        cards_html = "\n".join(make_card(i) for i in sorted_trend)
        src_count = len(set(i["source"] for i in trending))
        trending_block = f"""<div class="section-head">
  <span class="dot" style="background:#60a5fa"></span>
  <h2 style="color:#60a5fa">Trending Now</h2>
  <span class="section-count">covered by {src_count}+ sources</span>
  <span class="section-divider"></span>
</div>
<div class="grid-trending">{cards_html}</div>"""

    # All stories
    all_cards = "\n".join(make_card(i) for i in all_items)

    # Filter chips — newsletters excluded (show_chip=False), grouped by category
    lab_chips     = ""
    news_chips    = ""
    creator_chips = ""
    x_chips       = ""
    seen = set()
    for i in items:
        src = i["source"]
        if src in seen or not i.get("show_chip", True):
            continue
        seen.add(src)
        color = i["color"]
        chip  = (f'<span class="chip on" data-f="{esc(src)}" '
                 f'style="background:{color}22;color:{color};border-color:{color}55">'
                 f'{esc(src)}</span>')
        cat = i["category"]
        if cat == "lab":
            lab_chips     += chip + "\n  "
        elif cat == "creator":
            creator_chips += chip + "\n  "
        elif cat == "x":
            x_chips       += chip + "\n  "
        else:
            news_chips    += chip + "\n  "

    creator_row = (
        f'<div class="filter-row"><span class="filter-label">Creators</span>{creator_chips}</div>'
        if creator_chips.strip() else ""
    )
    x_row = (
        f'<div class="filter-row"><span class="filter-label">X / Twitter</span>{x_chips}</div>'
        if x_chips.strip() else ""
    )

    chip_src_count = len(seen)
    return HTML.format(
        date=date_str,
        count=len(items),
        sources=chip_src_count,
        releases=len(releases),
        trending_count=len(trending),
        brief_block=brief_block,
        warn_block=warn_block,
        releases_block=releases_block,
        trending_block=trending_block,
        all_cards=all_cards,
        lab_chips=lab_chips,
        news_chips=news_chips,
        creator_row=creator_row,
        x_row=x_row,
    )

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    date_str     = datetime.now().strftime("%B %d, %Y  %H:%M")
    archive_name = datetime.now().strftime("dashboard-%Y-%m-%d.html")
    script_dir   = os.path.dirname(os.path.abspath(__file__))
    out_path     = os.path.join(script_dir, "dashboard.html")
    archive_path = os.path.join(script_dir, "archive", archive_name)

    print("Fetching feeds...")
    all_items = []
    for name, cfg in FEEDS.items():
        print(f"  {name}...", end=" ", flush=True)
        items = fetch_feed(name, cfg)
        print(f"{len(items)}")
        all_items.extend(items)

    print(f"\n{len(all_items)} total items")

    # Detect releases, classify, subject, trending, score
    for item in all_items:
        is_r, pred = detect_release(item)
        item["is_release"]  = is_r
        item["predecessor"] = pred
        item["story_type"]  = classify_story(item)
        item["about"]       = detect_about(item)

    detect_trending(all_items)

    for item in all_items:
        item["score"] = score_item(item)

    # Label releases per source as Latest / Previous / Earlier (timeline order)
    _ORDER_LABELS = ["Latest Release", "Previous Release", "Earlier Release", "Archive"]
    _src_releases = defaultdict(list)
    for item in all_items:
        if item["is_release"]:
            _src_releases[item["source"]].append(item)
    for src_rels in _src_releases.values():
        epoch = datetime.min.replace(tzinfo=timezone.utc)
        src_rels.sort(key=lambda x: x.get("date_raw") or epoch, reverse=True)
        for idx, rel in enumerate(src_rels):
            rel["release_order_label"] = _ORDER_LABELS[min(idx, len(_ORDER_LABELS) - 1)]

    releases = sum(1 for i in all_items if i["is_release"])
    trending = sum(1 for i in all_items if i["trending"])
    print(f"Releases: {releases}  |  Trending: {trending}")

    ollama_ok = ollama_available()
    print(f"Ollama: {'✓ on' if ollama_ok else '✗ offline'}")

    if ollama_ok:
        print("\nSummarizing in plain English...")
        for idx, item in enumerate(all_items):
            print(f"  [{idx+1}/{len(all_items)}] {item['source']}: {item['title'][:65]}...")
            if item["is_release"]:
                item["ai_summary"] = summarize_release(item)
            elif item["type"] == "newsletter":
                item["ai_summary"] = summarize_newsletter(item)
            elif item["type"] == "video":
                item["ai_summary"] = summarize_video(item)
            else:
                item["ai_summary"] = summarize_article(item)
        print("\nWriting morning brief...")
        top3 = top3_summary(all_items)
    else:
        top3 = None

    print("\nBuilding dashboard...")
    html = build_html(all_items, top3, ollama_ok, date_str)

    os.makedirs(os.path.join(script_dir, "archive"), exist_ok=True)
    for path in (out_path, archive_path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
    print(f"Saved → {out_path}")
    print(f"Archived → {archive_path}")

    webbrowser.open(f"file://{out_path}")
    print("Done.")

if __name__ == "__main__":
    main()
