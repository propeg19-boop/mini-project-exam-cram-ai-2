"""
ExamCram AI — Flask Backend
Deterministic exam strategy engine. Zero-friction. Always returns valid JSON.

Endpoints:
  POST /start-analysis
  POST /generate-answer
  POST /get-diagrams
  POST /mark-complete
"""

import os
from flask import Flask, request, jsonify
from flask_cors import CORS

from utils.input_processor import clean_input, split_into_topics, detect_input_type
from utils.question_generator import generate_questions
from utils.priority_engine import (
    classify_priorities,
    build_matrix,
    generate_study_plan,
    detect_subject,
    compute_initial_readiness,
)
from utils.answer_engine import generate_answer
from utils.diagram_engine import get_diagrams
from utils.session_manager import (
    create_session,
    get_session,
    mark_topic_complete,
    cache_answer,
    get_cached_answer,
)

app = Flask(__name__)
CORS(app)  # Allow frontend on any origin during development


# ─── Health Check ─────────────────────────────────────────

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "ExamCram AI Backend"})


# ─── POST /start-analysis ─────────────────────────────────

@app.route("/start-analysis", methods=["POST"])
def start_analysis():
    """
    Full pipeline:
    Input → Clean → Detect → (Generate Questions if syllabus)
    → Classify Priority → Build Matrix → Plan → Session → Return
    """
    try:
        body = request.get_json(force=True) or {}
        content = str(body.get("content", "")).strip()
        days    = int(body.get("days", 3))
        level   = str(body.get("level", "standard")).strip()
        tone    = str(body.get("tone", "locked-in")).strip()

        if not content:
            return jsonify({"error": "No content provided."}), 400

        # ── Stage 1: Clean & Split ─────────────────────────
        cleaned   = clean_input(content)
        topics    = split_into_topics(cleaned)

        # ── Stage 2: Detect Input Type ────────────────────
        input_type = detect_input_type(cleaned)

        # ── Stage 3: Syllabus → Questions ─────────────────
        if input_type == "syllabus":
            questions = generate_questions(topics, level)
        else:
            # Already a question bank — use lines as questions
            questions = [t for t in topics if len(t) > 10][:25]

        if not questions:
            return jsonify({"error": "Could not extract questions from input."}), 422

        # ── Stage 4: AI Priority Classification ───────────
        classified = classify_priorities(questions, level)

        # ── Stage 5: Build Matrix & Plan ──────────────────
        matrix  = build_matrix(classified)
        plan    = generate_study_plan(matrix, days)

        # ── Stage 6: Subject + Readiness ──────────────────
        subject         = detect_subject(questions)
        readiness_score = compute_initial_readiness(matrix, days)

        # ── Stage 7: Create Session ───────────────────────
        session = create_session(
            input_type=input_type,
            raw_input=content,
            questions=questions,
            matrix=matrix,
            plan=plan,
            days=days,
            level=level,
            tone=tone,
            subject=subject,
        )

        return jsonify({
            "session_id": session["session_id"],
            "meta": {
                "input_type": input_type,
                "subject": subject,
                "total_questions": len(questions),
                "readiness_score": readiness_score,
            },
            "matrix": matrix,
            "plan": plan,
        })

    except Exception as e:
        app.logger.exception("Error in /start-analysis")
        return jsonify({
            "error": "Analysis engine failed. Please try again.",
            "detail": str(e),
        }), 500


# ─── POST /generate-answer ────────────────────────────────

@app.route("/generate-answer", methods=["POST"])
def generate_answer_route():
    """
    Generate a study answer for a topic in focused/revision/exam mode.
    Caches result in session to avoid repeated AI calls.
    """
    try:
        body       = request.get_json(force=True) or {}
        session_id = str(body.get("session_id", "")).strip()
        topic      = str(body.get("topic", "")).strip()
        mode       = str(body.get("mode", "focused")).strip().lower()

        if not topic:
            return jsonify({"error": "Topic is required."}), 400

        # Check session for level (affects answer depth)
        level = "standard"
        session = get_session(session_id)
        if session:
            level = session.get("level", "standard")

        # ── Cache lookup ──────────────────────────────────
        cache_key = f"{topic}::{mode}"
        cached = get_cached_answer(session_id, cache_key) if session_id else None

        if cached:
            return jsonify(cached)

        # ── Generate ──────────────────────────────────────
        result = generate_answer(topic, mode, level)

        # ── Cache result ──────────────────────────────────
        if session_id:
            cache_answer(session_id, cache_key, result)

        return jsonify(result)

    except Exception as e:
        app.logger.exception("Error in /generate-answer")
        return jsonify({
            "concept":       "Answer generation failed. Try again.",
            "answer":        f"• Review your notes on this topic\n• Check your textbook\n• Topic: {body.get('topic', '')}",
            "mnemonic":      "Review → Recall → Revise",
            "diagram_query": f"{body.get('topic', 'diagram')} labeled diagram",
        })


# ─── POST /get-diagrams ───────────────────────────────────

@app.route("/get-diagrams", methods=["POST"])
def get_diagrams_route():
    """
    Fetch 3 diagram images for a query via SerpAPI.
    Always returns 3 URLs (real or placeholder).
    """
    try:
        body  = request.get_json(force=True) or {}
        query = str(body.get("query", "")).strip()

        if not query:
            return jsonify({"images": _placeholders()})

        images = get_diagrams(query)
        return jsonify({"images": images})

    except Exception as e:
        app.logger.exception("Error in /get-diagrams")
        return jsonify({"images": _placeholders()})


# ─── POST /mark-complete ──────────────────────────────────

@app.route("/mark-complete", methods=["POST"])
def mark_complete():
    """
    Mark a topic as complete, update XP and rank.
    Returns updated progress_score, rank, and motivational message.
    """
    try:
        body       = request.get_json(force=True) or {}
        session_id = str(body.get("session_id", "")).strip()
        topic      = str(body.get("topic", "")).strip()

        if not session_id or not topic:
            return jsonify({"error": "session_id and topic required."}), 400

        result = mark_topic_complete(session_id, topic)
        return jsonify(result)

    except Exception as e:
        app.logger.exception("Error in /mark-complete")
        return jsonify({
            "progress_score": 0,
            "rank": "Unprepared",
            "message": "Progress update failed.",
        }), 500


# ─── Helpers ──────────────────────────────────────────────

def _placeholders() -> list[str]:
    return [
        "https://placehold.co/600x400/111114/8B5CF6?text=Diagram+Loading",
        "https://placehold.co/600x400/111114/EC4899?text=Visual+Aid",
        "https://placehold.co/600x400/111114/F97316?text=Reference+Image",
    ]


# ─── Entry Point ──────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
