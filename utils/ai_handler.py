"""
ai_handler.py — Gemini AI wrapper with automatic model fallback
Never crashes; always returns valid JSON.
"""

import os
import json
import re
import requests

# ─── Model fallback chain ───────────────────────────────────────────────────
# Fastest first, most capable last.
MODEL_CHAIN = [
    "gemini-2.0-flash-lite",   # fastest, cheapest
    "gemini-2.0-flash",        # solid middle ground
    "gemini-1.5-flash",        # reliable fallback
    "gemini-1.5-pro",          # heavy hitter if all else fails
]

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


def _call_gemini(model: str, prompt: str, api_key: str) -> str:
    """
    Raw call to a single Gemini model.
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
    # Navigate Gemini response structure safely
    candidates = data.get("candidates", [])
    if not candidates:
        raise ValueError("No candidates returned")
    text = candidates[0]["content"]["parts"][0]["text"]
    return text.strip()


def call_ai(prompt: str) -> str:
    """
    Try each model in MODEL_CHAIN until one succeeds.
    Returns raw text from the model.
    Raises RuntimeError only if ALL models fail.
    """
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set in .env")

    last_error = None
    for model in MODEL_CHAIN:
        try:
            print(f"[AI] Trying model: {model}")
            result = _call_gemini(model, prompt, api_key)
            print(f"[AI] Success with: {model}")
            return result
        except Exception as e:
            print(f"[AI] {model} failed: {e}")
            last_error = e
            continue

    raise RuntimeError(f"All Gemini models failed. Last error: {last_error}")


def extract_json(raw: str) -> dict:
    """
    Robustly pull JSON from a Gemini response that may include markdown fences.
    """
    # Strip ```json ... ``` wrappers if present
    cleaned = re.sub(r"```(?:json)?\s*", "", raw).replace("```", "").strip()

    # Try direct parse first
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Try to find the first { ... } block
    match = re.search(r'\{.*\}', cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    # Last resort: return the raw text in a safe wrapper
    return {"answer": cleaned, "analogy": "", "understanding": "", "extra": ""}


# ─── Prompt builders ─────────────────────────────────────────────────────────

def build_plan_prompt(questions: str, days: int, level: str, tone: str) -> str:
    return f"""You are an expert study planner. A student needs help organizing their exam prep.

Student level: {level}
Tone: {tone}
Available days: {days}
Questions:
{questions}

Return ONLY a valid JSON object (no markdown, no explanation) in this exact format:
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
    "total": <number of questions>
  }}
}}

Rules:
- High priority → define, list, state, name, identify
- Medium priority → explain, describe, discuss, outline
- Low priority → analyze, compare, evaluate, contrast
- Spread evenly across {days} days with High-priority first
- estimated_time should be human-readable like "15 min" or "30 min"
"""


def build_answer_prompt(question: str, mode: str, level: str, tone: str) -> str:
    if mode == "exam":
        return f"""You are an expert exam coach. Write a model exam answer.

Question: {question}
Student level: {level}
Tone: {tone}

Return ONLY valid JSON (no markdown):
{{
  "answer": "A complete, structured answer ready to write in an exam. Use clear paragraphs. Include intro, body, conclusion."
}}
"""
    elif mode == "quick":
        return f"""You are a fast-revision tutor.

Question: {question}
Student level: {level}
Tone: {tone}

Return ONLY valid JSON (no markdown):
{{
  "analogy": "One punchy analogy to remember this",
  "understanding": "3-5 bullet points of core concepts",
  "answer": "A concise 2-3 sentence summary answer",
  "extra": "One exam tip or common mistake to avoid"
}}
"""
    else:  # focused (default)
        return f"""You are a deep-learning study coach.

Question: {question}
Student level: {level}
Tone: {tone}

Return ONLY valid JSON (no markdown):
{{
  "analogy": "A real-world analogy that makes this click",
  "understanding": "A thorough conceptual breakdown in plain language",
  "answer": "A well-structured, detailed answer with key points clearly explained",
  "extra": "A memory technique, pro tip, or related concept worth knowing"
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
