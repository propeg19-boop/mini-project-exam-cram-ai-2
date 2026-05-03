"""
Question Generator — converts syllabus topics into exam-style questions.
Uses AI with a rule-based fallback.
Constraints: 1–3 questions per topic, max 25 total, no duplicates.
"""

from utils.ai_client import call_ai_json
import json

MAX_QUESTIONS = 25
QUESTION_STARTERS = [
    "Define", "Explain", "List", "Compare",
    "Describe", "What is", "How does", "Differentiate between",
    "State the", "Discuss",
]

# ─── Main Entry ───────────────────────────────────────────

def generate_questions(topics: list[str], level: str = "standard") -> list[str]:
    """
    Given a list of syllabus topics, returns exam-style questions.
    Falls back to rule-based if AI fails.
    """
    try:
        return _ai_generate(topics, level)
    except Exception:
        return _rule_generate(topics)


# ─── AI Generation ────────────────────────────────────────

def _ai_generate(topics: list[str], level: str) -> list[str]:
    level_instructions = {
        "survival": "1 question per topic, focused on core definitions only.",
        "standard": "1–2 questions per topic, mix of definitions and applications.",
        "topper":   "2–3 questions per topic, include analysis, comparison, and edge cases.",
    }
    instruction = level_instructions.get(level, level_instructions["standard"])

    topics_str = "\n".join(f"- {t}" for t in topics[:30])  # cap input

    prompt = f"""You are an exam question generator for university-level exams.

Convert these syllabus topics into exam-style questions.
{instruction}
Rules:
- Use verbs like: Define, Explain, List, Compare, Describe, Discuss, Differentiate
- Maximum {MAX_QUESTIONS} questions total
- No duplicate questions
- Return a JSON array of strings, each string is one question

TOPICS:
{topics_str}

Return ONLY a JSON array like: ["question1", "question2", ...]"""

    result = call_ai_json(prompt, max_tokens=2000)

    if isinstance(result, list):
        questions = [str(q).strip() for q in result if q]
        # Deduplicate
        seen = set()
        unique = []
        for q in questions:
            key = q.lower()[:60]
            if key not in seen:
                seen.add(key)
                unique.append(q)
        return unique[:MAX_QUESTIONS]

    return _rule_generate(topics)


# ─── Rule-Based Fallback ──────────────────────────────────

def _rule_generate(topics: list[str]) -> list[str]:
    """Simple template-based question generation."""
    questions = []
    for topic in topics:
        if len(questions) >= MAX_QUESTIONS:
            break
        topic = topic.strip().rstrip('.')
        questions.append(f"Define and explain {topic}.")
        if len(questions) < MAX_QUESTIONS:
            questions.append(f"List the key characteristics of {topic}.")

    # Deduplicate
    seen = set()
    unique = []
    for q in questions:
        k = q.lower()[:60]
        if k not in seen:
            seen.add(k)
            unique.append(q)

    return unique[:MAX_QUESTIONS]
