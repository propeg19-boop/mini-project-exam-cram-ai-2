# ExamCram AI v2 — Gemini + SerpAPI Edition

A modular Flask backend for generating study plans and AI-powered answers.

---

## Project Structure

```
examcram_v2/
├── app.py                  ← All Flask routes
├── .env                    ← Your API keys (never commit this)
├── requirements.txt
└── utils/
    ├── __init__.py
    ├── priority.py         ← Study plan logic (pure Python, no API)
    ├── ai_handler.py       ← Gemini AI with 4-model fallback chain
    └── image_fetcher.py    ← SerpAPI Google Images fetcher
```

---

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Add your API keys to .env
#    GEMINI_API_KEY  → https://aistudio.google.com/app/apikey  (free)
#    SERPAPI_KEY     → https://serpapi.com                      (100 free/month)

# 3. Run the server
python app.py
# → http://localhost:5000
```

---

## API Reference

### POST /generate-plan

**Request:**
```json
{
  "questions": "Define osmosis\nExplain Newton's laws\nAnalyze climate change",
  "days": 3,
  "level": "intermediate",
  "tone": "formal"
}
```

**Response:**
```json
{
  "table": [
    { "question": "Define osmosis", "priority": "High", "estimated_time": "10–15 mins" },
    { "question": "Explain Newton's laws", "priority": "Medium", "estimated_time": "20–30 mins" },
    { "question": "Analyze climate change", "priority": "Low", "estimated_time": "40–60 mins" }
  ],
  "day_plan": {
    "Day 1": ["Define osmosis"],
    "Day 2": ["Explain Newton's laws"],
    "Day 3": ["Analyze climate change"]
  },
  "meta": { "total_questions": 3, "days": 3, "level": "intermediate", "tone": "formal" }
}
```

---

### POST /generate-answer

**Request:**
```json
{
  "question": "Explain Newton's second law",
  "mode": "focused",
  "level": "beginner",
  "tone": "casual"
}
```

**Response:**
```json
{
  "analogy": "Pushing a shopping cart — harder push = faster cart.",
  "understanding": "Force equals mass times acceleration (F=ma).",
  "answer": "Newton's second law states...",
  "extra": "Common mistake: forgetting force and acceleration are vectors."
}
```

`mode` options: `"focused"` (detailed) or `"quick"` (bullet points)

---

### POST /get-images

**Request:**
```json
{ "topic": "mitosis cell division" }
```

**Response:**
```json
{
  "images": [
    "https://...",
    "https://...",
    "https://..."
  ]
}
```

---

## Gemini Fallback Chain

| Order | Model | Notes |
|-------|-------|-------|
| 1 | `gemini-2.0-flash-lite` | Fastest, lowest cost |
| 2 | `gemma-3-27b-it` | Open model backup |
| 3 | `gemini-1.5-flash` | Reliable general model |
| 4 | `gemini-1.5-flash-8b` | Last resort |

If ALL models fail, the app still returns valid JSON (never crashes).

---

## Priority Logic (for viva)

| Keyword in question | Priority | Time |
|---------------------|----------|------|
| define, list, state | High | 10–15 mins |
| explain, describe | Medium | 20–30 mins |
| analyze, compare, derive | Low | 40–60 mins |

Defaults to Medium if no keyword matched.
