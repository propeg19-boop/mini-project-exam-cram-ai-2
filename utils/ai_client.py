"""
AI Client — implements the fallback model chain.
Tries each model in order; switches on failure automatically.
All calls go through call_ai() and call_ai_json().
"""

import json
import re
import time
import os
import requests

# ─── Model Fallback Chain (in priority order) ──────────────
MODELS = [
    "gemini-2.0-flash-lite",
    "gemini-2.5-flash-lite-preview-06-17",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
]

# Timeout per attempt (seconds)
REQUEST_TIMEOUT = 25

_api_key = os.environ.get("GEMINI_API_KEY", "")

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


# ─── Core Caller (pure requests — no SDK dependency) ───────

def call_ai(prompt: str, max_tokens: int = 1000, system: str = "") -> str:
    """
    Attempt each model in MODELS order via REST API.
    No google SDK required — works on any host.
    Raises RuntimeError if all models fail.
    """
    if not _api_key:
        raise RuntimeError("GEMINI_API_KEY not set.")

    last_err = None
    contents = []

    if system:
        contents.append({"role": "user", "parts": [{"text": system}]})
        contents.append({"role": "model", "parts": [{"text": "Understood."}]})

    contents.append({"role": "user", "parts": [{"text": prompt}]})

    payload = {
        "contents": contents,
        "generationConfig": {
            "maxOutputTokens": max_tokens,
            "temperature": 0.4,
        },
    }

    for model_name in MODELS:
        try:
            url = GEMINI_URL.format(model=model_name)
            resp = requests.post(
                url,
                params={"key": _api_key},
                json=payload,
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return text.strip()
        except Exception as e:
            last_err = e
            time.sleep(0.3)
            continue

    raise RuntimeError(f"All AI models failed. Last error: {last_err}")


def call_ai_json(prompt: str, max_tokens: int = 2000, system: str = "") -> dict | list:
    """
    Same as call_ai but:
    - Instructs the model to return only valid JSON
    - Strips markdown fences
    - Parses and returns Python object
    Raises ValueError if JSON cannot be parsed after all retries.
    """
    json_system = (
        (system + "\n\n" if system else "") +
        "IMPORTANT: Respond ONLY with valid JSON. No markdown, no backticks, no explanation. Raw JSON only."
    )

    raw = call_ai(prompt, max_tokens=max_tokens, system=json_system)

    # Strip markdown fences if present
    cleaned = re.sub(r"```(?:json)?|```", "", raw).strip()

    # Try to extract JSON object/array if surrounded by extra text
    match = re.search(r'(\[.*\]|\{.*\})', cleaned, re.DOTALL)
    if match:
        cleaned = match.group(1)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(f"AI returned invalid JSON: {e}\nRaw: {raw[:300]}")
