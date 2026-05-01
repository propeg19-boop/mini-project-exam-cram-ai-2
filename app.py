"""
app.py — ExamCram AI Flask Backend
Routes: /, /generate-plan, /generate-answer, /get-images, /save-queue, /get-queue
"""

import os
from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

from utils.ai_handler    import generate_plan, generate_answer
from utils.image_fetcher import fetch_images
from utils.priority      import split_questions, build_table, build_day_plan

# ─── App setup ───────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "examcram-secret-dev-key-change-in-prod")
CORS(app, supports_credentials=True)

# In-memory queue store (simple dict keyed by session)
# Fine for single-user/dev; swap for Redis in production
_queue_store: dict = {}


# ─── Frontend ────────────────────────────────────────────────────────────────
@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")


# ─── /generate-plan ──────────────────────────────────────────────────────────
@app.route("/generate-plan", methods=["POST"])
def route_generate_plan():
    try:
        body      = request.get_json(force=True) or {}
        questions = body.get("questions", "").strip()
        days      = int(body.get("days", 5))
        level     = body.get("level", "intermediate")
        tone      = body.get("tone", "casual")

        if not questions:
            return jsonify({"error": "No questions provided"}), 400

        try:
            result = generate_plan(questions, days, level, tone)
            if not result.get("table"):
                raise ValueError("AI returned empty table")
            return jsonify(result)

        except Exception as ai_err:
            print(f"[Plan] AI failed ({ai_err}), using local fallback")
            q_list   = split_questions(questions)
            table    = build_table(q_list)
            day_plan = build_day_plan(table, days)
            return jsonify({
                "table":    table,
                "day_plan": day_plan,
                "meta":     {"days": days, "total": len(q_list)},
            })

    except Exception as e:
        print(f"[Plan] Error: {e}")
        return jsonify({"error": str(e)}), 500


# ─── /generate-answer ────────────────────────────────────────────────────────
@app.route("/generate-answer", methods=["POST"])
def route_generate_answer():
    try:
        body     = request.get_json(force=True) or {}
        question = body.get("question", "").strip()
        mode     = body.get("mode", "focused")
        level    = body.get("level", "intermediate")
        tone     = body.get("tone", "casual")

        if not question:
            return jsonify({"error": "No question provided"}), 400

        result = generate_answer(question, mode, level, tone)
        return jsonify(result)

    except Exception as e:
        print(f"[Answer] Error: {e}")
        return jsonify({
            "answer":        f"Could not generate answer: {str(e)}",
            "analogy":       "",
            "understanding": "",
            "extra":         "Check your API key or try again.",
        }), 500


# ─── /get-images ─────────────────────────────────────────────────────────────
@app.route("/get-images", methods=["POST"])
def route_get_images():
    try:
        body  = request.get_json(force=True) or {}
        topic = body.get("topic", "").strip()

        if not topic:
            return jsonify({"error": "No topic provided"}), 400

        images = fetch_images(topic)
        return jsonify({"images": images})

    except Exception as e:
        print(f"[Images] Error: {e}")
        return jsonify({
            "images": [
                "https://placehold.co/640x400/13131f/9333ea?text=Error",
                "https://placehold.co/640x400/13131f/06b6d4?text=Error",
                "https://placehold.co/640x400/13131f/ec4899?text=Error",
            ]
        }), 500


# ─── /save-queue  (Timer queue persistence) ──────────────────────────────────
@app.route("/save-queue", methods=["POST"])
def route_save_queue():
    """
    Save the timer question queue to server memory.
    Called when user clicks 'Timer →' from Breakdown tab.

    Body: { "questions": ["q1", "q2", ...] }
    """
    try:
        body      = request.get_json(force=True) or {}
        questions = body.get("questions", [])

        if not isinstance(questions, list):
            return jsonify({"error": "questions must be a list"}), 400

        # Use IP as a simple session key (good enough for dev/demo)
        key = request.remote_addr or "default"
        _queue_store[key] = [
            {"text": q, "done": False}
            for q in questions
            if isinstance(q, str) and q.strip()
        ]

        print(f"[Queue] Saved {len(_queue_store[key])} questions for {key}")
        return jsonify({"saved": len(_queue_store[key])})

    except Exception as e:
        print(f"[Queue] Save error: {e}")
        return jsonify({"error": str(e)}), 500


# ─── /get-queue  (Timer queue retrieval) ─────────────────────────────────────
@app.route("/get-queue", methods=["GET"])
def route_get_queue():
    """
    Retrieve the saved timer question queue.
    Called when Timer tab loads.

    Returns: { "questions": [{"text": str, "done": bool}, ...] }
    """
    try:
        key = request.remote_addr or "default"
        queue = _queue_store.get(key, [])
        print(f"[Queue] Returning {len(queue)} questions for {key}")
        return jsonify({"questions": queue})

    except Exception as e:
        print(f"[Queue] Get error: {e}")
        return jsonify({"questions": []}), 500


# ─── /clear-queue ────────────────────────────────────────────────────────────
@app.route("/clear-queue", methods=["POST"])
def route_clear_queue():
    """Clear the queue when user resets timer."""
    key = request.remote_addr or "default"
    _queue_store.pop(key, None)
    return jsonify({"cleared": True})


# ─── Run ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port  = int(os.getenv("PORT", 5000))
    debug = os.getenv("DEBUG", "true").lower() == "true"
    print(f"ExamCram AI backend running on port {port}")
    app.run(host="0.0.0.0", port=port, debug=debug)
