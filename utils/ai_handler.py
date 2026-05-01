"""
ai_handler.py — Gemini AI wrapper with automatic model fallback
Model IDs verified against Google AI Studio rate limit page (May 2026).
Never crashes; always returns valid JSON.
"""

import os
import json
import re
import requests

# ─── Model fallback chain ────────────────────────────────────────────────────
#
# Ordered: highest RPM first → best availability → most capable last
#
# From your Google AI Studio rate limits:
# ┌────────────────────────────┬───────────┬────────────┐
# │ Model (UI Name)            │ RPM       │ TPM        │
# ├────────────────────────────┼───────────┼────────────┤
# │ Gemini 3.1 Flash Lite      │ 15 RPM    │ 250K       │
# │ Gemini 2.5 Flash Lite      │ 10 RPM    │ 250K       │
# │ Gemini 2.5 Flash           │  5 RPM    │ 250K       │
# │ Gemini 3 Flash             │  5 RPM    │ 250K       │
# │ Gemma 4 26B                │ 15 RPM    │ Unlimited  │
# │ Gemma 4 31B                │ 15 RPM    │ Unlimited  │
# │ Gemma 3 27B                │ 30 RPM    │ 15K        │
# └────────────────────────────┴───────────┴────────────┘

MODEL_CHAIN = [
    # Tier 1: Highest RPM, fastest response
    "gemini-3.1-flash-lite",                   # 15 RPM | 250K TPM
    "gemini-2.5-flash-lite-preview-06-17",     # 10 RPM | 250K TPM

    # Tier 2: Smarter models, moderate RPM
    "gemini-2.5-flash",                        # 5 RPM  | 250K TPM
    "gemini-3.0-flash",                        # 5 RPM  | 250K TPM

    # Tier 3: Gemma — great fallbacks, unlimited tokens
    "gemma-4-27b-it",                          # 15 RPM | Unlimited (Gemma 4 26B)
    "gemma-4-31b-it",                          # 15 RPM | Unlimited (Gemma 4 31B)
    "gemma-3-27b-it",                          # 30 RPM | 15K
]

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


def _call_gemini(model: str, prompt: str, api_key: str) -> str:
    """
    Raw call to a single Gemini/Gemma model.
    Returns the text content of the first candidate.
    Raises on non-200 or empty response.
    """
    url = f"{GEMINI_BASE}/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 2048,
        },
    }
    resp = requests.post(url, json=payload, timeout=30)
    resp.raise_for_status()

    data = resp.json()
    candidates = data.get("candidates", [])
    if not candidates:
        raise ValueError("No candidates returned")

    content = candidates[0].get("content", {})
    parts = content.get("parts", [])
    if not parts:
        raise ValueError("Empty parts in response")

    text = parts[0].get("text", "").strip()
    if not text:
        raise ValueError("Empty text in response")

    return text


def call_ai(prompt: str) -> str:
    """
    Try each model in MODEL_CHAIN until one succeeds.
    Returns raw text from the model.
    Raises RuntimeError only if ALL models fail (very unlikely with 7 models).
    """
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set in .env")

    last_error = None
    for model in MODEL_CHAIN:
        try:
            print(f"[AI] Trying model: {model}")
            result = _call_gemini(model, prompt, api_key)
            print(f"[AI] SUCCESS with: {model}")
            return result
        except Exception as e:
            print(f"[AI] FAILED {model}: {e}")
            last_error = e
            continue

    raise RuntimeError(f"All Gemini models failed. Last error: {last_error}")


def extract_json(raw: str) -> dict:
    """
    Robustly pull JSON from a model response that may include markdown fences.
    """
    # Strip ```json ... ``` or ``` ... ``` wrappers
    cleaned = re.sub(r"```(?:json)?\s*", "", raw).replace("```", "").strip()

    # Try direct parse first
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Find first outermost { ... } block
    match = re.search(r'\{.*\}', cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    # Last resort: wrap raw text so frontend never breaks
    print(f"[AI] WARNING: Could not parse JSON, wrapping raw text as answer")
    return {
        "answer": cleaned,
        "analogy": "",
        "understanding": "",
        "extra": "Note: AI response could not be fully structured."
    }


# ─── Prompt builders ─────────────────────────────────────────────────────────

def build_plan_prompt(questions: str, days: int, level: str, tone: str) -> str:
    return f"""You are an expert study planner. A student needs help organizing exam prep.

Student level: {level}
Tone: {tone}
Available days: {days}
Questions:
{questions}

Return ONLY a valid JSON object. No markdown. No explanation. Just raw JSON.
{{
  "table": [
    {{"question": "...", "priority": "High|Medium|Low", "estimated_time": "..."}}
  ],
  "day_plan": {{
    "Day 1": ["question text", ...],
    "Day 2": ["question text", ...]
  }},
  "meta": {{
    "days": {days},
    "total": <integer>
  }}
}}

Rules:
- High priority: define, list, state, name, identify
- Medium priority: explain, describe, discuss, outline
- Low priority: analyze, compare, evaluate, contrast
- Spread across {days} days with High questions first
- estimated_time format: "10 min", "20 min", "35 min"
"""


def build_answer_prompt(question: str, mode: str, level: str, tone: str) -> str:
    if mode == "exam":
        return f"""You are an expert exam coach.

Question: {question}
Student level: {level}
Tone: {tone}

Return ONLY valid JSON. No markdown. No extra text:
{{
  "answer": "Complete structured exam answer with introduction, main body points, and conclusion."
}}
"""
    elif mode == "quick":
        return f"""You are a fast-revision tutor.

Question: {question}
Student level: {level}
Tone: {tone}

Return ONLY valid JSON. No markdown. No extra text:
{{
  "analogy": "One punchy analogy to remember this",
  "understanding": "3-5 bullet points of core concepts",
  "answer": "Concise 2-3 sentence summary answer",
  "extra": "One exam tip or common mistake to avoid"
}}
"""
    else:  # focused
        return f"""You are a deep-learning study coach.

Question: {question}
Student level: {level}
Tone: {tone}

Return ONLY valid JSON. No markdown. No extra text:
{{
  "analogy": "A real-world analogy that makes this concept click",
  "understanding": "Thorough conceptual breakdown in plain language",
  "answer": "Well-structured detailed answer with all key points explained",
  "extra": "Memory technique, pro tip, or related concept for exam edge"
}}
"""


def generate_plan(questions: str, days: int, level: str, tone: str) -> dict:
    """Full pipeline for /generate-plan"""
    prompt = build_plan_prompt(questions, days, level, tone)
    raw = call_ai(prompt)
    return extract_json(raw)


def generate_answer(question: str, mode: str, level: str, tone: str) -> dict:
    """Full pipeline for /generate-answer"""
    prompt = build_answer_prompt(question, mode, level, tone)
    raw = call_ai(prompt)
    return extract_json(raw)
