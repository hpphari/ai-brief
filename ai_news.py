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
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root{{
  --bg:#08090f;--s1:#0e1018;--s2:#14151f;--s3:#1a1b27;
  --border:#1f2133;--border2:#262840;
  --text:#eef0f8;--muted:#5a6080;--dim:#2a2e45;
  --accent:#10b981;--accent-dim:rgba(16,185,129,.12);--accent-border:rgba(16,185,129,.25);
  --amber:#f59e0b;--amber-dim:rgba(245,158,11,.10);--amber-border:rgba(245,158,11,.22);
  --red:#f87171;--blue:#60a5fa;
  --r:8px;
  --font:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
  --mono:'JetBrains Mono','Courier New',monospace;
}}
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--text);font-family:var(--font);font-size:14px;line-height:1.6;min-height:100vh;-webkit-font-smoothing:antialiased}}

/* ── NAV ── */
nav{{position:sticky;top:0;z-index:100;background:rgba(8,9,15,.93);backdrop-filter:blur(20px);border-bottom:1px solid var(--border);padding:0 28px;height:52px;display:flex;align-items:center;justify-content:space-between;gap:16px}}
.brand{{display:flex;align-items:center;gap:12px}}
.brand-mark{{width:30px;height:30px;border-radius:7px;background:var(--accent);display:flex;align-items:center;justify-content:center;font-size:15px;font-weight:900;color:#000;flex-shrink:0;font-family:var(--mono)}}
.brand-name{{font-size:15px;font-weight:800;letter-spacing:-.02em}}
.brand-date{{font-size:11px;color:var(--muted);font-family:var(--mono)}}
.nav-right{{display:flex;align-items:center;gap:20px}}
.nav-stat{{font-size:12px;color:var(--muted);display:flex;align-items:center;gap:5px}}
.nav-stat strong{{color:var(--text);font-weight:700}}
.nav-dot{{width:6px;height:6px;border-radius:50%;flex-shrink:0}}

/* ── FILTER BAR ── */
.filter-wrap{{background:var(--s1);border-bottom:1px solid var(--border)}}
.filter-primary{{padding:0 28px;display:flex;align-items:center;gap:0;overflow-x:auto;scrollbar-width:none;border-bottom:1px solid var(--border)}}
.filter-primary::-webkit-scrollbar{{display:none}}
.tab{{padding:0 16px;height:42px;font-size:13px;font-weight:600;cursor:pointer;background:transparent;border:none;color:var(--muted);border-bottom:2px solid transparent;transition:all .15s;user-select:none;white-space:nowrap;flex-shrink:0;display:flex;align-items:center;gap:6px;margin-bottom:-1px}}
.tab.on{{color:var(--text);border-bottom-color:var(--accent)}}
.tab:hover{{color:var(--text)}}
.tab-count{{font-size:10.5px;color:var(--muted);background:var(--s2);border:1px solid var(--border);padding:0 6px;border-radius:999px;line-height:1.6}}
.tab.on .tab-count{{color:var(--accent);border-color:var(--accent-border);background:var(--accent-dim)}}
.filter-sources{{padding:0 28px;height:34px;display:flex;align-items:center;gap:4px;overflow-x:auto;scrollbar-width:none}}
.filter-sources::-webkit-scrollbar{{display:none}}
.src-label{{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:var(--dim);margin-right:6px;white-space:nowrap;flex-shrink:0}}
.src-cat{{font-size:11.5px;font-weight:600;padding:2px 11px;border-radius:4px;cursor:pointer;color:var(--muted);background:transparent;border:1px solid transparent;transition:all .15s;user-select:none;white-space:nowrap;flex-shrink:0}}
.src-cat.on{{color:var(--text);background:var(--s2);border-color:var(--border)}}
.src-cat:hover{{color:var(--text)}}
.src-dot{{width:5px;height:5px;border-radius:50%;display:inline-block;margin-right:4px;vertical-align:middle}}

/* ── LAYOUT ── */
.layout{{max-width:1120px;margin:0 auto;padding:28px 28px 80px;display:grid;grid-template-columns:1fr 264px;gap:28px;align-items:start}}
.main{{min-width:0}}
.sidebar{{display:flex;flex-direction:column;gap:14px;position:sticky;top:94px}}

/* ── HERO ── */
.hero{{grid-column:1/-1;background:var(--s1);border:1px solid var(--border);border-top:2px solid var(--accent);border-radius:var(--r);padding:26px 30px;margin-bottom:4px;position:relative;overflow:hidden}}
.hero::before{{content:'';position:absolute;top:0;left:0;right:0;bottom:0;background:radial-gradient(ellipse at 0% 0%,rgba(16,185,129,.05) 0%,transparent 60%);pointer-events:none}}
.hero-eyebrow{{font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:.12em;color:var(--accent);margin-bottom:10px;display:flex;align-items:center;gap:8px}}
.hero-eyebrow::before{{content:'';display:block;width:18px;height:2px;background:var(--accent)}}
.hero-headline{{font-size:22px;font-weight:800;line-height:1.25;letter-spacing:-.03em;color:var(--text);margin-bottom:10px}}
.hero-headline a{{color:inherit;text-decoration:none}}
.hero-headline a:hover{{color:var(--accent)}}
.hero-why{{font-size:14px;color:#8892aa;line-height:1.75;margin-bottom:14px}}
.hero-footer{{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:12px}}
.hero-impact{{display:inline-flex;align-items:flex-start;gap:6px;background:var(--accent-dim);border:1px solid var(--accent-border);border-radius:6px;padding:9px 13px;font-size:12.5px;color:var(--accent);line-height:1.5}}
.hero-impact::before{{content:'→';flex-shrink:0;margin-top:1px}}

/* ── MORNING BRIEF ── */
.brief{{grid-column:1/-1;background:var(--s1);border:1px solid var(--border);border-radius:var(--r);padding:18px 24px;margin-bottom:4px;display:flex;gap:16px;align-items:flex-start}}
.brief-icon{{font-size:20px;line-height:1;margin-top:2px;flex-shrink:0}}
.brief-inner{{flex:1}}
.brief-label{{font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:.12em;color:var(--muted);margin-bottom:8px}}
.brief-text{{font-size:13.5px;line-height:1.85;color:#9aa3c0}}
.brief-text p{{margin-bottom:4px}}
.brief-text p:last-child{{margin-bottom:0}}
.brief-offline{{font-size:13px;color:var(--muted);font-style:italic}}

/* ── SIDEBAR WIDGETS ── */
.widget{{background:var(--s1);border:1px solid var(--border);border-radius:var(--r);padding:16px 18px}}
.widget-label{{font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:.12em;color:var(--muted);margin-bottom:14px}}
.tl-days{{display:flex;gap:4px;align-items:flex-end}}
.tl-day{{display:flex;flex-direction:column;align-items:center;gap:4px;flex:1}}
.tl-bar-wrap{{height:48px;display:flex;align-items:flex-end;width:100%}}
.tl-fill{{width:100%;background:var(--s3);border-radius:3px 3px 0 0;min-height:3px}}
.tl-today .tl-fill{{background:var(--accent)}}
.tl-name{{font-size:10px;color:var(--muted);font-family:var(--mono)}}
.tl-today .tl-name{{color:var(--accent);font-weight:700}}
.tl-cnt{{font-size:9px;color:var(--dim)}}
.sb-row{{display:flex;align-items:center;gap:8px;margin-bottom:10px}}
.sb-row:last-child{{margin-bottom:0}}
.sb-name{{font-size:12px;color:var(--text);width:68px;flex-shrink:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.sb-bar-wrap{{flex:1;background:var(--s3);border-radius:2px;height:4px;overflow:hidden}}
.sb-bar{{height:100%;background:var(--accent);border-radius:2px;opacity:.7}}
.sb-cnt{{font-size:11px;color:var(--muted);width:18px;text-align:right;flex-shrink:0}}

/* ── SECTION HEADERS ── */
.section-head{{display:flex;align-items:center;gap:10px;margin:24px 0 12px;padding-bottom:10px;border-bottom:1px solid var(--border)}}
.section-head:first-child{{margin-top:0}}
.section-label{{font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:.1em;color:var(--text)}}
.section-count{{font-size:11px;color:var(--muted);background:var(--s2);border:1px solid var(--border);padding:1px 8px;border-radius:999px;margin-left:auto}}

/* ── RELEASE GRID ── */
.release-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(288px,1fr));gap:12px}}
.release-card{{background:#0c0900;border:1px solid #2a1c00;border-top:2px solid var(--amber);border-radius:var(--r);padding:16px 18px;display:flex;flex-direction:column;gap:9px;transition:border-color .12s,box-shadow .12s}}
.release-card:hover{{border-color:#3d2900;box-shadow:0 4px 24px rgba(245,158,11,.1)}}
.rc-header{{display:flex;align-items:center;gap:6px;flex-wrap:wrap}}
.rc-headline{{font-size:14px;font-weight:700;line-height:1.35;letter-spacing:-.01em}}
.rc-headline a{{color:var(--text);text-decoration:none}}
.rc-headline a:hover{{color:var(--amber)}}
.rc-orig{{font-size:11px;color:var(--muted);margin-top:1px;line-height:1.4}}
.rc-what{{font-size:12.5px;color:#fef3c7;font-style:italic;line-height:1.5}}
.rc-bullets{{display:flex;flex-direction:column;gap:5px}}
.rc-bullet{{font-size:12.5px;color:#d4d8e8;display:flex;gap:7px;line-height:1.45}}
.rc-bullet::before{{content:'✓';color:var(--amber);flex-shrink:0;font-weight:700}}
.rc-who{{font-size:11.5px;color:#6ee7b7;padding-top:8px;border-top:1px solid #2a1c00}}
.rc-impact{{font-size:12px;color:var(--amber);display:flex;gap:5px;align-items:flex-start}}
.rc-impact::before{{content:'→';flex-shrink:0}}

/* ── STORY LIST ── */
.story-list{{display:flex;flex-direction:column}}
.story{{padding:13px 14px;border-radius:var(--r);border:1px solid transparent;display:flex;flex-direction:column;gap:5px;transition:background .1s,border-color .1s}}
.story:hover{{background:var(--s2);border-color:var(--border)}}
.story-meta{{display:flex;align-items:center;gap:6px;flex-wrap:wrap}}
.src-chip{{font-size:10.5px;font-weight:700;padding:2px 8px;border-radius:4px;border:1px solid;white-space:nowrap}}
.badge-new{{font-size:9.5px;font-weight:800;padding:2px 6px;border-radius:4px;background:var(--accent-dim);color:var(--accent);border:1px solid var(--accent-border);letter-spacing:.06em;text-transform:uppercase}}
.badge-hot{{font-size:10px;padding:2px 6px;border-radius:4px;background:rgba(239,68,68,.08);color:#f87171;border:1px solid rgba(239,68,68,.2)}}
.badge-release-sm{{font-size:9.5px;font-weight:800;padding:2px 6px;border-radius:4px;background:var(--amber-dim);color:var(--amber);border:1px solid var(--amber-border);letter-spacing:.06em;text-transform:uppercase}}
.story-time{{font-size:10.5px;color:var(--dim);font-family:var(--mono);margin-left:auto}}
.story-headline{{font-size:14.5px;font-weight:700;line-height:1.35;letter-spacing:-.01em;color:var(--text)}}
.story-headline a{{color:inherit;text-decoration:none}}
.story-headline a:hover{{color:var(--accent)}}
.story-orig{{font-size:11px;color:var(--muted);margin-top:1px;line-height:1.4}}
.story-summary{{font-size:13px;color:#7a83a0;line-height:1.65}}
.story-impact{{font-size:12.5px;color:var(--accent);display:flex;gap:5px;align-items:flex-start}}
.story-impact::before{{content:'→';flex-shrink:0}}
.nl-bullets{{display:flex;flex-direction:column;gap:3px;margin-top:1px}}
.nl-bullet{{font-size:13px;color:#7a83a0;display:flex;gap:7px;line-height:1.55}}
.nl-bullet::before{{content:'·';color:var(--accent);flex-shrink:0;font-weight:700;font-size:16px;line-height:1.2}}

/* ── JARGON ── */
.jargon{{border-bottom:1px dotted var(--accent);cursor:help;position:relative}}
.jargon[title]:hover::after{{content:attr(title);position:absolute;bottom:100%;left:0;background:var(--s2);border:1px solid var(--border2);border-radius:6px;padding:6px 10px;font-size:11.5px;color:var(--text);white-space:normal;max-width:220px;z-index:200;margin-bottom:5px;line-height:1.5;pointer-events:none;box-shadow:0 6px 20px rgba(0,0,0,.6)}}

/* ── STATES ── */
.ollama-warn{{background:#0e0700;border:1px solid #3a1a00;border-radius:var(--r);padding:11px 15px;font-size:13px;color:#fcd34d;display:flex;gap:10px;align-items:flex-start;margin-bottom:16px}}
.empty{{color:var(--muted);font-size:13px;padding:24px;text-align:center;background:var(--s1);border:1px dashed var(--border);border-radius:var(--r)}}

/* ── RESPONSIVE ── */
@media(max-width:860px){{.layout{{grid-template-columns:1fr;padding:20px 20px 60px}}.sidebar{{display:none}}.release-grid{{grid-template-columns:1fr}}}}
@media(max-width:580px){{nav,.filter-bar{{padding:0 16px}}.layout{{padding:16px 16px 60px}}.hero{{padding:20px 18px}}.hero-headline{{font-size:18px}}.brief{{padding:14px 16px}}}}
</style>
</head>
<body>

<nav>
  <div class="brand">
    <div class="brand-mark">AI</div>
    <div>
      <div class="brand-name">AI Brief</div>
      <div class="brand-date">{date}</div>
    </div>
  </div>
  <div class="nav-right">
    <div class="nav-stat"><span class="nav-dot" style="background:var(--amber)"></span><strong>{releases}</strong>&nbsp;releases</div>
    <div class="nav-stat"><span class="nav-dot" style="background:var(--red)"></span><strong>{trending_count}</strong>&nbsp;trending</div>
    <div class="nav-stat"><span class="nav-dot" style="background:var(--accent)"></span><strong>{count}</strong>&nbsp;stories</div>
  </div>
</nav>

<div class="filter-wrap">
  <div class="filter-primary">
    <span class="tab on"  data-f="all"><span class="tab-count">{count}</span> All</span>
    <span class="tab off" data-f="__rel__">🚀 Releases</span>
    <span class="tab off" data-f="__trend__">🔥 Trending</span>
    {new_today_tab}
  </div>
  <div class="filter-sources">
    <span class="src-label">Sources</span>
    <span class="src-cat off" data-f="__cat_lab__"><span class="src-dot" style="background:#4ade80"></span>Labs</span>
    <span class="src-cat off" data-f="__cat_news__"><span class="src-dot" style="background:#60a5fa"></span>News</span>
    <span class="src-cat off" data-f="__cat_creator__"><span class="src-dot" style="background:#c084fc"></span>Creators</span>
    <span class="src-cat off" data-f="__cat_x__"><span class="src-dot" style="background:#94a3b8"></span>X · Twitter</span>
  </div>
</div>

<div class="layout">

{hero_block}
{brief_block}

<div class="main">
  {warn_block}
  {releases_block}
  {trending_block}
  {all_block}
</div>

<div class="sidebar">
  {timeline_widget}
  {scoreboard_widget}
</div>

</div>

<script>
(function(){{
  const tabs     = document.querySelectorAll('.tab[data-f]');
  const srcCats  = document.querySelectorAll('.src-cat[data-f]');
  const allItems = Array.from(document.querySelectorAll('[data-src]'));
  const secRel   = document.getElementById('sec-releases');
  const secTrend = document.getElementById('sec-trending');
  const secAll   = document.getElementById('sec-all');

  function show(el){{if(el)el.style.display='';}}
  function hide(el){{if(el)el.style.display='none';}}
  function hasVisible(sec){{return sec&&[...sec.querySelectorAll('[data-src]')].some(c=>c.style.display!=='none');}}

  function clearSrcCats(){{srcCats.forEach(c=>{{c.classList.remove('on');c.classList.add('off');}});}}

  function applyFilter(f){{
    tabs.forEach(c=>{{c.classList.toggle('on',c.dataset.f===f);c.classList.toggle('off',c.dataset.f!==f);}});
    clearSrcCats();
    if(f==='all'){{
      show(secRel);show(secTrend);show(secAll);allItems.forEach(c=>c.style.display='');
    }}else if(f==='__rel__'){{
      show(secRel);hide(secTrend);hide(secAll);allItems.forEach(c=>c.style.display='');
    }}else if(f==='__trend__'){{
      hide(secRel);show(secTrend);hide(secAll);
      allItems.forEach(c=>{{c.style.display=c.dataset.trend==='1'?'':'none';}});
      if(!hasVisible(secTrend))hide(secTrend);
    }}else if(f==='__new_today__'){{
      show(secRel);show(secTrend);show(secAll);
      allItems.forEach(c=>{{c.style.display=c.dataset.newtoday==='1'?'':'none';}});
      if(!hasVisible(secRel))hide(secRel);if(!hasVisible(secTrend))hide(secTrend);
    }}
  }}

  function applySrcFilter(el, f){{
    const isOn = el.classList.contains('on');
    clearSrcCats();
    tabs.forEach(c=>{{c.classList.toggle('on',c.dataset.f==='all');c.classList.toggle('off',c.dataset.f!=='all');}});
    if(isOn){{
      allItems.forEach(c=>c.style.display='');
      show(secRel);show(secTrend);show(secAll);
      return;
    }}
    el.classList.add('on');el.classList.remove('off');
    const cat=f.replace('__cat_','').replace('__','');
    allItems.forEach(c=>{{c.style.display=c.dataset.cat===cat?'':'none';}});
    show(secRel);show(secTrend);show(secAll);
    if(!hasVisible(secRel))hide(secRel);
    if(!hasVisible(secTrend))hide(secTrend);
    const list=document.querySelector('#sec-all .story-list');
    if(list){{const vis=[...list.querySelectorAll('[data-src]')].filter(c=>c.style.display!=='none');vis.sort((a,b)=>parseInt(b.dataset.ts||0)-parseInt(a.dataset.ts||0));vis.forEach(c=>list.appendChild(c));}}
  }}

  tabs.forEach(c=>c.addEventListener('click',()=>applyFilter(c.dataset.f)));
  srcCats.forEach(c=>c.addEventListener('click',()=>applySrcFilter(c,c.dataset.f)));
}})();
</script>
</body>
</html>"""


# ── Render helpers ─────────────────────────────────────────────────────────────

def _src_chip(item):
    c = item["color"]
    return (f'<span class="src-chip" style="color:{c};background:{c}18;border-color:{c}44">'
            f'{esc(item["source"])}</span>')

def make_card(item, extra_class=""):
    """Render a story as a clean list row."""
    is_r   = item.get("is_release", False)
    is_t   = item.get("trending", False)
    is_new = item.get("is_new_today", False)
    area   = item.get("life_area") or ""
    plain_h = item.get("plain_headline", "").strip()
    impact  = item.get("impact", "").strip()
    ts      = int(item["date_raw"].timestamp()) if item.get("date_raw") else 0

    title_text = plain_h if (plain_h and plain_h.lower() != item["title"].lower()) else item["title"]
    orig_html  = (f'<div class="story-orig">{esc(item["title"])}</div>'
                  if (plain_h and plain_h.lower() != item["title"].lower()) else "")

    badges = _src_chip(item)
    if is_new: badges += '<span class="badge-new">NEW</span>'
    if is_t:   badges += '<span class="badge-hot">🔥 HOT</span>'
    if is_r:   badges += '<span class="badge-release-sm">🚀 RELEASE</span>'
    time_html = f'<span class="story-time">{esc(item["date"])}</span>'

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
            summary_html = f'<div class="story-summary">{jargon_wrap(esc(s))}</div>'

    impact_html = f'<div class="story-impact">{jargon_wrap(esc(impact))}</div>' if impact else ""

    return (
        f'<article class="story" data-src="{esc(item["source"])}" data-cat="{esc(item["category"])}" '
        f'data-rel="{"1" if is_r else "0"}" data-trend="{"1" if is_t else "0"}" '
        f'data-area="{esc(area)}" data-newtoday="{"1" if is_new else "0"}" data-ts="{ts}">\n'
        f'  <div class="story-meta">{badges}{time_html}</div>\n'
        f'  <div class="story-headline"><a href="{item["link"]}" target="_blank" rel="noopener">{esc(title_text)}</a></div>\n'
        f'  {orig_html}\n'
        f'  {summary_html}\n'
        f'  {impact_html}\n'
        f'</article>'
    )

def make_release_card(item):
    """Render a release as an amber-accented card."""
    is_t   = item.get("trending", False)
    is_new = item.get("is_new_today", False)
    area   = item.get("life_area") or ""
    plain_h = item.get("plain_headline", "").strip()
    impact  = item.get("impact", "").strip()
    ts      = int(item["date_raw"].timestamp()) if item.get("date_raw") else 0

    title_text = plain_h if (plain_h and plain_h.lower() != item["title"].lower()) else item["title"]
    orig_html  = (f'<div class="rc-orig">{esc(item["title"])}</div>'
                  if (plain_h and plain_h.lower() != item["title"].lower()) else "")

    badges = '<span class="badge-release-sm">🚀 RELEASE</span>' + _src_chip(item)
    if is_new: badges += '<span class="badge-new">NEW</span>'
    if is_t:   badges += '<span class="badge-hot">🔥 HOT</span>'

    s = item.get("ai_summary", "")
    what = who = imp_line = ""
    bullets = []
    if s:
        for line in s.split("\n"):
            l = line.strip(); u = l.upper()
            if u.startswith("WHAT:"):    what    = l[5:].strip()
            elif u.startswith("WHO:"):   who     = l[4:].strip()
            elif u.startswith("IMPACT:"): imp_line = l[7:].strip()
            elif l.startswith(("•", "-")): bullets.append(l.lstrip("•-").strip())
        if not imp_line: imp_line = impact
    else:
        imp_line = impact

    what_h    = f'<div class="rc-what">{jargon_wrap(esc(what))}</div>' if what else ""
    bul_h     = ('<div class="rc-bullets">' +
                 "".join(f'<div class="rc-bullet">{jargon_wrap(esc(b))}</div>' for b in bullets[:3]) +
                 "</div>") if bullets else ""
    who_h     = f'<div class="rc-who">Best for: {esc(who)}</div>' if who else ""
    impact_h  = f'<div class="rc-impact">{jargon_wrap(esc(imp_line))}</div>' if imp_line else ""
    no_sum_h  = '<div class="story-summary" style="font-style:italic;color:var(--muted)">Summary unavailable — run Ollama for summaries</div>' if not s else ""

    return (
        f'<div class="release-card" data-src="{esc(item["source"])}" data-cat="{esc(item["category"])}" '
        f'data-rel="1" data-trend="{"1" if is_t else "0"}" '
        f'data-area="{esc(area)}" data-newtoday="{"1" if is_new else "0"}" data-ts="{ts}">\n'
        f'  <div class="rc-header">{badges}'
        f'<span class="story-time">{esc(item["date"])}</span></div>\n'
        f'  <div class="rc-headline"><a href="{item["link"]}" target="_blank" rel="noopener">{esc(title_text)}</a></div>\n'
        f'  {orig_html}{what_h}{bul_h}{who_h}{impact_h}{no_sum_h}\n'
        f'</div>'
    )


# ── Build HTML ─────────────────────────────────────────────────────────────────

def build_html(items, top3, ollama_ok, date_str, archive_dir):
    releases  = [i for i in items if i.get("is_release")]
    trending  = [i for i in items if i.get("trending") and not i.get("is_release")]
    all_items = sorted(items, key=lambda x: x["score"], reverse=True)

    # Hero
    hero_block = ""
    top_item = all_items[0] if all_items else None
    if top_item:
        h_title  = top_item.get("hero_title") or top_item.get("plain_headline") or top_item["title"]
        h_why    = top_item.get("hero_why", "")
        h_action = top_item.get("hero_action", "") or top_item.get("impact", "")
        color    = top_item["color"]
        why_html    = f'<div class="hero-why">{esc(h_why)}</div>' if h_why else ""
        impact_html = f'<div class="hero-impact">{jargon_wrap(esc(h_action))}</div>' if h_action else ""
        hero_block = (
            f'<div class="hero">\n'
            f'  <div class="hero-eyebrow">Story of the Day</div>\n'
            f'  <div class="hero-headline"><a href="{top_item["link"]}" target="_blank" rel="noopener">{esc(h_title)}</a></div>\n'
            f'  {why_html}\n'
            f'  <div class="hero-footer">'
            f'<span class="src-chip" style="color:{color};background:{color}18;border-color:{color}44">{esc(top_item["source"])}</span>'
            f'<span class="story-time">{esc(top_item["date"])}</span></div>\n'
            f'  {impact_html}\n'
            f'</div>'
        )

    # Morning brief
    if top3:
        lines = [l.strip() for l in top3.split("\n") if l.strip()]
        paras = "".join(f"<p>{esc(l)}</p>" for l in lines)
        brief_block = (
            f'<div class="brief">'
            f'<div class="brief-icon">📰</div>'
            f'<div class="brief-inner"><div class="brief-label">Morning Brief</div>'
            f'<div class="brief-text">{paras}</div></div></div>'
        )
    else:
        brief_block = (
            '<div class="brief">'
            '<div class="brief-icon">📰</div>'
            '<div class="brief-inner"><div class="brief-label">Morning Brief</div>'
            '<div class="brief-offline">Start Ollama to generate your daily briefing.</div>'
            '</div></div>'
        )

    # Warn
    warn_block = ""
    if not ollama_ok:
        warn_block = (
            '<div class="ollama-warn"><span>⚠️</span><span>Ollama offline — '
            'run <code>ollama serve</code> and re-run for AI summaries.</span></div>'
        )

    # Releases
    releases_block = ""
    if releases:
        epoch      = datetime.min.replace(tzinfo=timezone.utc)
        sorted_rel = sorted(releases, key=lambda x: x.get("date_raw") or epoch, reverse=True)
        cards_html = "\n".join(make_release_card(i) for i in sorted_rel)
        releases_block = (
            f'<div id="sec-releases">'
            f'<div class="section-head">'
            f'<span class="section-label">🚀 What\'s New</span>'
            f'<span class="section-count">{len(releases)} release{"s" if len(releases)!=1 else ""}</span>'
            f'</div>'
            f'<div class="release-grid">{cards_html}</div>'
            f'</div>'
        )

    # Trending
    trending_block = ""
    if trending:
        sorted_t  = sorted(trending, key=lambda x: x["score"], reverse=True)
        stories   = "\n".join(make_card(i) for i in sorted_t)
        src_count = len(set(i["source"] for i in trending))
        trending_block = (
            f'<div id="sec-trending">'
            f'<div class="section-head">'
            f'<span class="section-label">🔥 Trending</span>'
            f'<span class="section-count">{src_count}+ sources</span>'
            f'</div>'
            f'<div class="story-list">{stories}</div>'
            f'</div>'
        )

    # All stories
    stories  = "\n".join(make_card(i) for i in all_items)
    all_block = (
        f'<div id="sec-all">'
        f'<div class="section-head">'
        f'<span class="section-label">All Stories</span>'
        f'<span class="section-count">{len(items)}</span>'
        f'</div>'
        f'<div class="story-list">{stories}</div>'
        f'</div>'
    )

    # Sidebar
    timeline_widget   = build_timeline_html(archive_dir)
    scoreboard_widget = build_scoreboard_html(items)

    # New today tab
    new_today_count = sum(1 for i in items if i.get("is_new_today"))
    new_today_tab   = ""
    if new_today_count:
        new_today_tab = (
            f'<span class="tab off" data-f="__new_today__">'
            f'✨ New Today <span class="tab-count">{new_today_count}</span></span>'
        )

    return HTML.format(
        date=date_str,
        count=len(items),
        releases=len(releases),
        trending_count=len(trending),
        hero_block=hero_block,
        brief_block=brief_block,
        warn_block=warn_block,
        releases_block=releases_block,
        trending_block=trending_block,
        all_block=all_block,
        timeline_widget=timeline_widget,
        scoreboard_widget=scoreboard_widget,
        new_today_tab=new_today_tab,
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
