from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os
import json
import traceback

from utils.ai_handler import call_ai, generate_plan_prompt, generate_answer_prompt
from utils.input_intelligence import analyse_input, parse_syllabus, generate_questions_from_syllabus, predict_exam_questions
from utils.priority import classify_question, build_table, build_day_plan
from utils.image_fetcher import fetch_images

load_dotenv()

app = Flask(__name__)
CORS(app)

SECRET_KEY = os.getenv('SECRET_KEY', 'examcram-secret-key')
app.secret_key = SECRET_KEY

# In-memory queue store
_queue_store = {}

# ─── ROUTES ───

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyse-input', methods=['POST'])
def analyse_input_route():
    try:
        data = request.get_json()
        content = data.get('content', '')
        result = analyse_input(content)
        return jsonify(result)
    except Exception as e:
        print(f'[AnalyseInputError: {str(e)}]')
        traceback.print_exc()
        # Fallback classification
        text_lower = content.lower()
        keywords = ['define', 'explain', 'analyze', 'compare', 'what', 'why', 'how', 'describe', 'discuss', 'evaluate']
        count = sum(1 for k in keywords if k in text_lower)
        q_type = 'question_bank' if count > 3 else 'syllabus'
        return jsonify({
            'type': q_type,
            'confidence': 50,
            'subject': 'General',
            'question_count': content.count('?') if q_type == 'question_bank' else 0,
            'unit_count': 0
        })

@app.route('/parse-syllabus', methods=['POST'])
def parse_syllabus_route():
    try:
        data = request.get_json()
        content = data.get('content', '')
        subject = data.get('subject', 'General')
        result = parse_syllabus(content, subject)
        return jsonify(result)
    except Exception as e:
        print(f'[ParseSyllabusError: {str(e)}]')
        traceback.print_exc()
        return jsonify({'units': [], 'total_topics': 0})

@app.route('/generate-questions', methods=['POST'])
def generate_questions_route():
    try:
        data = request.get_json()
        units = data.get('units', [])
        level = data.get('level', 'intermediate')
        subject = data.get('subject', 'General')
        result = generate_questions_from_syllabus(units, level, subject)
        return jsonify(result)
    except Exception as e:
        print(f'[GenerateQuestionsError: {str(e)}]')
        traceback.print_exc()
        return jsonify({'questions': []})

@app.route('/predict-exam', methods=['POST'])
def predict_exam_route():
    try:
        data = request.get_json()
        questions = data.get('questions', [])
        subject = data.get('subject', 'General')
        level = data.get('level', 'intermediate')
        days = data.get('days', 5)
        result = predict_exam_questions(questions, subject, level, days)
        return jsonify(result)
    except Exception as e:
        print(f'[PredictExamError: {str(e)}]')
        traceback.print_exc()
        return jsonify({'predicted': []})

@app.route('/generate-plan', methods=['POST'])
def generate_plan_route():
    try:
        data = request.get_json()
        questions_text = data.get('questions', '')
        days = int(data.get('days', 5))
        level = data.get('level', 'intermediate')
        tone = data.get('tone', 'casual')

        # Try AI first
        prompt = generate_plan_prompt(questions_text, days, level, tone)
        ai_result = call_ai(prompt)

        if ai_result and 'table' in ai_result:
            return jsonify(ai_result)

        # Fallback to local logic
        questions = [q.strip() for q in questions_text.split('\n') if q.strip()]
        table = build_table(questions)
        day_plan = build_day_plan(table, days)
        return jsonify({
            'table': table,
            'day_plan': day_plan,
            'meta': {'days': days, 'total': len(questions)}
        })
    except Exception as e:
        print(f'[GeneratePlanError: {str(e)}]')
        traceback.print_exc()
        return jsonify({'table': [], 'day_plan': {}, 'meta': {'days': 5, 'total': 0}})

@app.route('/generate-answer', methods=['POST'])
def generate_answer_route():
    try:
        data = request.get_json()
        question = data.get('question', '')
        mode = data.get('mode', 'focused')
        level = data.get('level', 'intermediate')
        tone = data.get('tone', 'casual')

        prompt = generate_answer_prompt(question, mode, level, tone)
        result = call_ai(prompt)

        if result:
            return jsonify(result)

        # Fallback
        if mode == 'exam':
            return jsonify({'answer': f'**Answer:**\n\n{question} is an important concept. Start with a clear definition, provide 2-3 key points with examples, and conclude with a summary statement. Time allocation: approximately 15-20 minutes for a complete answer.'})
        return jsonify({
            'analogy': 'Think of this like building a house — you need a strong foundation before adding details.',
            'understanding': 'The core idea is understanding relationships between key concepts.',
            'answer': f'**Detailed Answer:**\n\n{question}\n\n1. **Definition**: Start with a precise academic definition.\n2. **Key Components**: Break down into 3-4 main parts.\n3. **Examples**: Provide concrete real-world applications.\n4. **Connections**: Link to related concepts in the syllabus.',
            'extra': '**Exam Tip**: This topic frequently appears in 4-6 mark questions. Practice writing a concise answer within 15 minutes.'
        })
    except Exception as e:
        print(f'[GenerateAnswerError: {str(e)}]')
        traceback.print_exc()
        return jsonify({'answer': 'Unable to generate answer at this time. Please try again.'})

@app.route('/get-images', methods=['POST'])
def get_images_route():
    try:
        data = request.get_json()
        topic = data.get('topic', '')
        images = fetch_images(topic)
        return jsonify({'images': images})
    except Exception as e:
        print(f'[GetImagesError: {str(e)}]')
        traceback.print_exc()
        return jsonify({'images': [
            f'https://placehold.co/400x250/1a1a2e/8b5cf6?text={topic[:20].replace(" ","+")}+Diagram+1',
            f'https://placehold.co/400x250/1a1a2e/06b6d4?text={topic[:20].replace(" ","+")}+Diagram+2',
            f'https://placehold.co/400x250/1a1a2e/ec4899?text={topic[:20].replace(" ","+")}+Diagram+3'
        ]})

@app.route('/save-queue', methods=['POST'])
def save_queue_route():
    try:
        data = request.get_json()
        questions = data.get('questions', [])
        ip = request.remote_addr
        _queue_store[ip] = [{'text': q, 'done': False} for q in questions]
        return jsonify({'saved': len(questions)})
    except Exception as e:
        print(f'[SaveQueueError: {str(e)}]')
        return jsonify({'saved': 0})

@app.route('/get-queue', methods=['GET'])
def get_queue_route():
    try:
        ip = request.remote_addr
        queue = _queue_store.get(ip, [])
        return jsonify({'questions': queue})
    except Exception as e:
        print(f'[GetQueueError: {str(e)}]')
        return jsonify({'questions': []})

@app.route('/clear-queue', methods=['POST'])
def clear_queue_route():
    try:
        ip = request.remote_addr
        if ip in _queue_store:
            del _queue_store[ip]
        return jsonify({'cleared': True})
    except Exception as e:
        print(f'[ClearQueueError: {str(e)}]')
        return jsonify({'cleared': False})

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('DEBUG', 'true').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)
