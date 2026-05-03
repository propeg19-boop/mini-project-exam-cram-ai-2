"""
Priority Engine — classifies questions as critical / important / skip
and generates a day-wise study plan.
AI-driven with fallback logic.
"""

import math
from utils.ai_client import call_ai_json

# ─── Priority Classification ──────────────────────────────

def classify_priorities(questions: list[str], level: str = "standard") -> list[dict]:
    """
    For each question, returns:
    { question, priority, reason, estimated_time }
    Uses AI; falls back to rule-based.
    """
    try:
        return _ai_classify(questions, level)
    except Exception:
        return _rule_classify(questions)


def _ai_classify(questions: list[str], level: str) -> list[dict]:
    level_bias = {
        "survival": "Be aggressive — most things should be 'skip', only truly high-frequency topics are 'critical'.",
        "standard": "Balance coverage — split roughly 40% critical, 40% important, 20% skip.",
        "topper":   "Almost everything matters — most should be 'critical' or 'important', rarely 'skip'.",
    }
    bias = level_bias.get(level, level_bias["standard"])

    questions_str = "\n".join(f"{i+1}. {q}" for i, q in enumerate(questions))

    prompt = f"""You are an expert exam strategy advisor for university students.

Classify each question by exam priority. {bias}

Priority definitions:
- "critical": High exam frequency, high marks, core concept — MUST study
- "important": Medium frequency, useful but not essential — SHOULD study
- "skip": Rarely tested, low marks, edge cases — can skim or ignore

For each question, also estimate study time needed.

Questions:
{questions_str}

Return a JSON array. Each element must be:
{{
  "question": "exact question text",
  "priority": "critical" | "important" | "skip",
  "reason": "one sentence why",
  "estimated_time": "e.g. 15 min"
}}

Return ONLY the JSON array."""

    result = call_ai_json(prompt, max_tokens=4000)

    if isinstance(result, list):
        validated = []
        for item in result:
            if isinstance(item, dict) and "question" in item:
                validated.append({
                    "question": str(item.get("question", "")),
                    "priority": _validate_priority(item.get("priority", "important")),
                    "reason": str(item.get("reason", "Exam relevance")),
                    "estimated_time": str(item.get("estimated_time", "20 min")),
                })
        if validated:
            return validated

    return _rule_classify(questions)


def _rule_classify(questions: list[str]) -> list[dict]:
    """
    Fallback: heuristic classification based on keywords.
    ~40% critical, ~40% important, ~20% skip.
    """
    critical_keywords = [
        "algorithm", "deadlock", "process", "memory", "virtual",
        "scheduling", "interrupt", "paging", "semaphore", "mutex",
        "define", "explain", "describe", "difference", "compare",
    ]
    skip_keywords = ["history", "introduction", "overview", "origin", "background"]

    classified = []
    for i, q in enumerate(questions):
        lower = q.lower()

        if any(k in lower for k in skip_keywords):
            priority = "skip"
        elif any(k in lower for k in critical_keywords):
            priority = "critical"
        elif i % 5 == 4:  # every 5th question → skip
            priority = "skip"
        elif i % 3 == 0:
            priority = "critical"
        else:
            priority = "important"

        classified.append({
            "question": q,
            "priority": priority,
            "reason": "Classified by keyword analysis.",
            "estimated_time": "20 min",
        })

    return classified


def _validate_priority(value: str) -> str:
    valid = {"critical", "important", "skip"}
    v = str(value).lower().strip()
    return v if v in valid else "important"


# ─── Priority Matrix Builder ──────────────────────────────

def build_matrix(classified: list[dict]) -> dict:
    """
    Returns:
    { "critical": [...], "important": [...], "skip": [...] }
    Each item retains full classification dict.
    """
    matrix = {"critical": [], "important": [], "skip": []}
    for item in classified:
        p = item.get("priority", "important")
        matrix.setdefault(p, []).append(item)
    return matrix


# ─── Study Plan Generator ─────────────────────────────────

def generate_study_plan(matrix: dict, days: int) -> dict:
    """
    Distributes questions across days.
    CRITICAL topics come first; balanced daily workload.
    Returns: { "day_1": [...], "day_2": [...] }
    """
    days = max(1, days)

    # Order: critical → important → skip
    ordered = (
        matrix.get("critical", []) +
        matrix.get("important", []) +
        matrix.get("skip", [])
    )

    total = len(ordered)
    per_day = math.ceil(total / days)

    plan = {}
    for day in range(1, days + 1):
        start = (day - 1) * per_day
        end = start + per_day
        slice_ = ordered[start:end]
        if slice_:
            plan[f"day_{day}"] = [item["question"] for item in slice_]

    # If days > questions, some days may be empty — that's fine
    return plan


# ─── Subject Detection ────────────────────────────────────

def detect_subject(questions: list[str]) -> str:
    """Infer the academic subject from question keywords."""
    try:
        return _ai_detect_subject(questions)
    except Exception:
        return _rule_detect_subject(questions)


def _ai_detect_subject(questions: list[str]) -> str:
    sample = "\n".join(questions[:10])
    prompt = f"""You are an academic subject classifier.
Given these exam questions, identify the single most likely academic subject.
Respond with ONLY the subject name (e.g. "Operating Systems", "Data Structures", "Thermodynamics").
No explanation.

Questions:
{sample}"""

    from utils.ai_client import call_ai
    result = call_ai(prompt, max_tokens=20)
    return result.strip()


def _rule_detect_subject(questions: list[str]) -> str:
    combined = " ".join(questions).lower()

    subjects = {
        "Operating Systems": ["process", "deadlock", "paging", "scheduling", "semaphore", "virtual memory"],
        "Data Structures": ["array", "linked list", "stack", "queue", "tree", "graph", "sorting"],
        "Database Systems": ["sql", "normalization", "transaction", "acid", "schema", "query"],
        "Computer Networks": ["tcp", "ip", "routing", "protocol", "network", "bandwidth"],
        "Thermodynamics": ["entropy", "heat", "temperature", "carnot", "pressure"],
        "Mathematics": ["integral", "derivative", "matrix", "vector", "probability"],
        "Economics": ["demand", "supply", "gdp", "inflation", "market"],
    }

    best = ("General Studies", 0)
    for subject, keywords in subjects.items():
        score = sum(1 for k in keywords if k in combined)
        if score > best[1]:
            best = (subject, score)

    return best[0]


# ─── Initial Readiness Score ──────────────────────────────

def compute_initial_readiness(matrix: dict, days: int) -> int:
    """
    Rough estimate before any studying happens.
    More days + fewer critical topics = higher starting readiness.
    Range: 5–25 (always shows room to grow).
    """
    total = sum(len(v) for v in matrix.values())
    critical_count = len(matrix.get("critical", []))

    if total == 0:
        return 10

    ratio = 1 - (critical_count / total)
    day_factor = min(days / 7, 1.0)

    score = int(5 + (ratio * 10) + (day_factor * 10))
    return min(score, 25)
