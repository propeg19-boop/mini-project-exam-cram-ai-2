"""
Answer Engine — generates answers in three modes:
  focused  → concept + bullets + mnemonic
  revision → bullets only
  exam     → strict exam format

Caches per session to avoid redundant AI calls.
"""

from utils.ai_client import call_ai_json, call_ai


# ─── Mode Prompts ─────────────────────────────────────────

def _focused_prompt(topic: str, level: str) -> str:
    return f"""You are an expert exam tutor. A student needs to understand this exam topic deeply.

Topic: {topic}
Level: {level}

Return a JSON object with EXACTLY these keys:
{{
  "concept": "2–3 sentence clear explanation of the core concept",
  "answer": "5–7 bullet points covering the complete answer for an exam",
  "mnemonic": "A memorable acronym, rhyme, or visual hook to remember this topic",
  "diagram_query": "3–5 word image search query to find a helpful diagram for this topic"
}}

Make it exam-ready. Be specific, not vague."""


def _revision_prompt(topic: str) -> str:
    return f"""You are an exam tutor helping a student do a rapid revision pass.

Topic: {topic}

Return a JSON object:
{{
  "concept": "One sentence summary",
  "answer": "3–4 ultra-concise bullet points — key facts only",
  "mnemonic": "Quick memory hook",
  "diagram_query": "3–5 word image search query"
}}"""


def _exam_prompt(topic: str) -> str:
    return f"""You are writing a model exam answer for a university exam.

Question/Topic: {topic}

Write a complete, marks-worthy exam answer.
Return a JSON object:
{{
  "concept": "Introduction paragraph (2–3 sentences)",
  "answer": "Full structured answer with numbered points, definitions, and examples — as you would write in an exam",
  "mnemonic": "Quick recall trigger for exam hall",
  "diagram_query": "3–5 word image search query for a relevant diagram"
}}

Use formal academic language. Aim for 80–120 words in the answer field."""


# ─── Main Entry ──────────────────────────────────────────

def generate_answer(topic: str, mode: str = "focused", level: str = "standard") -> dict:
    """
    Generate an answer for a topic in the given mode.
    Returns: { concept, answer, mnemonic, diagram_query }
    """
    mode = mode.lower().strip()

    prompt_map = {
        "focused":  _focused_prompt(topic, level),
        "revision": _revision_prompt(topic),
        "exam":     _exam_prompt(topic),
    }

    prompt = prompt_map.get(mode, prompt_map["focused"])

    try:
        result = call_ai_json(prompt, max_tokens=1500)
        if isinstance(result, dict):
            return _validate_answer(result, topic)
    except Exception:
        pass

    # Fallback: plain text answer
    return _fallback_answer(topic, mode)


def _validate_answer(data: dict, topic: str) -> dict:
    """Ensure all required keys exist."""
    return {
        "concept":       str(data.get("concept", f"Core concept of {topic}.")),
        "answer":        str(data.get("answer", f"• {topic} is an important exam topic.\n• Study core definitions and applications.")),
        "mnemonic":      str(data.get("mnemonic", f"Remember: {topic[:20]}...")),
        "diagram_query": str(data.get("diagram_query", f"{topic} diagram")),
    }


def _fallback_answer(topic: str, mode: str) -> dict:
    """Minimal fallback when AI is completely unavailable."""
    if mode == "revision":
        answer = f"• Definition: Core meaning of {topic}\n• Key property 1\n• Key property 2\n• Application"
    elif mode == "exam":
        answer = (
            f"{topic} is a fundamental concept in this subject. "
            f"It involves [key mechanism]. "
            f"Key points include: (1) definition, (2) working principle, (3) advantages/disadvantages."
        )
    else:
        answer = (
            f"• Definition: What {topic} is\n"
            f"• How it works: Core mechanism\n"
            f"• Why it matters: Exam significance\n"
            f"• Common pitfall: What students get wrong\n"
            f"• Example: Real-world or textbook example"
        )

    return {
        "concept": f"{topic} — a key exam topic. Review your notes and textbook for full details.",
        "answer": answer,
        "mnemonic": f"Think of {topic.split()[0] if topic else 'this'} as a system with inputs and outputs.",
        "diagram_query": f"{topic} diagram labeled",
    }
