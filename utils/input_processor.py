"""
Input Processor — cleans raw text and detects whether it's a
question_bank or a syllabus, using AI with a rule-based fallback.
"""

import re
from utils.ai_client import call_ai

# ─── Cleaning ──────────────────────────────────────────────

def clean_input(raw: str) -> str:
    """Normalize whitespace, remove junk chars, return clean lines."""
    text = raw.strip()
    text = re.sub(r'\r\n|\r', '\n', text)          # normalize line endings
    text = re.sub(r'[ \t]+', ' ', text)             # collapse spaces/tabs
    text = re.sub(r'\n{3,}', '\n\n', text)          # max 2 blank lines
    text = re.sub(r'[^\x20-\x7E\n]', '', text)      # strip non-ASCII
    return text.strip()


def split_into_topics(text: str) -> list[str]:
    """Split cleaned text into individual topic/question lines."""
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    # Filter out very short noise lines (< 5 chars)
    return [l for l in lines if len(l) >= 5]


# ─── Input Type Detection ──────────────────────────────────

QUESTION_VERBS = [
    "what", "why", "how", "explain", "define", "describe",
    "list", "compare", "differentiate", "state", "write",
    "discuss", "evaluate", "analyze", "give", "mention",
    "?",
]

def detect_input_type(text: str) -> str:
    """
    Returns 'question_bank' or 'syllabus'.
    Uses AI first; falls back to rule-based detection.
    """
    try:
        return _ai_detect(text)
    except Exception:
        return _rule_detect(text)


def _ai_detect(text: str) -> str:
    prompt = f"""You are an exam content classifier. Given the following academic text, 
classify it as EXACTLY one of:
- "question_bank"  — if it contains exam-style questions (with ?, imperative verbs like Explain/Define/List)
- "syllabus"       — if it contains topic names, unit headings, or course outlines

Respond with ONLY the classification word, nothing else.

TEXT:
{text[:2000]}"""

    result = call_ai(prompt, max_tokens=10)
    result = result.strip().lower().replace('"', '').replace("'", "")
    if result in ("question_bank", "syllabus"):
        return result
    # If AI returned something unexpected, use rule fallback
    return _rule_detect(text)


def _rule_detect(text: str) -> str:
    """Rule-based fallback: if verb patterns found → question_bank, else syllabus."""
    lower = text.lower()
    verb_count = sum(1 for v in QUESTION_VERBS if v in lower)
    total_lines = len([l for l in text.split('\n') if l.strip()])
    # If more than 30% of content matches question verbs, treat as question_bank
    if verb_count >= max(2, total_lines * 0.3):
        return "question_bank"
    return "syllabus"
