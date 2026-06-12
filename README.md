# AI Brief

> Your daily AI news dashboard — plain-English summaries, release detection, and trending stories. Runs 100% locally. Zero cost.

![Python](https://img.shields.io/badge/Python-3.9+-blue?style=flat-square)
![Ollama](https://img.shields.io/badge/Ollama-llama3.2-green?style=flat-square)
![Sources](https://img.shields.io/badge/Sources-49-orange?style=flat-square)
![Cost](https://img.shields.io/badge/Cost-%240-brightgreen?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-purple?style=flat-square)

---

## What it does

AI Brief runs every morning, pulls from 49 AI sources, and builds a single offline-readable HTML dashboard with:

- **Plain-English summaries** — no jargon, written for people who use AI tools daily
- **Release Radar** — detects new model/product launches and shows what changed vs the previous version
- **Trending Now** — flags stories covered by 2+ sources so you know what everyone is talking about
- **Subject tagging** — a `re: Google` or `re: Anthropic` badge tells you what a story is actually about, regardless of which feed it came from
- **Relevance scoring** — every story is scored 1–5 stars based on your interests (Claude, MCP, agents, enterprise AI)
- **YouTube creator feed** — pulls latest videos from top AI creators via native YouTube RSS
- **X / Twitter feed** — pulls posts from key AI accounts via RSSHub (self-host for reliability)
- **Daily archive** — each run is saved to `archive/dashboard-YYYY-MM-DD.html` so you keep history

---

## Dashboard layout

```
┌────────────────────────────────────────────────────────┐
│  AI Today  ·  Jun 11, 2026  │  5 releases  32 trending │
├────────────────────────────────────────────────────────┤
│  Filter: All | 🚀 Releases | 🔥 Trending               │
│  Companies: Anthropic OpenAI Google xAI Perplexity …   │
│  News: VentureBeat TechCrunch Hacker News              │
│  Creators: Varun Mayya · Fireship · AI Explained …     │
│  X / Twitter: @karpathy · @sama · @swyx …              │
├────────────────────────────────────────────────────────┤
│  Morning Brief (3-sentence plain-English briefing)     │
├────────────────────────────────────────────────────────┤
│  🚀 What's New  (release cards with version comparison)│
├────────────────────────────────────────────────────────┤
│  🔥 Trending Now  (multi-source stories)               │
├────────────────────────────────────────────────────────┤
│  All Stories  (sorted by relevance score)              │
└────────────────────────────────────────────────────────┘
```

---

## Sources (49 total)

| Category | Sources |
|---|---|
| **Newsletters** | TLDR AI, The Rundown AI, Ben's Bites |
| **AI Labs** | Anthropic, OpenAI, Google AI, Google Research, DeepMind, Microsoft AI, Meta AI, Apple ML, xAI/Grok, Perplexity, Hugging Face, NVIDIA AI |
| **Industry News** | VentureBeat AI, TechCrunch AI, Hacker News (AI-filtered) |
| **YouTube Creators** | AI Explained, Matt Wolfe, Fireship, Lex Fridman, Two Minute Papers, DeepLearning.AI, Varun Mayya, Vaibhav Sisinty, Dan Martell, Alberta Tech, Doctor AI, AI Adventurer, Underfitted |
| **X / Twitter** | @karpathy, @sama, @DarioAmodei, @swyx, @emollick, @rowancheung, @ai_rohitt, @AnthropicAI, @OpenAI, @GoogleDeepMind, @LangChainAI, @googlegemini, @perplexity_ai, @claudeai, @vaibhavsisinty, @VarunMayya, @danmartell |

> **Notes:**
> - Anthropic, xAI, and Perplexity have no public RSS feeds — covered via targeted Hacker News feeds. The `re:` badge ensures correct attribution.
> - X/Twitter feeds require RSSHub. The public instance (`rsshub.app`) is best-effort. Set `RSSHUB_URL` for a self-hosted instance.
> - YouTube feeds use native YouTube RSS — no API key needed.

---

## Architecture

```
RSS + YouTube RSS + RSSHub (X/Twitter)
        │
        ▼
  feedparser + requests
  (follows redirects, 24h–14d window per source)
        │
        ▼
  Detection pipeline
  ├── detect_release()      → new model/product announcements
  ├── detect_about()        → which company the story is about
  ├── detect_trending()     → same topic in 2+ sources
  ├── classify_story()      → New Release / Funding / Research / Policy …
  └── score_item()          → 1–5 relevance stars
        │
        ▼
  Ollama (llama3.2:1b, local)
  ├── newsletters  → 3 plain-English bullets, ads stripped
  ├── articles     → 1–2 sentence plain-English summary
  ├── videos       → 1-sentence "why watch this" summary
  ├── releases     → WHAT changed / 3 real-world improvements / WHO benefits
  └── top 3        → morning briefing
        │
        ▼
  dashboard.html  (opens in browser)
  archive/dashboard-YYYY-MM-DD.html
```

**Fallback:** if Ollama is offline the dashboard still builds with headlines, scores, and badges — it never crashes.

---

## Setup

### 1. Clone and install dependencies

```bash
git clone https://github.com/hpphari/ai-brief.git
cd ai-brief
pip install feedparser requests
```

Only two dependencies — no OpenAI key, no paid API, no cloud.

### 2. Install Ollama (for AI summaries)

Download from **https://ollama.com/download**, then:

```bash
ollama pull llama3.2:1b   # ~800 MB, fast on CPU
ollama serve              # keep this terminal open
```

> **Intel Mac users:** use `llama3.2:1b` (default). It runs on CPU at ~8 tokens/sec — about 4–6 min for a full run. Apple Silicon users can switch to `llama3.2` (3B) for better quality.

### 3. Run

```bash
python3 ai_news.py
```

The dashboard opens automatically in your browser.

---

## X / Twitter feeds (optional)

X accounts are fetched via [RSSHub](https://docs.rsshub.app). The public instance is used by default but may be rate-limited.

For reliable X feeds, self-host RSSHub and point the script to it:

```bash
# Option A — Docker
docker run -d -p 1200:1200 diygod/rsshub

# Option B — npm
npx rsshub
```

Then run:

```bash
RSSHUB_URL=http://localhost:1200 python3 ai_news.py
```

Without this, X feeds are best-effort — they fail silently and the dashboard still builds from all other sources.

---

## Daily automation (6 AM cron)

```bash
crontab -e
```

Add:
```
0 6 * * * cd /path/to/ai-brief && ollama serve & sleep 10 && /usr/bin/python3 ai_news.py >> /tmp/ai_brief.log 2>&1
```

---

## Configuration

All config is at the top of `ai_news.py`:

| Setting | Default | Description |
|---|---|---|
| `OLLAMA_MODEL` | `llama3.2:1b` | Swap to `llama3.2` for better quality on Apple Silicon |
| `FEEDS` | 49 sources | Add/remove sources, adjust `window_hours` and `max_items` |
| `INTEREST_KW` | Claude, MCP, agents… | Keywords that boost relevance score |
| `HIGH_INTEREST` | Claude, MCP, LangGraph… | Keywords that boost score more |
| `COMPANY_SUBJECTS` | 13 companies | Patterns used for the `re:` subject badge |
| `RSSHUB_URL` env var | `https://rsshub.app` | Override with self-hosted RSSHub for reliable X feeds |

### Adding a YouTube channel

Find the channel ID on YouTube (channel page → View Source → search `channelId`), then:

```python
"Channel Name": {
    "url":          "https://www.youtube.com/feeds/videos.xml?channel_id=UC...",
    "color":        "#hexcolor",
    "type":         "video",
    "category":     "creator",
    "window_hours": 336,    # 14 days — creators post less frequently
    "max_items":    5,
},
```

### Adding an X / Twitter account

```python
"X: handle": {
    "url":          f"{_RSSHUB}/twitter/user/handle",
    "color":        "#hexcolor",
    "type":         "article",
    "category":     "x",
    "window_hours": 48,
    "max_items":    5,
},
```

### Adding a news/blog source

```python
"Source Name": {
    "url":          "https://example.com/feed.xml",
    "color":        "#hexcolor",
    "type":         "article",
    "category":     "lab",     # "lab", "news", "newsletter", "creator", or "x"
    "window_hours": 72,
    "max_items":    7,
    "show_chip":    True,
},
```

---

## Cost

| Item | Cost |
|---|---|
| Ollama (local LLM) | $0 |
| RSS + YouTube RSS feeds | $0 |
| RSSHub (self-hosted) | $0 |
| Hosting | $0 — runs on your Mac |
| **Total** | **$0** |

## Time saved

| Task | Before | After |
|---|---|---|
| Morning AI news scan | ~30 min/day | ~2 min/day |
| **Per week** | ~3.5 hours | ~15 min |
| **Saved** | | **~3 hours/week** |

---

## Repo

**https://github.com/hpphari/ai-brief**
