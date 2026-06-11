# AI Brief

> Your daily AI news dashboard — plain-English summaries, release detection, and trending stories. Runs 100% locally. Zero cost.

![Python](https://img.shields.io/badge/Python-3.9+-blue?style=flat-square)
![Ollama](https://img.shields.io/badge/Ollama-llama3.2-green?style=flat-square)
![Cost](https://img.shields.io/badge/Cost-%240-brightgreen?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-purple?style=flat-square)

---

## What it does

AI Brief runs every morning, pulls from 18 AI news sources, and builds a single offline-readable HTML dashboard with:

- **Plain-English summaries** — no jargon, written for people who use AI tools daily
- **Release Radar** — detects new model/product launches and shows what changed vs the previous version
- **Trending Now** — flags stories covered by 2+ sources so you know what everyone is talking about
- **Subject tagging** — a `re: Google` or `re: Anthropic` badge tells you what a story is actually about, regardless of which feed it came from
- **Relevance scoring** — every story is scored 1–5 stars based on your interests (Claude, MCP, agents, enterprise AI)
- **Daily archive** — each run is saved to `archive/dashboard-YYYY-MM-DD.html` so you keep history

---

## Dashboard layout

```
┌────────────────────────────────────────────────────────┐
│  AI Today  ·  Jun 11, 2026  │  5 releases  32 trending │
├────────────────────────────────────────────────────────┤
│  Filter: All | 🚀 Releases | 🔥 Trending               │
│  Companies: Anthropic OpenAI Google xAI Perplexity …   │
│  News: VentureBeat TechCrunch The Verge Hacker News    │
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

## Sources

| Category | Sources |
|---|---|
| **Newsletters** | TLDR AI, The Rundown AI, Ben's Bites |
| **AI Labs** | Anthropic, OpenAI, Google AI, Google Research, DeepMind, Microsoft AI, Meta AI, Apple ML, xAI/Grok, Perplexity, Hugging Face, NVIDIA AI |
| **Industry News** | VentureBeat AI, TechCrunch AI, The Verge, Hacker News |

> **Note:** Anthropic, xAI, and Perplexity have no public RSS feeds — they're covered via targeted Hacker News feeds and industry publications. The `re:` badge ensures correct attribution.

---

## Architecture

```
RSS Feeds (18 sources)
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

> **Intel Mac users:** use `llama3.2:1b` (default in this repo). It runs on CPU at ~8 tokens/sec — about 4–6 min for a full run. Apple Silicon users can switch to `llama3.2` (3B) for better quality.

### 3. Run

```bash
python3 ai_news.py
```

The dashboard opens automatically in your browser.

---

## Daily automation (6 AM cron)

```bash
crontab -e
```

Add:
```
0 6 * * * cd /Users/tcsadmin/ai-news && ollama serve & sleep 10 && /usr/bin/python3 ai_news.py >> /tmp/ai_brief.log 2>&1
```

---

## Configuration

All config is at the top of `ai_news.py`:

| Setting | Default | Description |
|---|---|---|
| `OLLAMA_MODEL` | `llama3.2:1b` | Swap to `llama3.2` for better quality on Apple Silicon |
| `FEEDS` | 18 sources | Add/remove sources, adjust `window_hours` and `max_items` |
| `INTEREST_KW` | Claude, MCP, agents… | Keywords that boost relevance score |
| `HIGH_INTEREST` | Claude, MCP, LangGraph… | Keywords that boost score more |
| `COMPANY_SUBJECTS` | 13 companies | Patterns used for the `re:` subject badge |

### Adding a new source

```python
"Source Name": {
    "url":          "https://example.com/feed.xml",
    "color":        "#hexcolor",
    "type":         "article",       # or "newsletter"
    "category":     "lab",           # "lab", "news", or "newsletter"
    "window_hours": 72,              # how far back to look
    "max_items":    7,               # max items to fetch
    "show_chip":    True,            # False hides it from the filter bar
},
```

---

## Cost

| Item | Cost |
|---|---|
| Ollama (local LLM) | $0 |
| RSS feeds | $0 |
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
