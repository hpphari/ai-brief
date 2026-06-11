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

### 1. Add a new news source

The most common contribution. Open `ai_news.py` and add an entry to the `FEEDS` dict:

```python
"Source Name": {
    "url":          "https://example.com/feed.xml",
    "color":        "#hexcolor",        # shown on filter chip + card badge
    "type":         "article",          # "article" or "newsletter"
    "category":     "lab",              # "lab", "news", or "newsletter"
    "window_hours": 72,                 # how far back to fetch (hours)
    "max_items":    7,                  # max items per run
    "show_chip":    True,               # False = absorbed into feed, no filter chip
},
```

**Before submitting:**
- Verify the feed URL works: `python3 -c "import feedparser; f=feedparser.parse('YOUR_URL'); print(len(f.entries), f.entries[0].title if f.entries else 'empty')"`
- Check it returns recent entries (not all 404 or empty)
- If the site blocks bots (403), note it in a comment — use an HN search feed as fallback

---

### 2. Improve release detection

Release detection lives in `detect_release()`. If a real release is being missed, add the trigger keyword to `RELEASE_TITLE_SIGNALS`. If a non-release is being falsely flagged, add a pattern to `RELEASE_NEGATIVES`.

To add a known model lineage (so the "replaces X" badge appears):

```python
# In MODEL_PREDECESSORS dict:
"new model name": ("Previous Model Name", "Company"),
```

---

### 3. Improve subject tagging

The `re: Company` badge comes from `detect_about()`. If a company is being missed or misidentified, update `COMPANY_SUBJECTS`:

```python
"Company Name": ["keyword1", "product name", "another signal"],
```

Put the most specific patterns first. Patterns are matched against lowercased title + first 400 chars of summary.

---

### 4. Improve Ollama prompts

Prompts are in four functions — `summarize_newsletter()`, `summarize_article()`, `summarize_release()`, `top3_summary()`. The goal is plain English that a non-developer AI user can understand immediately. When editing:

- Avoid jargon: "replies faster" not "lower latency", "reads long documents" not "large context window"
- Keep output format instructions explicit — the HTML renderer parses `WHAT:` / `WHO:` / `•` prefixes
- Test with `llama3.2:1b` (slowest/smallest supported model) so it works for everyone

---

### 5. Fix a bug or improve the UI

- HTML/CSS/JS is all inside the `HTML` string in `ai_news.py` — search for `HTML = """`
- The dashboard must work **offline** (no CDN fonts, no external scripts)
- Only `feedparser` and `requests` are allowed as dependencies — keep it that way

---

## Submitting a pull request

1. Fork the repo and create a branch: `git checkout -b your-feature`
2. Make your change
3. Run `python3 ai_news.py` and confirm the dashboard generates without errors
4. Commit with a clear message:
   ```
   feat: add MIT Technology Review feed
   fix: false positive on GPT-2 historical posts
   improve: clearer release summary prompt
   ```
5. Open a PR against `main` with a short description of what you changed and why

---

## What not to contribute

- **New dependencies** — `feedparser` and `requests` only. No BeautifulSoup, no LangChain, no paid APIs.
- **Cloud/API-based summarization** — the whole point is local + free. Ollama stays.
- **Breaking the offline requirement** — the HTML file must open without internet.
- **Auto-commit or auto-push logic** — the script runs locally, users push manually.

---

## Reporting issues

Open an issue at **https://github.com/hpphari/ai-brief/issues** with:
- What you expected to happen
- What actually happened
- Output from the terminal when you ran `python3 ai_news.py`
- Your Python version (`python3 --version`) and OS
