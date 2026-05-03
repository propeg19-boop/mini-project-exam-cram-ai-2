"""
AI Client — implements the fallback model chain.
Tries each model in order; switches on failure automatically.
All calls go through call_ai() and call_ai_json().
"""

import json
import re
import time
import google.generativeai as genai
import os

# ─── Model Fallback Chain (in priority order) ──────────────
MODELS = [
    "gemini-2.0-flash-lite",
    "gemini-2.5-flash-lite-preview-06-17",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemma-3-27b-it",
]

# Timeout per attempt (seconds)
REQUEST_TIMEOUT = 20

# ─── Configure Gemini SDK ──────────────────────────────────
_api_key = os.environ.get("GEMINI_API_KEY", "")
if _api_key:
    genai.configure(api_key=_api_key)


# ─── Core Caller ──────────────────────────────────────────

def call_ai(prompt: str, max_tokens: int = 1000, system: str = "") -> str:
    """
    Attempt each model in MODELS order.
    Returns the first successful text response.
    Raises RuntimeError if all models fail.
    """
    last_err = None
    full_prompt = f"{system}\n\n{prompt}" if system else prompt

    for model_name in MODELS:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=max_tokens,
                    temperature=0.4,
                ),
                request_options={"timeout": REQUEST_TIMEOUT},
            )
            return response.text.strip()
        except Exception as e:
            last_err = e
            # Small backoff before next attempt
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
