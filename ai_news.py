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
        bar_h    = max(4, round(day["count"] / max_cnt * 52)) if day["count"] else 4
        today_c  = " tl-today" if day["today"] else ""
        cnt_str  = str(day["count"]) if day["count"] > 0 else "–"
        days_html += (
            f'<div class="tl-day{today_c}">'
            f'<span class="tl-name">{day["name"]}</span>'
            f'<div class="tl-bar-wrap"><div class="tl-fill" style="height:{bar_h}px"></div></div>'
            f'<span class="tl-cnt">{cnt_str}</span>'
            f'</div>'
        )
    return (
        f'<div class="timeline-strip">'
        f'<span class="tl-label">7-Day Activity</span>'
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
    ranked  = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:6]
    max_c   = ranked[0][1] or 1
    rows    = ""
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
        f'<div class="scoreboard">'
        f'<div class="sb-label">Company Activity</div>'
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
nav{{position:sticky;top:0;z-index:100;background:rgba(13,15,26,.94);backdrop-filter:blur(12px);border-bottom:1px solid var(--border);padding:10px 24px;display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}}
.nav-brand{{display:flex;align-items:center;gap:10px}}
.nav-brand h1{{font-size:1.1rem;font-weight:800;letter-spacing:-.02em;background:linear-gradient(135deg,#818cf8,#c084fc);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
.nav-meta{{font-size:.75rem;color:var(--muted)}}
.stat-pills{{display:flex;gap:6px;flex-wrap:wrap}}
.stat-pill{{padding:3px 10px;border-radius:999px;font-size:.72rem;font-weight:700;border:1px solid var(--border)}}

/* ── Timeline strip ── */
.timeline-strip{{background:var(--s1);border-bottom:1px solid var(--border);padding:8px 24px;display:flex;align-items:center;gap:16px;overflow-x:auto}}
.tl-label{{font-size:.65rem;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);white-space:nowrap;flex-shrink:0}}
.tl-days{{display:flex;gap:10px;align-items:flex-end}}
.tl-day{{display:flex;flex-direction:column;align-items:center;gap:3px;min-width:32px}}
.tl-name{{font-size:.62rem;color:var(--muted)}}
.tl-bar-wrap{{height:56px;display:flex;align-items:flex-end}}
.tl-fill{{width:20px;background:var(--border);border-radius:3px 3px 0 0;transition:height .3s;min-height:4px}}
.tl-today .tl-fill{{background:linear-gradient(180deg,#818cf8,#c084fc)}}
.tl-today .tl-name{{color:#818cf8;font-weight:700}}
.tl-cnt{{font-size:.6rem;color:var(--muted)}}
.tl-today .tl-cnt{{color:#818cf8}}

/* ── Filter bar ── */
.filter-bar{{padding:8px 24px;display:flex;flex-direction:column;gap:6px;border-bottom:1px solid var(--border);background:var(--s1)}}
.filter-row{{display:flex;flex-wrap:wrap;gap:5px;align-items:center}}
.filter-label{{font-size:.65rem;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);width:72px;flex-shrink:0}}
.chip{{padding:3px 11px;border-radius:999px;font-size:.72rem;font-weight:600;cursor:pointer;border:1.5px solid transparent;transition:all .15s;user-select:none;white-space:nowrap}}
.chip.on{{opacity:1}}
.chip.off{{opacity:.28}}

/* ── Page body ── */
.page{{max-width:1320px;margin:0 auto;padding:24px 24px 60px}}

/* ── Hero / Story of the Day ── */
.hero{{background:linear-gradient(135deg,#13152a,#1a1435);border:1px solid #4c1d95;border-radius:var(--r);padding:28px 32px;margin-bottom:20px;position:relative;overflow:hidden}}
.hero::before{{content:'';position:absolute;top:-40px;right:-40px;width:200px;height:200px;background:radial-gradient(circle,#7c3aed22,transparent 70%);pointer-events:none}}
.hero-eyebrow{{font-size:.7rem;font-weight:800;text-transform:uppercase;letter-spacing:.1em;color:#a78bfa;margin-bottom:10px;display:flex;align-items:center;gap:8px}}
.hero-title{{font-size:1.45rem;font-weight:800;line-height:1.3;margin-bottom:10px}}
.hero-title a{{color:var(--text);text-decoration:none}}
.hero-title a:hover{{color:#c084fc}}
.hero-sub{{font-size:.95rem;color:#c7d2fe;line-height:1.7;margin-bottom:12px}}
.hero-meta{{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:12px}}
.hero-impact{{background:#1a0f2e;border-left:3px solid #7c3aed;border-radius:0 8px 8px 0;padding:10px 14px;font-size:.88rem;color:#e9d5ff;line-height:1.6}}

/* ── Brief + Scoreboard ── */
.brief-outer{{display:grid;grid-template-columns:1fr 240px;gap:16px;margin-bottom:24px;align-items:start}}
.brief{{background:linear-gradient(135deg,#1a1b2e,#1e1b3a);border:1px solid #3730a3;border-radius:var(--r);padding:22px 26px;border-left:4px solid #818cf8}}
.brief-label{{font-size:.68rem;font-weight:800;text-transform:uppercase;letter-spacing:.1em;color:#818cf8;margin-bottom:10px}}
.brief-text{{font-size:.95rem;line-height:1.85;color:#c7d2fe}}
.brief-text p{{margin-bottom:.5em}}

/* ── Company Scoreboard ── */
.scoreboard{{background:var(--s1);border:1px solid var(--border);border-radius:var(--r);padding:18px 20px}}
.sb-label{{font-size:.68rem;font-weight:800;text-transform:uppercase;letter-spacing:.1em;color:var(--muted);margin-bottom:12px}}
.sb-row{{display:flex;align-items:center;gap:8px;margin-bottom:8px}}
.sb-name{{font-size:.75rem;color:var(--text);width:74px;flex-shrink:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.sb-bar-wrap{{flex:1;background:var(--s2);border-radius:3px;height:6px;overflow:hidden}}
.sb-bar{{height:100%;background:linear-gradient(90deg,#818cf8,#c084fc);border-radius:3px;transition:width .4s}}
.sb-cnt{{font-size:.68rem;color:var(--muted);width:20px;text-align:right;flex-shrink:0}}

/* ── Section headers ── */
.section-head{{display:flex;align-items:center;gap:10px;margin-bottom:16px;margin-top:28px}}
.section-head h2{{font-size:.78rem;font-weight:800;text-transform:uppercase;letter-spacing:.1em}}
.section-head .dot{{width:6px;height:6px;border-radius:50%;flex-shrink:0}}
.section-count{{font-size:.7rem;color:var(--muted);padding:1px 8px;background:var(--s2);border-radius:999px;border:1px solid var(--border)}}
.section-divider{{flex:1;height:1px;background:var(--border)}}

/* ── Grids ── */
.grid-releases{{display:grid;grid-template-columns:repeat(auto-fill,minmax(380px,1fr));gap:16px;margin-bottom:8px}}
.grid-trending{{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:14px;margin-bottom:8px}}
.grid-all{{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:14px}}

/* ── Cards ── */
.card{{background:var(--s1);border:1px solid var(--border);border-radius:var(--r);padding:16px 18px;transition:transform .12s,box-shadow .12s;display:flex;flex-direction:column;gap:9px}}
.card:hover{{transform:translateY(-2px);box-shadow:0 8px 32px rgba(0,0,0,.4)}}
.card-release{{background:var(--amber-bg);border-color:#78350f;box-shadow:0 0 0 1px #92400e33}}
.card-release:hover{{box-shadow:0 8px 32px rgba(245,158,11,.15)}}
.card-trending{{background:#0f1a2e;border-color:#1e3a5f}}
.card-trending:hover{{box-shadow:0 8px 32px rgba(96,165,250,.12)}}

/* Card internals */
.card-top{{display:flex;justify-content:space-between;align-items:flex-start;gap:8px}}
.card-plain-headline{{font-size:.95rem;font-weight:700;line-height:1.4;flex:1}}
.card-plain-headline a{{color:var(--text);text-decoration:none}}
.card-plain-headline a:hover{{color:#818cf8}}
.card-orig-title{{font-size:.73rem;color:var(--muted);margin-top:2px;line-height:1.4}}
.card-score{{flex-shrink:0;font-size:.7rem;font-weight:700;padding:3px 7px;border-radius:6px;background:var(--s2);border:1px solid var(--border);white-space:nowrap}}
.score-5{{color:#34d399;border-color:#064e3b}}
.score-4{{color:#a3e635;border-color:#1a2e05}}
.score-3{{color:#fbbf24;border-color:#451a03}}
.score-low{{color:var(--muted)}}

.card-badges{{display:flex;flex-wrap:wrap;gap:4px;align-items:center}}
.badge{{display:inline-flex;align-items:center;gap:3px;padding:2px 8px;border-radius:999px;font-size:.65rem;font-weight:700;white-space:nowrap}}
.badge-trending{{background:#1e3a5f;color:#93c5fd;border:1px solid #1d4ed8}}
.badge-type{{border:1px solid currentColor;background:transparent;opacity:.85}}
.badge-new-today{{background:#052e16;color:#34d399;border:1px solid #065f46}}

/* Revolution-O-Meter */
.rev-badge{{padding:2px 8px;border-radius:999px;font-size:.65rem;font-weight:700;border:1px solid currentColor}}
.rev-game-changer{{color:#f87171;background:#1a0505}}
.rev-notable{{color:#fbbf24;background:#1c1202}}
.rev-incremental{{color:#60a5fa;background:#0c1a2e}}

/* Hype vs Real */
.hype-badge{{padding:2px 8px;border-radius:999px;font-size:.65rem;font-weight:700;border:1px solid currentColor}}
.hype-real{{color:#34d399;background:#052e16}}
.hype-research{{color:#a78bfa;background:#1e1040}}
.hype-opinion{{color:#94a3b8;background:#1e293b}}
.hype-hype{{color:#fb923c;background:#1c0a00}}

/* Life area */
.area-badge{{padding:2px 8px;border-radius:999px;font-size:.65rem;font-weight:700;border:1px solid currentColor}}

/* Read time */
.read-time{{font-size:.65rem;color:var(--muted);background:var(--s2);border:1px solid var(--border);padding:2px 7px;border-radius:999px}}

.card-meta{{font-size:.72rem;color:var(--muted);display:flex;gap:6px;align-items:center;flex-wrap:wrap}}

/* Card summary */
.card-summary{{font-size:.875rem;color:#c7d2fe;line-height:1.7;background:var(--s2);border-radius:8px;padding:11px 13px}}
.card-summary ul{{padding-left:14px;display:flex;flex-direction:column;gap:4px}}
.card-summary li{{list-style:none;padding-left:0}}
.card-summary li::before{{content:"→ ";color:var(--muted)}}

/* Impact box */
.impact-box{{background:#0a1628;border-left:3px solid #3b82f6;border-radius:0 6px 6px 0;padding:8px 12px;font-size:.82rem;color:#bfdbfe;line-height:1.6;margin-top:2px}}

/* Release card layouts */
.rel-what{{font-size:.83rem;color:#fef3c7;margin-bottom:8px;font-style:italic}}
.rel-bullets{{display:flex;flex-direction:column;gap:5px;margin-bottom:8px}}
.rel-bullet{{font-size:.83rem;color:#e8eaf6;display:flex;gap:7px}}
.rel-bullet::before{{content:"✓";color:#f59e0b;font-weight:700;flex-shrink:0}}
.rel-who{{font-size:.78rem;color:#6ee7b7;padding-top:6px;border-top:1px solid #78350f}}
.no-summary{{font-size:.78rem;color:var(--muted);font-style:italic}}

/* Before / After comparison */
.before-after{{display:flex;align-items:center;gap:8px;background:var(--s2);border-radius:8px;padding:10px 12px;margin-top:2px}}
.ba-col{{flex:1;text-align:center}}
.ba-lbl{{display:block;font-size:.6rem;font-weight:800;text-transform:uppercase;letter-spacing:.08em;margin-bottom:3px}}
.ba-old .ba-lbl{{color:#6b7280}}
.ba-new .ba-lbl{{color:#f59e0b}}
.ba-val{{font-size:.78rem;font-weight:600;color:var(--text)}}
.ba-old .ba-val{{color:#6b7280}}
.ba-arr{{font-size:1.2rem;color:#f59e0b;flex-shrink:0}}

/* Share button */
.share-btn{{background:transparent;border:1px solid var(--border);border-radius:6px;padding:4px 10px;font-size:.68rem;color:var(--muted);cursor:pointer;transition:all .15s;white-space:nowrap}}
.share-btn:hover{{border-color:#818cf8;color:#818cf8}}
.share-btn.copied{{border-color:#34d399;color:#34d399}}

/* Jargon tooltip */
.jargon{{border-bottom:1px dotted #818cf8;cursor:help;text-decoration:none}}
.jargon[title]:hover::after{{content:attr(title);position:absolute;background:#1e1b4b;border:1px solid #3730a3;border-radius:6px;padding:6px 10px;font-size:.75rem;color:#e0e7ff;white-space:normal;max-width:240px;z-index:200;margin-top:4px;line-height:1.5;pointer-events:none}}
.jargon[title]{{position:relative}}

/* Ollama warning */
.ollama-warn{{background:#1c0a00;border:1px solid #7c2d12;border-radius:var(--r);padding:12px 16px;font-size:.85rem;color:#fcd34d;margin-bottom:20px;display:flex;gap:10px;align-items:flex-start}}

/* Empty state */
.empty{{color:var(--muted);font-size:.85rem;padding:20px;text-align:center;background:var(--s1);border-radius:var(--r);border:1px dashed var(--border)}}

/* ── Mobile responsive ── */
@media (max-width:900px){{
  .brief-outer{{grid-template-columns:1fr}}
}}
@media (max-width:640px){{
  nav,.filter-bar,.page{{padding-left:14px;padding-right:14px}}
  .timeline-strip{{padding:6px 14px}}
  .grid-releases,.grid-trending,.grid-all{{grid-template-columns:1fr}}
  .hero{{padding:20px 18px}}
  .hero-title{{font-size:1.15rem}}
  .stat-pills{{display:none}}
  .filter-label{{width:56px;font-size:.6rem}}
  .card{{padding:13px 14px}}
  .before-after{{flex-direction:column;gap:4px}}
  .ba-arr{{transform:rotate(90deg)}}
  .brief{{padding:16px 18px}}
}}
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
    <span class="stat-pill" style="color:#34d399;border-color:#065f46">{new_today_count} new today</span>
    <span class="stat-pill" style="color:var(--muted)">{count} stories · {sources} sources</span>
  </div>
</nav>

{timeline_block}

<div class="filter-bar">
  <div class="filter-row">
    <span class="filter-label">View</span>
    <span class="chip on"  data-f="all"         style="background:#1e293b;color:#e2e8f0;border-color:#334155">All</span>
    <span class="chip off" data-f="__rel__"     style="background:#78350f22;color:#fef3c7;border-color:#78350f">🚀 Releases</span>
    <span class="chip off" data-f="__trend__"   style="background:#1e3a5f22;color:#bfdbfe;border-color:#1e3a5f">🔥 Trending</span>
    {new_today_chip}
  </div>
  <div class="filter-row">
    <span class="filter-label">Life Area</span>
    <span class="chip off" data-f="__area_work__"     style="background:#1e293b22;color:#60a5fa;border-color:#1e3a5f">💼 Work</span>
    <span class="chip off" data-f="__area_coding__"   style="background:#05291522;color:#34d399;border-color:#065f46">💻 Coding</span>
    <span class="chip off" data-f="__area_creative__" style="background:#2d124422;color:#c084fc;border-color:#7e22ce">🎨 Creative</span>
    <span class="chip off" data-f="__area_health__"   style="background:#1a042422;color:#f43f5e;border-color:#9f1239">🏥 Health</span>
    <span class="chip off" data-f="__area_education__" style="background:#1c120222;color:#fbbf24;border-color:#92400e">📚 Education</span>
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

{hero_block}

<div class="brief-outer">
  {brief_block}
  {scoreboard_block}
</div>

{warn_block}

{new_today_block}

<div id="sec-releases">{releases_block}</div>
<div id="sec-trending">{trending_block}</div>

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
  const chips    = document.querySelectorAll('.chip[data-f]');
  const allCards = Array.from(document.querySelectorAll('.card[data-src]'));
  const secRel   = document.getElementById('sec-releases');
  const secTrend = document.getElementById('sec-trending');
  const secAll   = document.getElementById('sec-all');

  function show(el) {{ if(el) el.style.display=''; }}
  function hide(el) {{ if(el) el.style.display='none'; }}
  function hasVisible(sec) {{
    return sec && [...sec.querySelectorAll('.card')].some(c=>c.style.display!=='none');
  }}

  function applyFilter(f) {{
    chips.forEach(c=>{{
      c.classList.toggle('on',  c.dataset.f===f);
      c.classList.toggle('off', c.dataset.f!==f);
    }});

    if (f==='all') {{
      show(secRel); show(secTrend); show(secAll);
      allCards.forEach(c=>c.style.display='');

    }} else if (f==='__rel__') {{
      show(secRel); hide(secTrend); hide(secAll);

    }} else if (f==='__trend__') {{
      hide(secRel); show(secTrend); hide(secAll);
      allCards.forEach(c=>{{c.style.display=c.dataset.trend==='1'?'':'none';}});
      if(!hasVisible(secTrend)) hide(secTrend);

    }} else if (f==='__new_today__') {{
      show(secRel); show(secTrend); show(secAll);
      allCards.forEach(c=>{{c.style.display=c.dataset.newtoday==='1'?'':'none';}});
      if(!hasVisible(secRel))   hide(secRel);
      if(!hasVisible(secTrend)) hide(secTrend);

    }} else if (f.startsWith('__area_')) {{
      const area = f.replace('__area_','').replace('__','');
      show(secRel); show(secTrend); show(secAll);
      allCards.forEach(c=>{{c.style.display=c.dataset.area===area?'':'none';}});
      if(!hasVisible(secRel))   hide(secRel);
      if(!hasVisible(secTrend)) hide(secTrend);

    }} else {{
      show(secRel); show(secTrend); show(secAll);
      allCards.forEach(c=>{{c.style.display=c.dataset.src===f?'':'none';}});
      if(!hasVisible(secRel))   hide(secRel);
      if(!hasVisible(secTrend)) hide(secTrend);
      const grid=document.getElementById('all-grid');
      if(grid){{
        const vis=[...grid.querySelectorAll('.card')].filter(c=>c.style.display!=='none');
        vis.sort((a,b)=>parseInt(b.dataset.ts||0)-parseInt(a.dataset.ts||0));
        vis.forEach(c=>grid.appendChild(c));
      }}
    }}
  }}

  chips.forEach(c=>c.addEventListener('click',()=>applyFilter(c.dataset.f)));

  // Share button
  document.querySelectorAll('.share-btn').forEach(btn=>{{
    btn.addEventListener('click',()=>{{
      const title = btn.dataset.title||'';
      const link  = btn.dataset.link||'';
      const sum   = btn.dataset.sum||'';
      const text  = title + (sum ? '\\n\\n'+sum : '') + (link ? '\\n'+link : '');
      navigator.clipboard.writeText(text).then(()=>{{
        btn.textContent='✓ Copied!';
        btn.classList.add('copied');
        setTimeout(()=>{{ btn.textContent='📤 Share'; btn.classList.remove('copied'); }},2000);
      }}).catch(()=>{{
        btn.textContent='Copy failed';
        setTimeout(()=>{{ btn.textContent='📤 Share'; }},2000);
      }});
    }});
  }});
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

def render_summary(item):
    s = item.get("ai_summary")
    if not s:
        return '<p class="no-summary">Summary unavailable — Ollama offline</p>'
    if item.get("is_release"):
        return _render_release(s, item)
    if item["type"] == "newsletter":
        return _render_bullets(s)
    return f'<div class="card-summary">{jargon_wrap(esc(s))}</div>'

def _render_bullets(s):
    lines = [l.strip().lstrip("•-").strip() for l in s.split("\n") if l.strip().startswith(("•", "-"))]
    if not lines:
        lines = [l.strip() for l in s.split("\n") if l.strip()][:3]
    items_html = "".join(f"<li>{jargon_wrap(esc(l))}</li>" for l in lines[:3])
    return f'<div class="card-summary"><ul>{items_html}</ul></div>'

def _render_release(s, item):
    what = who = impact_line = ""
    bullets = []
    for line in s.split("\n"):
        l = line.strip()
        u = l.upper()
        if u.startswith("WHAT:"):
            what = l[5:].strip()
        elif u.startswith("WHO:"):
            who = l[4:].strip()
        elif u.startswith("IMPACT:"):
            impact_line = l[7:].strip()
        elif l.startswith("•") or l.startswith("-"):
            bullets.append(l.lstrip("•-").strip())
    if not what and not bullets:
        return f'<div class="card-summary">{jargon_wrap(esc(s))}</div>'
    what_h   = f'<div class="rel-what">{jargon_wrap(esc(what))}</div>' if what else ""
    bul_h    = ""
    if bullets:
        bul_h = '<div class="rel-bullets">' + "".join(
            f'<div class="rel-bullet">{jargon_wrap(esc(b))}</div>' for b in bullets[:3]
        ) + "</div>"
    who_h    = f'<div class="rel-who">Best for: {esc(who)}</div>' if who else ""
    return f'<div class="card-summary">{what_h}{bul_h}{who_h}</div>'


def make_card(item, extra_class=""):
    st          = STORY_TYPE_CONFIG.get(item["story_type"], STORY_TYPE_CONFIG["general"])
    sc          = item["score"]
    is_r        = item.get("is_release", False)
    is_t        = item.get("trending", False)
    pred        = item.get("predecessor")
    order_label = item.get("release_order_label")
    area        = item.get("life_area") or ""
    is_new      = item.get("is_new_today", False)
    rev         = item.get("revolution_level", "incremental")
    hype        = item.get("hype_type", "real")
    read_time   = item.get("read_time", "")
    plain_h     = item.get("plain_headline", "").strip()
    impact      = item.get("impact", "").strip()

    # Title block: plain headline (if available) + original title as sub-label
    if plain_h and plain_h.lower() != item["title"].lower():
        title_html = (
            f'<div class="card-plain-headline">'
            f'<a href="{item["link"]}" target="_blank" rel="noopener">{esc(plain_h)}</a>'
            f'</div>'
            f'<div class="card-orig-title">{esc(item["title"])}</div>'
        )
    else:
        title_html = (
            f'<div class="card-plain-headline">'
            f'<a href="{item["link"]}" target="_blank" rel="noopener">{esc(item["title"])}</a>'
            f'</div>'
        )

    # Revolution badge
    rev_label = REV_CONFIG[rev]["label"]
    rev_cls   = f"rev-badge rev-{rev}"

    # Hype badge
    hype_label = HYPE_CONFIG[hype]["label"]
    hype_cls   = f"hype-badge hype-{hype}"

    # Life area badge
    area_badge = ""
    if area and area in AREA_CONFIG:
        ac = AREA_CONFIG[area]
        area_badge = (f'<span class="area-badge" style="color:{ac["color"]};background:{ac["color"]}11;'
                      f'border:1px solid {ac["color"]}44">{ac["emoji"]} {ac["label"]}</span>')

    # Standard badges
    order_colors = {
        "Latest Release":   ("background:#064e3b;color:#6ee7b7;border:1px solid #065f46", "🆕 Latest"),
        "Previous Release": ("background:#451a03;color:#fcd34d;border:1px solid #78350f", "⏮ Previous"),
        "Earlier Release":  ("background:#1e1b4b;color:#a5b4fc;border:1px solid #3730a3", "📅 Earlier"),
        "Archive":          ("background:#1e293b;color:#94a3b8;border:1px solid #334155", "🗂 Archive"),
    }
    type_badge  = f'<span class="badge badge-type" style="color:{st["color"]}">{st["emoji"]} {st["label"]}</span>'
    src_badge   = (f'<span class="badge" style="background:{item["color"]}22;color:{item["color"]};'
                   f'border:1px solid {item["color"]}44">via {esc(item["source"])}</span>')
    trend_badge = '<span class="badge badge-trending">🔥 Trending</span>' if is_t else ""
    new_badge   = '<span class="badge badge-new-today">🆕 New</span>' if is_new else ""
    pred_badge  = ""
    if is_r and pred:
        pred_badge = (f'<span class="badge" style="background:#78350f44;color:#fbbf24;'
                      f'border:1px solid #92400e">replaces {esc(pred[0])}</span>')
    about       = item.get("about")
    about_badge = ""
    if about:
        src_lower = item["source"].lower().replace(" ai", "").replace(" ml", "")
        if about.lower() not in src_lower:
            about_badge = (f'<span class="badge" style="background:#0f2240;color:#93c5fd;'
                           f'border:1px solid #1e40af;font-weight:800">re: {esc(about)}</span>')
    order_badge = ""
    if order_label and order_label in order_colors:
        style_str, label_text = order_colors[order_label]
        order_badge = f'<span class="badge" style="{style_str}">{label_text}</span>'

    # Before/After for releases with predecessor
    before_after_html = ""
    if is_r and pred:
        before_after_html = (
            f'<div class="before-after">'
            f'<div class="ba-col ba-old"><span class="ba-lbl">BEFORE</span>'
            f'<span class="ba-val">{esc(pred[0])}</span></div>'
            f'<span class="ba-arr">→</span>'
            f'<div class="ba-col ba-new"><span class="ba-lbl">NOW</span>'
            f'<span class="ba-val">New from {esc(pred[1])}</span></div>'
            f'</div>'
        )

    # Impact box (articles/videos)
    impact_html = ""
    if impact and not is_r:
        impact_html = f'<div class="impact-box">💡 {jargon_wrap(esc(impact))}</div>'

    # Read time + share button
    rt_html   = f'<span class="read-time">{esc(read_time)}</span>' if read_time else ""
    share_sum = (item.get("ai_summary") or "")[:200].replace('"', '').replace('\n', ' ')
    share_btn = (f'<button class="share-btn" data-title="{esc(item["title"])}" '
                 f'data-link="{esc(item["link"])}" data-sum="{esc(share_sum)}">📤 Share</button>')

    # Card class
    card_cls = "card"
    if is_r:   card_cls += " card-release"
    elif is_t: card_cls += " card-trending"
    if extra_class: card_cls += f" {extra_class}"

    summary_html = render_summary(item)
    ts = int(item["date_raw"].timestamp()) if item.get("date_raw") else 0

    return (
        f'<div class="{card_cls}" data-src="{esc(item["source"])}" '
        f'data-rel="{"1" if is_r else "0"}" data-trend="{"1" if is_t else "0"}" '
        f'data-area="{esc(area)}" data-newtoday="{"1" if is_new else "0"}" data-ts="{ts}">\n'
        f'  <div class="card-top">\n'
        f'    <div style="flex:1">{title_html}</div>\n'
        f'    <span class="card-score {score_cls(sc)}">{star_str(sc)}</span>\n'
        f'  </div>\n'
        f'  <div class="card-badges">{order_badge}{about_badge}{type_badge}'
        f'{src_badge}{trend_badge}{new_badge}{pred_badge}</div>\n'
        f'  <div class="card-badges" style="gap:4px">'
        f'<span class="{rev_cls}">{rev_label}</span>'
        f'<span class="{hype_cls}">{hype_label}</span>'
        f'{area_badge}</div>\n'
        f'  <div class="card-meta"><span>{item["date"]}</span>{rt_html}{share_btn}</div>\n'
        f'  {before_after_html}\n'
        f'  {summary_html}\n'
        f'  {impact_html}\n'
        f'</div>'
    )


# ── Build HTML ─────────────────────────────────────────────────────────────────

def build_html(items, top3, ollama_ok, date_str, archive_dir):
    releases  = [i for i in items if i.get("is_release")]
    trending  = [i for i in items if i.get("trending") and not i.get("is_release")]
    new_today = [i for i in items if i.get("is_new_today")]
    all_items = sorted(items, key=lambda x: x["score"], reverse=True)

    # ── Hero: story of the day ──
    top_item    = all_items[0] if all_items else None
    hero_block  = ""
    if top_item:
        h_title  = top_item.get("hero_title")  or top_item.get("plain_headline") or top_item["title"]
        h_why    = top_item.get("hero_why", "")
        h_action = top_item.get("hero_action", "") or top_item.get("impact", "")
        rev      = top_item.get("revolution_level", "notable")
        rc       = REV_CONFIG.get(rev, REV_CONFIG["notable"])
        st       = STORY_TYPE_CONFIG.get(top_item["story_type"], STORY_TYPE_CONFIG["general"])
        rt       = top_item.get("read_time", "")
        hero_sub_html   = f'<div class="hero-sub">{esc(h_why)}</div>' if h_why else ""
        hero_impact_html= f'<div class="hero-impact">💡 {esc(h_action)}</div>' if h_action else ""
        hero_block = (
            f'<div class="hero">\n'
            f'  <div class="hero-eyebrow">⭐ Story of the Day &nbsp;·&nbsp; '
            f'<span style="color:{rc["color"]}">{rc["label"]}</span></div>\n'
            f'  <div class="hero-title"><a href="{top_item["link"]}" target="_blank" rel="noopener">'
            f'{esc(h_title)}</a></div>\n'
            f'  {hero_sub_html}\n'
            f'  <div class="hero-meta">\n'
            f'    <span class="badge badge-type" style="color:{st["color"]}">{st["emoji"]} {st["label"]}</span>\n'
            f'    <span class="badge" style="background:{top_item["color"]}22;color:{top_item["color"]};'
            f'border:1px solid {top_item["color"]}44">via {esc(top_item["source"])}</span>\n'
            f'    <span class="read-time">{esc(rt)}</span>\n'
            f'    <span style="color:var(--muted);font-size:.73rem">{top_item["date"]}</span>\n'
            f'  </div>\n'
            f'  {hero_impact_html}\n'
            f'</div>'
        )

    # ── Morning brief ──
    brief_block = ""
    if top3:
        lines = [l.strip() for l in top3.split("\n") if l.strip()]
        paras = "".join(f"<p>{esc(l)}</p>" for l in lines)
        brief_block = (
            f'<div class="brief"><div class="brief-label">Morning Brief</div>'
            f'<div class="brief-text">{paras}</div></div>'
        )
    else:
        brief_block = (
            '<div class="brief"><div class="brief-label">Morning Brief</div>'
            '<div class="brief-text"><p style="color:var(--muted)">Start Ollama to generate your daily briefing.</p>'
            '</div></div>'
        )

    # ── Scoreboard ──
    scoreboard_block = build_scoreboard_html(items)

    # ── Ollama warning ──
    warn_block = ""
    if not ollama_ok:
        warn_block = (
            '<div class="ollama-warn"><span>⚠️</span><span>Ollama is offline — '
            'showing headlines and scores only. Run <code>ollama serve</code> '
            'then re-run this script for plain-English summaries.</span></div>'
        )

    # ── New today section ──
    new_today_block = ""
    if new_today:
        nt_sorted   = sorted(new_today, key=lambda x: x["score"], reverse=True)
        nt_cards    = "\n".join(make_card(i) for i in nt_sorted[:6])
        new_today_block = (
            f'<div id="sec-new-today">'
            f'<div class="section-head">'
            f'<span class="dot" style="background:#34d399"></span>'
            f'<h2 style="color:#34d399">New Since Yesterday</h2>'
            f'<span class="section-count">{len(new_today)} new</span>'
            f'<span class="section-divider"></span>'
            f'</div>'
            f'<div class="grid-all">{nt_cards}</div>'
            f'</div>'
        )

    # ── New Today chip ──
    new_today_count = len(new_today)
    new_today_chip  = ""
    if new_today_count:
        new_today_chip = (
            f'<span class="chip off" data-f="__new_today__" '
            f'style="background:#05291522;color:#34d399;border-color:#065f46">'
            f'🆕 New Today ({new_today_count})</span>'
        )

    # ── Timeline ──
    timeline_block = build_timeline_html(archive_dir)

    # ── Releases section ──
    releases_block = ""
    if releases:
        epoch      = datetime.min.replace(tzinfo=timezone.utc)
        sorted_rel = sorted(releases, key=lambda x: x.get("date_raw") or epoch, reverse=True)
        cards_html = "\n".join(make_card(i) for i in sorted_rel)
        releases_block = (
            f'<div class="section-head">'
            f'<span class="dot" style="background:#f59e0b"></span>'
            f'<h2 style="color:#f59e0b">What\'s New</h2>'
            f'<span class="section-count">{len(releases)} release{"s" if len(releases)!=1 else ""} detected</span>'
            f'<span class="section-divider"></span>'
            f'</div>'
            f'<div class="grid-releases">{cards_html}</div>'
        )

    # ── Trending section ──
    trending_block = ""
    if trending:
        sorted_t   = sorted(trending, key=lambda x: x["score"], reverse=True)
        cards_html = "\n".join(make_card(i) for i in sorted_t)
        src_count  = len(set(i["source"] for i in trending))
        trending_block = (
            f'<div class="section-head">'
            f'<span class="dot" style="background:#60a5fa"></span>'
            f'<h2 style="color:#60a5fa">Trending Now</h2>'
            f'<span class="section-count">covered by {src_count}+ sources</span>'
            f'<span class="section-divider"></span>'
            f'</div>'
            f'<div class="grid-trending">{cards_html}</div>'
        )

    # ── All stories ──
    all_cards = "\n".join(make_card(i) for i in all_items)

    # ── Filter chips ──
    lab_chips = news_chips = creator_chips = x_chips = ""
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

    return HTML.format(
        date=date_str,
        count=len(items),
        sources=len(seen),
        releases=len(releases),
        trending_count=len(trending),
        new_today_count=new_today_count,
        brief_block=brief_block,
        scoreboard_block=scoreboard_block,
        warn_block=warn_block,
        hero_block=hero_block,
        timeline_block=timeline_block,
        new_today_chip=new_today_chip,
        new_today_block=new_today_block,
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
