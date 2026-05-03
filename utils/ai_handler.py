import os
import requests
import json
import re
import traceback

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')

MODEL_CHAIN = [
    "gemini-3.1-flash-lite-preview",
    "gemini-2.5-flash-lite-preview-06-17",
    "gemini-2.5-flash",
    "gemini-3.0-flash",
    "gemini-2.5-pro",
    "gemma-3-27b-it",
]

def call_ai(prompt, temperature=0.7, max_tokens=2048):
    """Try each model in MODEL_CHAIN until one succeeds."""
    if not GEMINI_API_KEY:
        print('[AIError: No GEMINI_API_KEY set]')
        return None

    for model in MODEL_CHAIN:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": max_tokens
                }
            }
            resp = requests.post(url, json=payload, timeout=60)
            if resp.status_code != 200:
                print(f'[AIWarn: {model} returned {resp.status_code}]')
                continue

            data = resp.json()
            candidates = data.get('candidates', [])
            if not candidates:
                continue

            text = candidates[0].get('content', {}).get('parts', [{}])[0].get('text', '')
            if not text:
                continue

            # Try to extract JSON
            result = extract_json(text)
            if result:
                return result

            # If no JSON but we got text, wrap it
            return {"answer": text, "analogy": "", "understanding": "", "extra": ""}

        except Exception as e:
            print(f'[AIWarn: {model} failed: {str(e)}]')
            continue

    print('[AIError: All models in chain failed]')
    return None

def extract_json(text):
    """Extract JSON from text, handling fences and raw blocks."""
    # Strip markdown fences
    cleaned = re.sub(r'```json\s*', '', text)
    cleaned = re.sub(r'```\s*', '', cleaned)
    cleaned = cleaned.strip()

    # Try direct parse
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Find first { } block
    match = re.search(r'\{.*\}', cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return None

def generate_plan_prompt(questions_text, days, level, tone):
    return f"""You are an expert study planner. Create a day-wise study plan for these exam questions.

Questions:
{questions_text}

Parameters:
- Days available: {days}
- Student level: {level}
- Preferred tone: {tone}

Classify each question as High/Medium/Low priority based on:
- High: foundational concepts, frequently tested, definitions
- Medium: explanatory questions, moderate complexity
- Low: advanced analysis, rarely tested, niche topics

Estimate time needed per question (10-45 min).

Return ONLY valid JSON in this exact structure:
{{
  "table": [
    {{"question": "question text", "priority": "High|Medium|Low", "estimated_time": "15 min"}}
  ],
  "day_plan": {{
    "Day 1": ["question text 1", "question text 2"],
    "Day 2": ["question text 3"]
  }},
  "meta": {{
    "days": {days},
    "total": number_of_questions
  }}
}}
"""

def generate_answer_prompt(question, mode, level, tone):
    if mode == 'exam':
        return f"""Write a complete, exam-ready answer for this question.

Question: {question}
Student level: {level}

Provide a well-structured answer that could be written in an exam:
- Clear introduction with definition
- 3-4 key points with examples
- Concluding statement
- Mention approximate marks and time allocation

Return ONLY valid JSON: {{"answer": "your complete answer here"}}"""

    return f"""Explain this concept deeply for a {level} level student.

Question: {question}
Tone: {tone}

Return ONLY valid JSON with these exact keys:
{{
  "analogy": "a relatable real-world analogy",
  "understanding": "the core concept explained simply",
  "answer": "a thorough academic explanation with structure",
  "extra": "exam tips, common mistakes, or related concepts"
}}
"""
