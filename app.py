"""
app.py — ExamCram AI Flask Backend
Routes: /, /generate-plan, /generate-answer, /get-images
"""

import os
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from utils.ai_handler    import generate_plan, generate_answer
from utils.image_fetcher import fetch_images
from utils.priority      import split_questions, build_table, build_day_plan

# ─── App setup ───────────────────────────────────────────────────────────────
app = Flask(__name__)
CORS(app)


# ─── Frontend route ──────────────────────────────────────────────────────────
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
                raise ValueError("Gemini returned empty table")

            return jsonify(result)

        except Exception as ai_err:
            print(f"[Plan] AI failed ({ai_err}), using fallback")

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
            "answer": f"Could not generate answer: {str(e)}",
            "analogy": "",
            "understanding": "",
            "extra": "Check API key or try again.",
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


# ─── Run ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("DEBUG", "true").lower() == "true"
    print(f"🚀 ExamCram AI backend running on port {port}")
    app.run(host="0.0.0.0", port=port, debug=debug)
