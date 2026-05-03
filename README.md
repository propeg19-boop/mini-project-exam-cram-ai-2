# ExamCram AI — Backend

> Deterministic exam strategy engine. Drop your syllabus. Get a survival plan.

---

## Stack

- **Flask** — lightweight API server
- **Google Gemini** (via `google-generativeai`) — AI engine
- **SerpAPI** — diagram image fetching
- **In-memory sessions** — zero external dependencies for storage

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

### 3. Run

```bash
python app.py
```

Server starts on `http://localhost:5000`

---

## API Reference

### `POST /start-analysis`

Full pipeline: input → clean → detect → classify → plan → session.

**Request:**
```json
{
  "content": "raw syllabus or question bank text",
  "days": 3,
  "level": "standard",
  "tone": "locked-in"
}
```

**Response:**
```json
{
  "session_id": "uuid",
  "meta": {
    "input_type": "syllabus | question_bank",
    "subject": "Operating Systems",
    "total_questions": 18,
    "readiness_score": 12
  },
  "matrix": {
    "critical": [{ "question": "...", "priority": "critical", "reason": "...", "estimated_time": "20 min" }],
    "important": [...],
    "skip": [...]
  },
  "plan": {
    "day_1": ["question1", "question2"],
    "day_2": [...]
  }
}
```

---

### `POST /generate-answer`

Generate a study answer in one of three modes.

**Request:**
```json
{
  "session_id": "uuid",
  "topic": "Process Scheduling Algorithms",
  "mode": "focused | revision | exam"
}
```

**Response:**
```json
{
  "concept": "Core explanation...",
  "answer": "• Bullet 1\n• Bullet 2...",
  "mnemonic": "Remember it as...",
  "diagram_query": "process scheduling diagram labeled"
}
```

---

### `POST /get-diagrams`

Fetch 3 diagram image URLs.

**Request:**
```json
{ "query": "process scheduling diagram labeled" }
```

**Response:**
```json
{ "images": ["url1", "url2", "url3"] }
```

---

### `POST /mark-complete`

Mark a topic done and update progress/rank.

**Request:**
```json
{
  "session_id": "uuid",
  "topic": "Process Scheduling Algorithms"
}
```

**Response:**
```json
{
  "progress_score": 45,
  "rank": "Getting There",
  "message": "Critical topic cleared. Big W."
}
```

---

## Architecture

```
app.py                      ← Flask routes + orchestration
utils/
  ai_client.py              ← Model fallback chain (Gemini)
  input_processor.py        ← Clean + detect input type
  question_generator.py     ← Syllabus → question bank
  priority_engine.py        ← AI classification + matrix + plan
  answer_engine.py          ← Focused / Revision / Exam answers
  diagram_engine.py         ← SerpAPI image fetch
  session_manager.py        ← In-memory session + XP + rank
```

## AI Model Fallback Chain

Models are tried in order. Auto-switches on failure:

1. `gemini-2.0-flash-lite` (fastest, cheapest)
2. `gemini-2.5-flash-lite-preview-06-17`
3. `gemini-2.5-flash`
4. `gemini-2.0-flash`
5. `gemma-3-27b-it`

---

## Rank System

| Score | Rank |
|-------|------|
| 0–20  | Unprepared |
| 20–40 | Surviving |
| 40–60 | Getting There |
| 60–80 | Exam Ready |
| 80–100 | Topper Mode |

## XP Weights

| Priority | XP |
|----------|-----|
| Critical | +5 |
| Important | +3 |
| Skip | +1 |
