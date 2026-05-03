"""
Session Manager — in-memory store for all active ExamCram sessions.
Holds questions, matrix, plan, progress, rank, and answer cache.
"""

import uuid
from datetime import datetime

# ─── In-memory store (replace with Redis for production) ───
_sessions: dict = {}

RANK_THRESHOLDS = [
    (80, "Topper Mode"),
    (60, "Exam Ready"),
    (40, "Getting There"),
    (20, "Surviving"),
    (0,  "Unprepared"),
]

FEEDBACK_MESSAGES = {
    "critical": [
        "Critical topic cleared. Big W.",
        "You're not cooked anymore.",
        "Rank up incoming.",
        "That was the heavy one. Keep going.",
    ],
    "important": [
        "Solid. One more down.",
        "Getting there. Don't stop now.",
        "Important topic locked in.",
    ],
    "skip": [
        "Even the small ones count.",
        "Skim secured.",
        "Covered. Move on.",
    ],
}

import random

def create_session(input_type: str, raw_input: str, questions: list,
                   matrix: dict, plan: dict, days: int,
                   level: str, tone: str, subject: str) -> dict:
    """Create and store a new session. Returns full session dict."""
    session_id = str(uuid.uuid4())

    # Compute max possible score for readiness calculation
    total_possible = _compute_max_score(matrix)

    session = {
        "session_id": session_id,
        "created_at": datetime.utcnow().isoformat(),
        "input_type": input_type,
        "raw_input": raw_input,
        "days": days,
        "level": level,
        "tone": tone,
        "subject": subject,
        "questions": questions,
        "matrix": matrix,
        "plan": plan,
        "progress_score": 0,
        "rank": "Unprepared",
        "completed_topics": [],
        "answers_cache": {},
        "total_possible": total_possible,
        "earned_score": 0,
    }

    _sessions[session_id] = session
    return session


def get_session(session_id: str) -> dict | None:
    return _sessions.get(session_id)


def mark_topic_complete(session_id: str, topic: str) -> dict:
    """
    Mark a topic done, add weighted XP, recalculate score + rank.
    Returns: { progress_score, rank, message }
    """
    session = get_session(session_id)
    if not session:
        return {"progress_score": 0, "rank": "Unprepared", "message": "Session not found."}

    if topic in session["completed_topics"]:
        return {
            "progress_score": session["progress_score"],
            "rank": session["rank"],
            "message": "Already completed.",
        }

    # Find priority of this topic in the matrix
    priority = _find_priority(session["matrix"], topic)
    weights = {"critical": 5, "important": 3, "skip": 1}
    earned = weights.get(priority, 1)

    session["completed_topics"].append(topic)
    session["earned_score"] += earned

    # Recalculate percentage
    total = max(session["total_possible"], 1)
    pct = round((session["earned_score"] / total) * 100)
    session["progress_score"] = min(pct, 100)

    # Determine rank
    rank = "Unprepared"
    for threshold, name in RANK_THRESHOLDS:
        if pct >= threshold:
            rank = name
            break
    session["rank"] = rank

    # Pick feedback message
    msgs = FEEDBACK_MESSAGES.get(priority, FEEDBACK_MESSAGES["skip"])
    message = random.choice(msgs)

    return {
        "progress_score": session["progress_score"],
        "rank": rank,
        "message": message,
    }


def cache_answer(session_id: str, cache_key: str, answer: dict):
    session = get_session(session_id)
    if session:
        session["answers_cache"][cache_key] = answer


def get_cached_answer(session_id: str, cache_key: str) -> dict | None:
    session = get_session(session_id)
    if session:
        return session["answers_cache"].get(cache_key)
    return None


# ─── Helpers ───────────────────────────────────────────────

def _compute_max_score(matrix: dict) -> int:
    weights = {"critical": 5, "important": 3, "skip": 1}
    total = 0
    for priority, items in matrix.items():
        total += len(items) * weights.get(priority, 1)
    return max(total, 1)


def _find_priority(matrix: dict, topic: str) -> str:
    for priority, items in matrix.items():
        for item in items:
            q = item.get("question", "") if isinstance(item, dict) else item
            if q == topic or topic in q:
                return priority
    return "skip"
