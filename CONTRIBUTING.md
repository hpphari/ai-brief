# Contributing to AI Brief

Thanks for your interest in improving AI Brief. Contributions are welcome — bug fixes, new sources, better prompts, or UI improvements.

---

## Quick start

```bash
git clone https://github.com/hpphari/ai-brief.git
cd ai-brief
pip install feedparser requests
python3 ai_news.py   # verify it runs
```

---

## Ways to contribute

### 1. Add a news or blog source

Open `ai_news.py` and add an entry to the `FEEDS` dict:

```python
"Source Name": {
    "url":          "https://example.com/feed.xml",
    "color":        "#hexcolor",        # shown on filter chip + card badge
    "type":         "article",          # "article", "newsletter", or "video"
    "category":     "lab",              # "lab", "news", "newsletter", "creator", or "x"
    "window_hours": 72,                 # how far back to fetch (hours)
    "max_items":    7,                  # max items per run
    "show_chip":    True,               # False = absorbed into feed, no filter chip
},
```

**Before submitting:**
- Verify the feed URL works: `python3 -c "import feedparser; f=feedparser.parse('YOUR_URL'); print(len(f.entries), f.entries[0].title if f.entries else 'empty')"`
- Check it returns recent entries (not all 404 or empty)
- If the site blocks bots (403), use an HN search feed as fallback and note it in a comment

---

### 2. Add a YouTube channel

YouTube channels have free native RSS feeds — no API key needed.

**Step 1 — Find the channel ID:**

```bash
python3 -c "
import requests, re
url = 'https://www.youtube.com/@channelhandle'
resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
m = re.search(r'\"channelId\":\"(UC[a-zA-Z0-9_-]{22})\"', resp.text)
print(m.group(1) if m else 'not found')
"
```

**Step 2 — Add to FEEDS:**

```python
"Channel Name": {
    "url":          "https://www.youtube.com/feeds/videos.xml?channel_id=UC...",
    "color":        "#hexcolor",
    "type":         "video",
    "category":     "creator",
    "window_hours": 336,    # 14 days — creators post less frequently than news sites
    "max_items":    5,
},
```

Only add channels that are **AI-focused** — general tech, programming tutorials, or business channels without AI content will score low and add noise.

---

### 3. Add an X / Twitter account

X feeds are served via [RSSHub](https://docs.rsshub.app). Use the `_RSSHUB` variable (already defined at the top of `ai_news.py`) so users can override it with a self-hosted instance.

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

X feeds fail silently if RSSHub is unavailable — the dashboard still builds from all other sources. Only add accounts that post original AI signal (researchers, lab accounts, curators). Avoid accounts that only retweet or post marketing.

---

### 4. Improve release detection

Release detection lives in `detect_release()`. If a real release is being missed, add the trigger keyword to `RELEASE_TITLE_SIGNALS`. If a non-release is being falsely flagged, add a pattern to `RELEASE_NEGATIVES`.

To add a known model lineage so the "replaces X" badge appears:

```python
# In MODEL_PREDECESSORS dict:
"new model name": ("Previous Model Name", "Company"),
```

---

### 5. Improve subject tagging

The `re: Company` badge comes from `detect_about()`. If a company is being missed or misidentified, update `COMPANY_SUBJECTS`:

```python
"Company Name": ["keyword1", "product name", "another signal"],
```

Put the most specific patterns first. Patterns are matched against lowercased title + first 400 chars of summary.

---

### 6. Improve Ollama prompts

Prompts live in five functions — `summarize_newsletter()`, `summarize_article()`, `summarize_video()`, `summarize_release()`, `top3_summary()`. The goal is plain English that a non-developer AI user understands immediately.

- Avoid jargon: "replies faster" not "lower latency", "reads long documents" not "large context window"
- Keep output format instructions explicit — the HTML renderer parses `WHAT:` / `WHO:` / `•` prefixes
- Test with `llama3.2:1b` (slowest/smallest supported model) so it works for everyone

---

### 7. Fix a bug or improve the UI

- HTML/CSS/JS is all inside the `HTML` string in `ai_news.py` — search for `HTML = """`
- The dashboard must work **offline** (no CDN fonts, no external scripts)
- Only `feedparser` and `requests` are allowed as dependencies

---

## Submitting a pull request

1. Fork the repo and create a branch: `git checkout -b your-feature`
2. Make your change
3. Run `python3 ai_news.py` and confirm the dashboard generates without errors
4. Commit with a clear message:
   ```
   feat: add MIT Technology Review feed
   feat: add @karpathy X account
   fix: false positive on GPT-2 historical posts
   improve: clearer release summary prompt
   ```
5. Open a PR against `main` with a short description of what you changed and why

---

## What not to contribute

- **New dependencies** — `feedparser` and `requests` only. No BeautifulSoup, no LangChain, no paid APIs.
- **Cloud/API-based summarization** — the whole point is local + free. Ollama stays.
- **Breaking the offline requirement** — the HTML file must open without internet.
- **Non-AI sources** — general tech, lifestyle, finance, or entertainment channels don't belong here.
- **Auto-commit or auto-push logic** — the script runs locally, users push manually.

---

## Reporting issues

Open an issue at **https://github.com/hpphari/ai-brief/issues** with:
- What you expected to happen
- What actually happened
- Output from the terminal when you ran `python3 ai_news.py`
- Your Python version (`python3 --version`) and OS
