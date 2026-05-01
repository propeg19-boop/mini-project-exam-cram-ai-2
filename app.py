"""
app.py — ExamCram AI Flask Backend
Routes: /generate-plan, /generate-answer, /get-images
"""

import os
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Load .env before importing utils (they read env vars at call time, not import time)
load_dotenv()

from utils.ai_handler    import generate_plan, generate_answer
from utils.image_fetcher import fetch_images
from utils.priority      import split_questions, build_table, build_day_plan

# ─── App setup ───────────────────────────────────────────────────────────────
app = Flask(__name__)
CORS(app)   # Allow requests from the frontend (any origin)


# ─── Health check ────────────────────────────────────────────────────────────
@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ExamCram AI backend is running ✅"})


# ─── /generate-plan ──────────────────────────────────────────────────────────
@app.route("/generate-plan", methods=["POST"])
def route_generate_plan():
    """
    Accepts: { questions, days, level, tone }
    Returns: { table, day_plan, meta }
    """
    try:
        body      = request.get_json(force=True) or {}
        questions = body.get("questions", "").strip()
        days      = int(body.get("days", 5))
        level     = body.get("level", "intermediate")
        tone      = body.get("tone", "casual")

        if not questions:
            return jsonify({"error": "No questions provided"}), 400

        # ── Strategy: try Gemini first, fall back to local classifier ──────
        try:
            result = generate_plan(questions, days, level, tone)

            # Safety net: if Gemini didn't return a proper table, rebuild locally
            if not result.get("table"):
                raise ValueError("Gemini returned empty table")

            return jsonify(result)

        except Exception as ai_err:
            print(f"[Plan] AI failed ({ai_err}), using local classifier fallback")

            # Local fallback — no AI needed
            q_list   = split_questions(questions)
            table    = build_table(q_list)
            day_plan = build_day_plan(table, days)

            return jsonify({
                "table":    table,
                "day_plan": day_plan,
                "meta":     {"days": days, "total": len(q_list)},
            })

    except Exception as e:
        print(f"[Plan] Unhandled error: {e}")
        return jsonify({"error": str(e)}), 500


# ─── /generate-answer ────────────────────────────────────────────────────────
@app.route("/generate-answer", methods=["POST"])
def route_generate_answer():
    """
    Accepts: { question, mode, level, tone }
    Returns: { analogy, understanding, answer, extra }  (exam mode: just { answer })
    """
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
        print(f"[Answer] Unhandled error: {e}")
        # Always return valid JSON so the frontend doesn't break
        return jsonify({
            "answer":       f"Could not generate answer: {str(e)}",
            "analogy":      "",
            "understanding": "",
            "extra":        "Please check your API key and try again.",
        }), 500


# ─── /get-images ─────────────────────────────────────────────────────────────
@app.route("/get-images", methods=["POST"])
def route_get_images():
    """
    Accepts: { topic }
    Returns: { images: [url, url, url] }
    """
    try:
        body  = request.get_json(force=True) or {}
        topic = body.get("topic", "").strip()

        if not topic:
            return jsonify({"error": "No topic provided"}), 400

        images = fetch_images(topic)
        return jsonify({"images": images})

    except Exception as e:
        print(f"[Images] Unhandled error: {e}")
        return jsonify({
            "images": [
                "https://placehold.co/640x400/13131f/9333ea?text=Error",
                "https://placehold.co/640x400/13131f/06b6d4?text=Error",
                "https://placehold.co/640x400/13131f/ec4899?text=Error",
            ]
        }), 500


# ─── Run ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("DEBUG", "true").lower() == "true"
    print(f"🚀 ExamCram AI backend starting on port {port}")
    app.run(host="0.0.0.0", port=port, debug=debug)
