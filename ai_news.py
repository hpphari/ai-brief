#!/usr/bin/env python3
"""AI News Dashboard — plain English, 15 layman-friendly features."""

import feedparser
import requests
import os
import re
import sys
import json
import webbrowser
import calendar
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

# Load .env if present
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())

_RSSHUB = os.environ.get("RSSHUB_URL", "https://rsshub.app")

# ── Feeds ─────────────────────────────────────────────────────────────────────

FEEDS = {
    "TLDR AI":          {"url": "https://bullrich.dev/tldr-rss/ai.rss",                                            "color": "#818cf8", "type": "newsletter", "category": "newsletter", "window_hours": 48,  "max_items": 5, "show_chip": False},
    "The Rundown AI":   {"url": "https://rss.beehiiv.com/feeds/2R3C6Bt5wj.xml",                                    "color": "#38bdf8", "type": "newsletter", "category": "newsletter", "window_hours": 48,  "max_items": 3, "show_chip": False},
    "Ben's Bites":      {"url": "https://bensbites.beehiiv.com/feed",                                              "color": "#34d399", "type": "newsletter", "category": "newsletter", "window_hours": 48,  "max_items": 3, "show_chip": False},
    "Anthropic":        {"url": "https://hnrss.org/newest?q=Anthropic+OR+Claude+AI+OR+Claude+Fable+OR+Claude+Sonnet+OR+Claude+Opus+OR+MCP+Anthropic&points=20", "color": "#f97316", "type": "article", "category": "lab", "window_hours": 168, "max_items": 10},
    "OpenAI":           {"url": "https://openai.com/news/rss.xml",                                                 "color": "#10b981", "type": "article",    "category": "lab",        "window_hours": 336, "max_items": 10},
    "Google AI":        {"url": "https://blog.google/technology/ai/rss/",                                          "color": "#4285f4", "type": "article",    "category": "lab",        "window_hours": 336, "max_items": 10},
    "DeepMind":         {"url": "https://deepmind.google/discover/blog/rss/",                                      "color": "#1a73e8", "type": "article",    "category": "lab",        "window_hours": 336, "max_items": 10},
    "Microsoft AI":     {"url": "https://blogs.microsoft.com/ai/feed/",                                            "color": "#00bcf2", "type": "article",    "category": "lab",        "window_hours": 336, "max_items": 10},
    "Meta AI":          {"url": "https://engineering.fb.com/category/ai-research/feed/",                           "color": "#0668e1", "type": "article",    "category": "lab",        "window_hours": 336, "max_items": 10},
    "Apple ML":         {"url": "https://machinelearning.apple.com/rss.xml",                                       "color": "#8e8e93", "type": "article",    "category": "lab",        "window_hours": 336, "max_items": 10},
    "xAI / Grok":       {"url": "https://hnrss.org/newest?q=Grok+OR+xAI+OR+%22x.ai%22+OR+%22Grok+4%22+OR+%22Grok+3%22&points=15", "color": "#60a5fa", "type": "article", "category": "lab", "window_hours": 168, "max_items": 8},
    "Perplexity":       {"url": "https://hnrss.org/newest?q=%22Perplexity+AI%22+OR+%22Perplexity+search%22+OR+%22Sonar+model%22&points=15", "color": "#a78bfa", "type": "article", "category": "lab", "window_hours": 168, "max_items": 8},
    "Google Research":  {"url": "https://research.google/blog/rss/",                                               "color": "#34a853", "type": "article",    "category": "lab",        "window_hours": 168, "max_items": 7},
    "Hugging Face":     {"url": "https://huggingface.co/blog/feed.xml",                                            "color": "#fbbf24", "type": "article",    "category": "lab",        "window_hours": 168, "max_items": 7},
    "NVIDIA AI":        {"url": "https://blogs.nvidia.com/blog/category/generative-ai/feed/",                      "color": "#76b900", "type": "article",    "category": "lab",        "window_hours": 168, "max_items": 7},
    "VentureBeat AI":   {"url": "https://venturebeat.com/feed",                                                    "color": "#c084fc", "type": "article",    "category": "news",       "window_hours": 120, "max_items": 7},
    "TechCrunch AI":    {"url": "https://techcrunch.com/category/artificial-intelligence/feed/",                   "color": "#0d9488", "type": "article",    "category": "news",       "window_hours": 72,  "max_items": 7},
    "Hacker News":      {"url": "https://hnrss.org/newest?q=AI+OR+LLM+OR+Claude+OR+GPT+OR+Gemini+OR+Grok&points=100", "color": "#fb923c", "type": "article", "category": "news",    "window_hours": 48,  "max_items": 7},
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

MAX_PER_SOURCE = 7
OLLAMA_URL     = "http://localhost:11434/api/generate"
OLLAMA_MODEL   = "llama3.2:1b"

# ── Escape helper (used throughout) ───────────────────────────────────────────

def esc(t):
    return str(t).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")

# ── Jargon glossary ───────────────────────────────────────────────────────────

JARGON_GLOSSARY = {
    "LLM":              "Large Language Model — the AI brain that reads and writes text",
    "token":            "a word-chunk AI reads; roughly ¾ of one English word",
    "inference":        "running a trained AI to get an answer (like pressing 'submit')",
    "fine-tuning":      "extra training on specific data to make a model better at one task",
    "benchmark":        "a standardised test used to compare different AI models",
    "parameters":       "numbers the AI learned during training; more usually means smarter",
    "context window":   "how much text an AI can read at once in one conversation",
    "embedding":        "turning text into numbers so AI can understand meaning and similarity",
    "RAG":              "Retrieval-Augmented Generation — AI searches your documents before answering",
    "RLHF":             "training AI using human ratings of good vs bad answers",
    "API":              "a way for software to talk to another service (like an AI) over the internet",
    "open source":      "software whose code is public — anyone can read, copy, and modify it for free",
    "multimodal":       "AI that understands both text AND images (and sometimes audio or video)",
    "hallucination":    "when AI confidently states something that is factually wrong",
    "agent":            "an AI that can take actions on its own, not just answer questions",
    "MCP":              "Model Context Protocol — a standard way for AI to connect to tools and data",
    "latency":          "how long you wait for the AI to respond",
    "quantization":     "compressing an AI model so it runs on weaker hardware",
    "GPU":              "a powerful chip for graphics, now essential for running AI",
    "transformer":      "the core architecture behind modern AI language models like GPT and Claude",
    "prompt":           "the text or question you type to get a response from an AI",
}

# ── Story classification ───────────────────────────────────────────────────────

STORY_TYPE_CONFIG = {
    "release":    {"label": "New Release",     "emoji": "🚀", "color": "#f59e0b", "bg": "#451a03"},
    "investment": {"label": "Funding & Deals", "emoji": "💰", "color": "#10b981", "bg": "#052e16"},
    "research":   {"label": "Research",        "emoji": "🔬", "color": "#a78bfa", "bg": "#2e1065"},
    "product":    {"label": "Product Update",  "emoji": "📦", "color": "#38bdf8", "bg": "#082f49"},
    "policy":     {"label": "Policy & Safety", "emoji": "🏛️", "color": "#fb7185", "bg": "#4c0519"},
    "enterprise": {"label": "Enterprise AI",   "emoji": "🏢", "color": "#818cf8", "bg": "#1e1b4b"},
    "general":    {"label": "Industry News",   "emoji": "📰", "color": "#94a3b8", "bg": "#1e293b"},
    "video":      {"label": "YouTube Video",   "emoji": "▶️",  "color": "#ef4444", "bg": "#1a0000"},
}

AREA_CONFIG = {
    "work":      {"emoji": "💼", "label": "Work",      "color": "#60a5fa"},
    "coding":    {"emoji": "💻", "label": "Coding",    "color": "#34d399"},
    "creative":  {"emoji": "🎨", "label": "Creative",  "color": "#c084fc"},
    "health":    {"emoji": "🏥", "label": "Health",    "color": "#f43f5e"},
    "education": {"emoji": "📚", "label": "Education", "color": "#fbbf24"},
}

REV_CONFIG = {
    "game_changer": {"label": "🔴 Game Changer", "color": "#f87171"},
    "notable":      {"label": "🟡 Notable",       "color": "#fbbf24"},
    "incremental":  {"label": "🔵 Incremental",   "color": "#60a5fa"},
}

HYPE_CONFIG = {
    "real":     {"label": "✅ Real",     "color": "#34d399"},
    "research": {"label": "🔬 Research", "color": "#a78bfa"},
    "opinion":  {"label": "💬 Opinion",  "color": "#94a3b8"},
    "hype":     {"label": "📣 Hype",     "color": "#fb923c"},
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

# ── Subject detection ──────────────────────────────────────────────────────────

COMPANY_SUBJECTS = {
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
    text = (item["title"] + " ") * 3 + item["summary_raw"][:400]
    text = text.lower()
    scores = {}
    for company, patterns in COMPANY_SUBJECTS.items():
        score = sum(text.count(p) for p in patterns)
        if score:
            scores[company] = score
    return max(scores, key=scores.get) if scores else None

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
    "fable":         ("Claude Opus 4.8",    "Anthropic"),
    "opus 4.8":      ("Claude 3 Opus",      "Anthropic"),
    "sonnet 4.6":    ("Claude 3.5 Sonnet",  "Anthropic"),
    "haiku 4.5":     ("Claude 3.5 Haiku",   "Anthropic"),
    "claude 4":      ("Claude 3.5",         "Anthropic"),
    "claude 3.7":    ("Claude 3.5",         "Anthropic"),
    "gpt-5":         ("GPT-4o",             "OpenAI"),
    "o4":            ("o3",                 "OpenAI"),
    "o3":            ("o1",                 "OpenAI"),
    "gpt-4.5":       ("GPT-4o",             "OpenAI"),
    "gemini 2.5":    ("Gemini 2.0",         "Google"),
    "gemini 2.0":    ("Gemini 1.5 Pro",     "Google"),
    "grok 4":        ("Grok 3",             "xAI"),
    "grok 3":        ("Grok 2",             "xAI"),
    "llama 4":       ("Llama 3.3",          "Meta"),
    "phi-4":         ("Phi-3",              "Microsoft"),
    "phi 4":         ("Phi-3",              "Microsoft"),
    "deepseek v3":   ("DeepSeek V2",        "DeepSeek"),
    "mistral large": ("Mistral Medium",     "Mistral"),
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

# ── Revolution-O-Meter ─────────────────────────────────────────────────────────

GAME_CHANGER_SIGNALS = [
    "agi", "artificial general intelligence", "surpasses human",
    "revolutionary", "unprecedented", "changes everything",
    "transforms", "beats human", "superhuman", "industry-wide",
]

def detect_revolution_level(item):
    text  = (item["title"] + " " + item["summary_raw"]).lower()
    score = item.get("score", 1)
    is_r  = item.get("is_release", False)
    if score >= 4 and is_r and any(s in text for s in GAME_CHANGER_SIGNALS):
        return "game_changer"
    if score >= 3 or is_r or item.get("trending"):
        return "notable"
    return "incremental"

# ── Hype vs Real ──────────────────────────────────────────────────────────────

HYPE_SIGNALS     = ["revolutionary", "unprecedented", "biggest ever", "game changing",
                    "will change everything", "blows away", "obliterates", "destroys all"]
RESEARCH_SIGNALS = ["paper", "arxiv", "study", "benchmark", "findings",
                    "researchers", "university", "published", "dataset", "evaluated"]
OPINION_SIGNALS  = ["i think", "in my opinion", "believe", "perspective",
                    "argues that", "opinion:", "thread:", "🧵", "hot take"]

def detect_hype_type(item):
    text = (item["title"] + " " + item["summary_raw"][:500]).lower()
    if any(s in text for s in HYPE_SIGNALS):
        return "hype"
    if any(s in text for s in OPINION_SIGNALS):
        return "opinion"
    if any(s in text for s in RESEARCH_SIGNALS):
        return "research"
    return "real"

# ── Life area detection ────────────────────────────────────────────────────────

AREA_KEYWORDS = {
    "work":      ["productivity", "workflow", "enterprise", "business", "meeting",
                  "email", "task", "automate", "workplace", "office", "manager", "employee"],
    "coding":    ["code", "developer", "programming", "github", "ide", "debug",
                  "testing", "software engineer", "python", "javascript", "cursor",
                  "copilot", "coding", "repository", "open source"],
    "creative":  ["image generation", "video generation", "music generation", "art ",
                  "generate images", "design", "creative", "midjourney", "stable diffusion",
                  "dall-e", "sora", "audio", "film", "animation", "illustration"],
    "health":    ["health", "medical", "diagnosis", "drug ", "clinical",
                  "patient", "hospital", "disease", "therapy", "doctor", "healthcare"],
    "education": ["learn", "education", "student", "course", "research paper",
                  "teach", "school", "training data", "tutorial", "curriculum"],
}

def detect_life_area(item):
    text   = (item["title"] + " " + item["summary_raw"][:600]).lower()
    scores = {area: sum(1 for kw in kws if kw in text)
              for area, kws in AREA_KEYWORDS.items()}
    scores = {k: v for k, v in scores.items() if v}
    return max(scores, key=scores.get) if scores else None

# ── Reading time ──────────────────────────────────────────────────────────────

def calc_read_time(item):
    if item["type"] == "video":
        return "YouTube"
    if item["type"] == "newsletter":
        return "digest"
    words = len(item["summary_raw"].split())
    return f"{max(1, round(words / 200))} min read"

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
    cutoff = datetime.now(timezone.utc) - timedelta(hours=config.get("window_hours", 48))
    max_n  = config.get("max_items", MAX_PER_SOURCE)
    items  = []
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
                "date_raw":            dt,
                "source":              name,
                "color":               config["color"],
                "type":                config["type"],
                "category":            config.get("category", "news"),
                "show_chip":           config.get("show_chip", True),
                # populated later
                "ai_summary":          None,
                "plain_headline":      "",
                "impact":              "",
                "story_type":          "general",
                "is_release":          False,
                "predecessor":         None,
                "release_order_label": None,
                "about":               None,
                "trending":            False,
                "trending_for":        None,
                "score":               1,
                "revolution_level":    "incremental",
                "hype_type":           "real",
                "life_area":           None,
                "read_time":           "",
                "is_new_today":        False,
            })
            if len(items) >= max_n:
                break
    except Exception as e:
        print(f"  [warn] {name}: {e}", file=sys.stderr)
    return items

# ── Archive helpers ────────────────────────────────────────────────────────────

def _summary_path(archive_dir, date_str):
    return os.path.join(archive_dir, f"summary-{date_str}.json")

def load_yesterday_links(archive_dir):
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    path = _summary_path(archive_dir, yesterday)
    if not os.path.exists(path):
        return set()
    try:
        with open(path) as f:
            data = json.load(f)
        return set(data.get("links", []))
    except Exception:
        return set()

def mark_new_today(items, archive_dir):
    yesterday_links = load_yesterday_links(archive_dir)
    if not yesterday_links:
        return  # first run — don't mark everything as new
    for item in items:
        item["is_new_today"] = item.get("link", "") not in yesterday_links

def write_archive_summary(items, archive_dir, date_str):
    top = sorted(items, key=lambda x: x["score"], reverse=True)[:3]
    data = {
        "date":        date_str,
        "count":       len(items),
        "releases":    sum(1 for i in items if i.get("is_release")),
        "trending":    sum(1 for i in items if i.get("trending")),
        "links":       [i.get("link", "") for i in items if i.get("link")],
        "top_stories": [i["title"] for i in top],
    }
    path = _summary_path(archive_dir, date_str)
    try:
        with open(path, "w") as f:
            json.dump(data, f)
    except Exception as e:
        print(f"  [warn] archive summary: {e}", file=sys.stderr)

def build_timeline_html(archive_dir):
    today   = datetime.now().date()
    days    = []
    max_cnt = 1
    for i in range(6, -1, -1):
        d        = today - timedelta(days=i)
        ds       = d.strftime("%Y-%m-%d")
        day_name = d.strftime("%a")
        count    = 0
        path     = _summary_path(archive_dir, ds)
        if os.path.exists(path):
            try:
                count = json.load(open(path)).get("count", 0)
            except Exception:
                pass
        days.append({"name": day_name, "count": count, "today": i == 0})
        max_cnt = max(max_cnt, count)

    days_html = ""
    for day in days:
        bar_h   = max(3, round(day["count"] / max_cnt * 48)) if day["count"] else 3
        cls     = "tl-day tl-today" if day["today"] else "tl-day"
        days_html += (
            f'<div class="{cls}">'
            f'<div class="tl-bar-wrap"><div class="tl-fill" style="height:{bar_h}px"></div></div>'
            f'<span class="tl-name">{day["name"]}</span>'
            f'<span class="tl-cnt">{day["count"] or ""}</span>'
            f'</div>'
        )
    return (
        f'<div class="widget">'
        f'<div class="widget-label">7-Day Activity</div>'
        f'<div class="tl-days">{days_html}</div>'
        f'</div>'
    )

def build_scoreboard_html(items):
    counts = defaultdict(int)
    for item in items:
        if item.get("about"):
            counts[item["about"]] += 1
    if not counts:
        return ""
    ranked = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:6]
    max_c  = ranked[0][1] or 1
    rows   = ""
    for company, count in ranked:
        pct  = round(count / max_c * 100)
        rows += (
            f'<div class="sb-row">'
            f'<span class="sb-name">{esc(company)}</span>'
            f'<div class="sb-bar-wrap"><div class="sb-bar" style="width:{pct}%"></div></div>'
            f'<span class="sb-cnt">{count}</span>'
            f'</div>'
        )
    return (
        f'<div class="widget">'
        f'<div class="widget-label">Company Activity</div>'
        f'{rows}'
        f'</div>'
    )

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
        "Write 3 bullet points. Each must:\n"
        "  - Use plain everyday language (no jargon)\n"
        "  - Say what happened AND why it matters\n"
        "  - Be under 20 words\n"
        "Skip ads, sponsors, job listings.\n\n"
        f"Title: {item['title']}\nContent: {item['summary_raw']}\n\n"
        "Output ONLY the 3 bullets, each starting with •"
    )
    return ollama_generate(prompt)

def summarize_combined(item):
    """Single Ollama call → plain_headline, ai_summary, impact."""
    src_hint = f"Channel: {item['source']}\n" if item["type"] == "video" else ""
    prompt = (
        "Analyze this AI news story. Respond in EXACTLY this format:\n\n"
        "HEADLINE: [Rewrite the title in plain English. Max 12 words. No jargon.]\n"
        "SUMMARY: [1-2 sentences. What happened + why it matters. No jargon.]\n"
        "IMPACT: [Start with 'This means you can' or 'For you, this means' — 1 sentence]\n\n"
        "Plain-English rules:\n"
        "- 'replies faster' not 'low latency'\n"
        "- 'reads long documents' not 'large context window'\n"
        "- 'makes fewer mistakes' not 'improved benchmark scores'\n"
        "- 'makes up answers less often' not 'reduced hallucinations'\n\n"
        f"{src_hint}"
        f"Title: {item['title']}\n"
        f"Content: {item['summary_raw'][:900]}\n\n"
        "Output ONLY the 3 labeled lines."
    )
    raw            = ollama_generate(prompt)
    plain_headline = ""
    ai_summary     = ""
    impact         = ""
    if raw:
        for line in raw.split("\n"):
            l = line.strip()
            u = l.upper()
            if u.startswith("HEADLINE:"):
                plain_headline = l[9:].strip().strip('"')
            elif u.startswith("SUMMARY:"):
                ai_summary = l[8:].strip()
            elif u.startswith("IMPACT:"):
                impact = l[7:].strip()
    return plain_headline, ai_summary, impact

def summarize_release(item):
    pred = item.get("predecessor")
    ctx  = f"The previous version was {pred[0]} by {pred[1]}. " if pred else ""
    prompt = (
        f"Explain this new AI product launch in plain English for someone who uses AI tools daily.\n"
        f"{ctx}"
        "Translate technical terms:\n"
        "  'faster response' → 'replies faster'\n"
        "  'larger context window' → 'reads much longer documents'\n"
        "  'improved benchmark' → 'makes fewer mistakes'\n"
        "  'lower cost per token' → 'cheaper to use'\n\n"
        f"Title: {item['title']}\nContent: {item['summary_raw']}\n\n"
        "Respond in EXACT format:\n"
        "WHAT: [one sentence — what was released and by whom]\n"
        "• [real-world improvement #1 vs old version]\n"
        "• [real-world improvement #2]\n"
        "• [real-world improvement #3]\n"
        "WHO: [one sentence — who benefits most]\n"
        "IMPACT: [Start 'This means you can...' — 1 sentence]\n"
    )
    return ollama_generate(prompt, timeout=150)

def summarize_story_of_day(item):
    """Hero block content for the #1 story."""
    prompt = (
        "This is today's biggest AI story. Write 3 lines:\n\n"
        "HEADLINE: [Plain English title, max 10 words, no jargon]\n"
        "WHY: [One sentence — why this is the biggest story today]\n"
        "ACTION: [Start 'For you, this means...' — 1 sentence]\n\n"
        f"Story: {item['title']}\nDetails: {item['summary_raw'][:700]}\n\n"
        "Output ONLY the 3 labeled lines."
    )
    raw    = ollama_generate(prompt, timeout=60)
    h_title  = item["plain_headline"] or item["title"]
    h_why    = ""
    h_action = item.get("impact", "")
    if raw:
        for line in raw.split("\n"):
            l = line.strip()
            u = l.upper()
            if u.startswith("HEADLINE:"):
                t = l[9:].strip().strip('"')
                if t:
                    h_title = t
            elif u.startswith("WHY:"):
                h_why = l[4:].strip()
            elif u.startswith("ACTION:"):
                h_action = l[7:].strip()
    return h_title, h_why, h_action

def top3_summary(items):
    top   = sorted(items, key=lambda x: x["score"], reverse=True)[:8]
    lines = "\n".join(f"- {i['title']}" for i in top)
    prompt = (
        "Write a 3-sentence morning briefing about AI news for someone who uses AI at work "
        "but is not a developer. Plain English only.\n\n"
        "1. The biggest thing that happened today in AI\n"
        "2. The most interesting trend or competitive move between AI companies\n"
        "3. One practical takeaway for someone who relies on AI tools daily\n\n"
        f"Today's headlines:\n{lines}\n\n"
        "Output only the 3 sentences, numbered 1. 2. 3."
    )
    return ollama_generate(prompt, timeout=120)

# ── Jargon buster ─────────────────────────────────────────────────────────────

def jargon_wrap(html_text):
    """Wrap known AI terms with hover tooltip spans (applied to already-escaped HTML)."""
    for term, definition in JARGON_GLOSSARY.items():
        def_esc = definition.replace('"', '&quot;')
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        repl    = f'<span class="jargon" title="{def_esc}">\\g<0></span>'
        html_text, _n = pattern.subn(repl, html_text, count=1)
    return html_text

# ── HTML template ──────────────────────────────────────────────────────────────

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI Brief — {date}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
:root{{
  --bg:#0a0a0f;--card:#111118;--border:#1e1e2c;
  --text:#f0f0f5;--muted:#6b7080;--soft:#9aa0b5;
  --accent:#10b981;--amber:#f59e0b;
  --font:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
  --max:680px;
}}
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--text);font-family:var(--font);font-size:15px;line-height:1.65;-webkit-font-smoothing:antialiased}}

/* ── HEADER ── */
header{{border-bottom:1px solid var(--border);padding:20px 0 16px}}
.hdr-inner{{max-width:var(--max);margin:0 auto;padding:0 24px;display:flex;align-items:baseline;justify-content:space-between;gap:12px}}
.hdr-brand{{font-size:20px;font-weight:800;letter-spacing:-.03em;color:var(--text)}}
.hdr-brand span{{color:var(--accent)}}
.hdr-meta{{font-size:12px;color:var(--muted)}}

/* ── PAGE ── */
.page{{max-width:var(--max);margin:0 auto;padding:28px 24px 80px}}

/* ── MORNING BRIEF ── */
.brief{{background:var(--card);border:1px solid var(--border);border-left:3px solid var(--accent);border-radius:6px;padding:18px 20px;margin-bottom:36px}}
.brief-label{{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.12em;color:var(--accent);margin-bottom:10px}}
.brief-text{{font-size:14px;line-height:1.8;color:var(--soft)}}
.brief-text p{{margin-bottom:6px}}
.brief-text p:last-child{{margin-bottom:0}}
.brief-offline{{font-size:13px;color:var(--muted);font-style:italic}}

/* ── SECTION ── */
.section{{margin-bottom:36px}}
.sec-title{{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.12em;color:var(--muted);margin-bottom:14px;display:flex;align-items:center;gap:8px}}
.sec-title::after{{content:'';flex:1;height:1px;background:var(--border)}}

/* ── STORY ROW ── */
.story{{padding:14px 0;border-bottom:1px solid var(--border)}}
.story:last-child{{border-bottom:none}}
.story-source{{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);margin-bottom:5px}}
.story-headline{{font-size:15px;font-weight:600;line-height:1.4;margin-bottom:6px}}
.story-headline a{{color:var(--text);text-decoration:none}}
.story-headline a:hover{{color:var(--accent)}}
.story-summary{{font-size:13.5px;color:var(--soft);line-height:1.65}}
.story-impact{{font-size:13px;color:var(--accent);margin-top:5px}}
.story-impact::before{{content:'→ ';font-weight:700}}

/* ── RELEASE ROW ── */
.release{{padding:16px;background:var(--card);border:1px solid var(--border);border-left:3px solid var(--amber);border-radius:6px;margin-bottom:10px}}
.release:last-child{{margin-bottom:0}}
.rel-source{{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:var(--amber);margin-bottom:5px}}
.rel-headline{{font-size:15px;font-weight:600;line-height:1.4;margin-bottom:8px}}
.rel-headline a{{color:var(--text);text-decoration:none}}
.rel-headline a:hover{{color:var(--amber)}}
.rel-what{{font-size:13.5px;color:var(--soft);font-style:italic;margin-bottom:8px;line-height:1.6}}
.rel-bullets{{display:flex;flex-direction:column;gap:4px;margin-bottom:8px}}
.rel-bullet{{font-size:13.5px;color:var(--soft);padding-left:16px;position:relative;line-height:1.5}}
.rel-bullet::before{{content:'✓';position:absolute;left:0;color:var(--amber);font-weight:700}}
.rel-impact{{font-size:13px;color:var(--amber)}}
.rel-impact::before{{content:'→ ';font-weight:700}}

/* ── NL BULLETS ── */
.nl-bullets{{display:flex;flex-direction:column;gap:4px}}
.nl-bullet{{font-size:13.5px;color:var(--soft);padding-left:14px;position:relative;line-height:1.6}}
.nl-bullet::before{{content:'·';position:absolute;left:0;color:var(--accent);font-weight:700;font-size:18px;line-height:1.1}}

/* ── JARGON ── */
.jargon{{border-bottom:1px dotted var(--accent);cursor:help;position:relative}}
.jargon[title]:hover::after{{content:attr(title);position:absolute;bottom:calc(100% + 4px);left:0;background:#1a1a2e;border:1px solid var(--border);border-radius:6px;padding:7px 11px;font-size:12px;color:var(--text);white-space:normal;max-width:220px;z-index:200;line-height:1.5;pointer-events:none;box-shadow:0 6px 24px rgba(0,0,0,.6)}}

/* ── FOOTER ── */
.foot{{border-top:1px solid var(--border);padding:20px 24px;max-width:var(--max);margin:0 auto;font-size:12px;color:var(--muted);display:flex;justify-content:space-between}}

@media(max-width:600px){{.page{{padding:20px 16px 60px}}.hdr-inner{{padding:0 16px}}}}
</style>
</head>
<body>

<header>
  <div class="hdr-inner">
    <div class="hdr-brand">AI<span>Brief</span></div>
    <div class="hdr-meta">{date} &nbsp;·&nbsp; {count} stories</div>
  </div>
</header>

<div class="page">
  {brief_block}
  {releases_block}
  {news_block}
  {creators_block}
  {x_block}
</div>

<div class="foot">
  <span>AI Brief — your daily AI digest</span>
  <span>{releases} releases · {trending_count} trending</span>
</div>

</body>
</html>"""


# ── Render helpers ─────────────────────────────────────────────────────────────

def make_card(item):
    """Render a story as a simple digest row: source · headline · 1-line summary."""
    plain_h = item.get("plain_headline", "").strip()
    impact  = item.get("impact", "").strip()
    title_text = plain_h if (plain_h and plain_h.lower() != item["title"].lower()) else item["title"]

    s = item.get("ai_summary", "")
    summary_html = ""
    if s:
        if item["type"] == "newsletter":
            lines = [l.strip().lstrip("•-").strip() for l in s.split("\n") if l.strip().startswith(("•", "-"))]
            if not lines:
                lines = [l.strip() for l in s.split("\n") if l.strip()][:3]
            bullets = "".join(f'<div class="nl-bullet">{jargon_wrap(esc(l))}</div>' for l in lines[:3])
            summary_html = f'<div class="nl-bullets">{bullets}</div>'
        else:
            first_line = s.split("\n")[0].strip()
            summary_html = f'<div class="story-summary">{jargon_wrap(esc(first_line))}</div>'

    impact_html = f'<div class="story-impact">{jargon_wrap(esc(impact))}</div>' if impact and not s else ""

    return (
        f'<div class="story">'
        f'<div class="story-source">{esc(item["source"])}</div>'
        f'<div class="story-headline"><a href="{item["link"]}" target="_blank" rel="noopener">{esc(title_text)}</a></div>'
        f'{summary_html}{impact_html}'
        f'</div>'
    )

def make_release_card(item):
    """Render a release as an amber-accented row."""
    plain_h = item.get("plain_headline", "").strip()
    impact  = item.get("impact", "").strip()
    title_text = plain_h if (plain_h and plain_h.lower() != item["title"].lower()) else item["title"]

    s = item.get("ai_summary", "")
    what = imp_line = ""
    bullets = []
    if s:
        for line in s.split("\n"):
            l = line.strip(); u = l.upper()
            if u.startswith("WHAT:"):     what     = l[5:].strip()
            elif u.startswith("IMPACT:"): imp_line = l[7:].strip()
            elif l.startswith(("•", "-")): bullets.append(l.lstrip("•-").strip())
        if not imp_line: imp_line = impact
    else:
        imp_line = impact

    what_h   = f'<div class="rel-what">{jargon_wrap(esc(what))}</div>' if what else ""
    bul_h    = ('<div class="rel-bullets">' +
                "".join(f'<div class="rel-bullet">{jargon_wrap(esc(b))}</div>' for b in bullets[:3]) +
                "</div>") if bullets else ""
    impact_h = f'<div class="rel-impact">{jargon_wrap(esc(imp_line))}</div>' if imp_line else ""

    return (
        f'<div class="release">'
        f'<div class="rel-source">{esc(item["source"])}</div>'
        f'<div class="rel-headline"><a href="{item["link"]}" target="_blank" rel="noopener">{esc(title_text)}</a></div>'
        f'{what_h}{bul_h}{impact_h}'
        f'</div>'
    )


# ── Build HTML ─────────────────────────────────────────────────────────────────

def _section(emoji_title, rows_html):
    return (
        f'<div class="section">'
        f'<div class="sec-title">{emoji_title}</div>'
        f'{rows_html}'
        f'</div>'
    )

def build_html(items, top3, ollama_ok, date_str, archive_dir):
    by_score = sorted(items, key=lambda x: x["score"], reverse=True)

    # Morning brief
    if top3:
        lines = [l.strip() for l in top3.split("\n") if l.strip()]
        paras = "".join(f"<p>{esc(l)}</p>" for l in lines)
        brief_block = (
            f'<div class="brief">'
            f'<div class="brief-label">Morning Brief</div>'
            f'<div class="brief-text">{paras}</div>'
            f'</div>'
        )
    else:
        brief_block = (
            '<div class="brief">'
            '<div class="brief-label">Morning Brief</div>'
            '<div class="brief-offline">Start Ollama to generate your daily briefing.</div>'
            '</div>'
        )

    # 🚀 What Launched — releases only, up to 6
    release_items = [i for i in by_score if i.get("is_release")][:6]
    releases_block = ""
    if release_items:
        rows = "".join(make_release_card(i) for i in release_items)
        releases_block = _section("🚀 What Launched", rows)

    # 📰 Top Stories — lab + news + newsletter, up to 8
    news_cats = {"lab", "news", "newsletter"}
    news_items = [i for i in by_score if i.get("category") in news_cats and not i.get("is_release")][:8]
    news_block = ""
    if news_items:
        rows = "".join(make_card(i) for i in news_items)
        news_block = _section("📰 Top Stories", rows)

    # 📺 Creator Picks — YouTube creators, up to 6
    creator_items = [i for i in by_score if i.get("category") == "creator"][:6]
    creators_block = ""
    if creator_items:
        rows = "".join(make_card(i) for i in creator_items)
        creators_block = _section("📺 Creator Picks", rows)

    # 🐦 From X — X/Twitter, up to 6
    x_items = [i for i in by_score if i.get("category") == "x"][:6]
    x_block = ""
    if x_items:
        rows = "".join(make_card(i) for i in x_items)
        x_block = _section("🐦 From X", rows)

    releases_count = sum(1 for i in items if i.get("is_release"))
    trending_count = sum(1 for i in items if i.get("trending"))

    return HTML.format(
        date=date_str,
        count=len(items),
        releases=releases_count,
        trending_count=trending_count,
        brief_block=brief_block,
        releases_block=releases_block,
        news_block=news_block,
        creators_block=creators_block,
        x_block=x_block,
    )


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    date_str     = datetime.now().strftime("%B %d, %Y  %H:%M")
    today_ds     = datetime.now().strftime("%Y-%m-%d")
    archive_name = f"dashboard-{today_ds}.html"
    script_dir   = os.path.dirname(os.path.abspath(__file__))
    out_path     = os.path.join(script_dir, "dashboard.html")
    archive_dir  = os.path.join(script_dir, "archive")
    archive_path = os.path.join(archive_dir, archive_name)

    os.makedirs(archive_dir, exist_ok=True)

    print("Fetching feeds...")
    all_items = []
    for name, cfg in FEEDS.items():
        print(f"  {name}...", end=" ", flush=True)
        fetched = fetch_feed(name, cfg)
        print(len(fetched))
        all_items.extend(fetched)

    # X bookmarks (requires X_AUTH_TOKEN + X_CT0 in .env)
    if os.environ.get("X_AUTH_TOKEN") and os.environ.get("X_CT0"):
        try:
            from x_fetcher import fetch_bookmarks
            print("  X: My Bookmarks...", end=" ", flush=True)
            bm = fetch_bookmarks(40)
            print(len(bm))
            all_items.extend(bm)
        except Exception as e:
            print(f"0 (error: {e})")

    # YouTube subscriptions via API (requires YOUTUBE_API_KEY in .env)
    if os.environ.get("YOUTUBE_API_KEY"):
        try:
            from youtube_fetcher import fetch_subscriptions, fill_missing_channel_ids
            filled = fill_missing_channel_ids()
            if filled:
                print(f"  YouTube: filled {filled} missing channel IDs")
            print("  YouTube: My Subscriptions (AI)...", end=" ", flush=True)
            yt = fetch_subscriptions(categories=["ai"], max_per_channel=3, window_hours=336)
            print(len(yt))
            all_items.extend(yt)
        except Exception as e:
            print(f"0 (error: {e})")

    # Instagram (requires IG_SESSION_ID in .env)
    if os.environ.get("IG_SESSION_ID"):
        try:
            from instagram_fetcher import fetch_instagram
            print("  Instagram: AI accounts...", end=" ", flush=True)
            ig = fetch_instagram(max_per_account=3, window_hours=168, ai_only=True)
            print(len(ig))
            all_items.extend(ig)
        except Exception as e:
            print(f"0 (error: {e})")

    print(f"\n{len(all_items)} total items")

    # Detection pipeline
    for item in all_items:
        is_r, pred = detect_release(item)
        item["is_release"]  = is_r
        item["predecessor"] = pred
        item["story_type"]  = classify_story(item)
        item["about"]       = detect_about(item)

    detect_trending(all_items)

    for item in all_items:
        item["score"]           = score_item(item)
        item["revolution_level"]= detect_revolution_level(item)
        item["hype_type"]       = detect_hype_type(item)
        item["life_area"]       = detect_life_area(item)
        item["read_time"]       = calc_read_time(item)

    # Label releases per source
    _ORDER_LABELS  = ["Latest Release", "Previous Release", "Earlier Release", "Archive"]
    _src_releases  = defaultdict(list)
    for item in all_items:
        if item["is_release"]:
            _src_releases[item["source"]].append(item)
    for src_rels in _src_releases.values():
        epoch = datetime.min.replace(tzinfo=timezone.utc)
        src_rels.sort(key=lambda x: x.get("date_raw") or epoch, reverse=True)
        for idx, rel in enumerate(src_rels):
            rel["release_order_label"] = _ORDER_LABELS[min(idx, len(_ORDER_LABELS) - 1)]

    # Mark new items (compare vs yesterday's archive)
    mark_new_today(all_items, archive_dir)

    releases = sum(1 for i in all_items if i["is_release"])
    trending = sum(1 for i in all_items if i["trending"])
    print(f"Releases: {releases}  |  Trending: {trending}")

    ollama_ok = ollama_available()
    print(f"Ollama: {'✓ on' if ollama_ok else '✗ offline'}")

    if ollama_ok:
        print("\nSummarizing in plain English...")
        for idx, item in enumerate(all_items):
            print(f"  [{idx+1}/{len(all_items)}] {item['source']}: {item['title'][:60]}...")
            if item["is_release"]:
                raw = summarize_release(item)
                item["ai_summary"] = raw
                # Extract IMPACT from release format
                if raw:
                    for line in raw.split("\n"):
                        l = line.strip()
                        if l.upper().startswith("IMPACT:"):
                            item["impact"] = l[7:].strip()
            elif item["type"] == "newsletter":
                item["ai_summary"] = summarize_newsletter(item)
            else:
                ph, sm, imp = summarize_combined(item)
                item["plain_headline"] = ph
                item["ai_summary"]     = sm
                item["impact"]         = imp

        # Story of the day hero (top-scored item)
        top_item = max(all_items, key=lambda x: x["score"])
        print(f"\nStory of the day: {top_item['title'][:60]}...")
        h_title, h_why, h_action = summarize_story_of_day(top_item)
        top_item["hero_title"]  = h_title
        top_item["hero_why"]    = h_why
        top_item["hero_action"] = h_action

        print("\nWriting morning brief...")
        top3 = top3_summary(all_items)
    else:
        top3 = None

    print("\nBuilding dashboard...")
    html = build_html(all_items, top3, ollama_ok, date_str, archive_dir)

    for path in (out_path, archive_path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
    print(f"Saved → {out_path}")
    print(f"Archived → {archive_path}")

    write_archive_summary(all_items, archive_dir, today_ds)

    webbrowser.open(f"file://{out_path}")
    print("Done.")

if __name__ == "__main__":
    main()
