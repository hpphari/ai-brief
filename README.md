# AI News Dashboard

## Problem
Keeping up with fast-moving AI news requires checking 7+ sources daily — newsletters, lab blogs, and Hacker News — with no unified view or relevance filtering for program management work (Claude, MCP, agents, enterprise AI delivery).

## Solution
A single Python script that pulls, filters, summarizes, and scores today's AI news into one offline-readable HTML dashboard — in under 2 minutes, at zero cost.

## Architecture

```
RSS Feeds (7 sources)
        │
        ▼
  feedparser  ──── last 24h, max 5/source
        │
        ▼
  Ollama (llama3.2, local)
    ├── newsletters  → 3 bullet points, ads stripped
    ├── articles     → 1 plain-English sentence
    └── top 3 overall → morning briefing
        │
        ▼
  Relevance scorer   (keyword match, 1–5 stars)
  Sorted by score
        │
        ▼
  dashboard.html     ← opens in browser
  archive/dashboard-YYYY-MM-DD.html
```

**Fallback:** if Ollama is offline, the dashboard still builds with headlines and scores — it never crashes.

## Cost
$0 — all local. Ollama runs llama3.2 on your machine. No API keys required.

## Time Saved
| Task | Before | After |
|---|---|---|
| Morning AI news scan | ~30 min/day | ~2 min/day |
| Weekly total | ~3.5 hours | ~15 min |
| **Time saved per week** | | **~3 hours** |

## Setup

**1. Install dependencies**
```bash
pip install feedparser requests
```

**2. Install and start Ollama** (optional — for AI summaries)
```bash
# Install: https://ollama.com
ollama pull llama3.2
ollama serve
```

**3. Run**
```bash
cd ~/ai-news
python ai_news.py
```
The dashboard opens automatically in your browser.

**4. Archive**
Every run saves a copy to `archive/dashboard-YYYY-MM-DD.html`. The live `dashboard.html` and `archive/` are git-ignored so your repo stays clean.

## Daily Cron (6 AM)

```cron
0 6 * * * cd /Users/tcsadmin/ai-news && /usr/bin/python3 ai_news.py >> /tmp/ai_news.log 2>&1
```

Add with: `crontab -e`

## Relevance Scoring

Articles are scored 1–5 based on keyword matches for:
- **High weight:** Claude, MCP, model context protocol, LangGraph, agents/agentic, enterprise AI
- **Standard weight:** LLM, GPT, OpenAI, Gemini, tool use, multi-agent, orchestration, deployment, production

## Repo

**https://github.com/hpphari/ai-news**
