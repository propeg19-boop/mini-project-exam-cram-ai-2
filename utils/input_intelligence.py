import re
import json
from utils.ai_handler import call_ai

def analyse_input(content):
    """Classify the input document type using AI or local fallback."""
    if not content or len(content.strip()) < 50:
        return {
            'type': 'notes',
            'confidence': 30,
            'subject': 'General',
            'question_count': 0,
            'unit_count': 0
        }

    prompt = f"""Analyse this academic document. Classify it strictly as one of:
- question_bank: contains explicit exam questions (define, explain, analyze etc)
- syllabus: contains topics, units, learning objectives but no direct questions
- notes: paragraph-form textbook or lecture content
- mixed: contains both topic headings AND explicit questions

Document content (first 3000 chars):
{content[:3000]}

Return ONLY valid JSON:
{{
  "type": "question_bank|syllabus|notes|mixed",
  "confidence": 0-100,
  "subject": "detected subject name",
  "question_count": estimated number of explicit questions if any,
  "unit_count": estimated number of topics/units if any
}}"""

    result = call_ai(prompt, temperature=0.3, max_tokens=512)
    if result and 'type' in result:
        return result

    # Local fallback
    text_lower = content.lower()
    keywords = ['define', 'explain', 'analyze', 'compare', 'what', 'why', 'how',
                'describe', 'discuss', 'evaluate', 'contrast', 'list', 'state',
                'identify', 'differentiate', 'illustrate']
    count = sum(1 for k in keywords if k in text_lower)

    # Detect subject
    subjects = {
        'biology': ['biology', 'cell', 'photosynthesis', 'mitosis', 'dna', 'rna', 'organism'],
        'physics': ['physics', 'force', 'energy', 'motion', 'quantum', 'thermodynamics'],
        'chemistry': ['chemistry', 'molecule', 'reaction', 'acid', 'base', 'organic'],
        'mathematics': ['mathematics', 'calculus', 'algebra', 'geometry', 'equation', 'theorem'],
        'computer science': ['algorithm', 'programming', 'data structure', 'code', 'software'],
        'history': ['history', 'war', 'empire', 'revolution', 'century', 'civilization'],
        'economics': ['economics', 'market', 'supply', 'demand', 'gdp', 'inflation']
    }

    detected_subject = 'General'
    for subj, markers in subjects.items():
        if any(m in text_lower for m in markers):
            detected_subject = subj.title()
            break

    if count > 5:
        doc_type = 'question_bank'
    elif count > 2:
        doc_type = 'mixed'
    elif 'unit' in text_lower or 'module' in text_lower or 'topic' in text_lower:
        doc_type = 'syllabus'
    else:
        doc_type = 'notes'

    return {
        'type': doc_type,
        'confidence': min(100, 40 + count * 10),
        'subject': detected_subject,
        'question_count': content.count('?') if doc_type in ('question_bank', 'mixed') else 0,
        'unit_count': len(re.findall(r'(?:Unit|Module|Chapter|Topic)\s*\d+', content, re.I))
    }

def parse_syllabus(content, subject='General'):
    """Extract topics and units from syllabus content."""
    prompt = f"""Extract all topics and units from this syllabus/notes document.

Subject: {subject}

Document content:
{content[:4000]}

Return ONLY valid JSON:
{{
  "units": [
    {{
      "name": "Unit name",
      "weight": "High|Medium|Low (based on how much space it takes)",
      "topics": ["topic 1", "topic 2", ...]
    }}
  ],
  "total_topics": int
}}"""

    result = call_ai(prompt, temperature=0.3, max_tokens=1024)
    if result and 'units' in result:
        return result

    # Local fallback: try to detect units by headers
    units = []
    # Match patterns like "Unit 1", "Module 1", "Chapter 1", "Topic 1"
    unit_matches = list(re.finditer(
        r'(?:Unit|Module|Chapter|Topic)\s*(\d+)[.:]?\s*(.*?)(?=(?:Unit|Module|Chapter|Topic)\s*\d+|\Z)',
        content, re.I | re.DOTALL
    ))

    if not unit_matches:
        # Fallback: split by numbered lines
        lines = [l.strip() for l in content.split('\n') if l.strip()]
        chunks = [lines[i:i+5] for i in range(0, len(lines), 5)]
        for i, chunk in enumerate(chunks[:6]):
            units.append({
                'name': f'Unit {i+1}',
                'weight': 'Medium',
                'topics': chunk[:3]
            })
    else:
        for m in unit_matches:
            unit_num = m.group(1)
            unit_text = m.group(2).strip()
            # Extract topics as bullet points or numbered items
            topics = re.findall(r'[•\-\d.]+\s*(.*?)(?=[•\-\d.]+|$)', unit_text, re.DOTALL)
            topics = [t.strip() for t in topics if len(t.strip()) > 3][:5]
            if not topics:
                topics = [unit_text[:80]]
            units.append({
                'name': f'Unit {unit_num}',
                'weight': 'Medium',
                'topics': topics
            })

    all_topics = sum(len(u['topics']) for u in units)
    return {'units': units, 'total_topics': all_topics}

def generate_questions_from_syllabus(units, level='intermediate', subject='General'):
    """Generate exam questions from syllabus units."""
    all_topics = []
    for u in units:
        all_topics.extend(u.get('topics', []))

    if not all_topics:
        return {'questions': []}

    topics_text = '\n'.join(f"- {t}" for t in all_topics[:20])

    prompt = f"""You are an expert {subject} examiner.
Generate exam questions for these topics:
{topics_text}

Student level: {level}

For each topic generate:
- 1 High priority question (define/state/list/name/identify)
- 1 Medium priority question (explain/describe/discuss/outline)
- 1 Low priority question (analyze/compare/evaluate/contrast)

Return ONLY valid JSON:
{{
  "questions": [
    {{
      "question": "question text",
      "topic": "source topic",
      "unit": "source unit",
      "priority": "High|Medium|Low",
      "estimated_time": "10 min|20 min|35 min",
      "source": "generated"
    }}
  ]
}}"""

    result = call_ai(prompt, temperature=0.7, max_tokens=2048)
    if result and 'questions' in result:
        return result

    # Local fallback: generate simple questions from topics
    questions = []
    for topic in all_topics[:15]:
        questions.append({
            'question': f'Define and explain {topic}.',
            'topic': topic,
            'unit': 'General',
            'priority': 'High',
            'estimated_time': '15 min',
            'source': 'generated'
        })
        questions.append({
            'question': f'Describe the importance and applications of {topic}.',
            'topic': topic,
            'unit': 'General',
            'priority': 'Medium',
            'estimated_time': '20 min',
            'source': 'generated'
        })

    return {'questions': questions}

def predict_exam_questions(questions, subject='General', level='intermediate', days=5):
    """Predict most likely exam questions from a question bank."""
    n = min(15, len(questions))
    if n == 0:
        return {'predicted': []}

    # Format questions for prompt
    q_list = []
    for q in questions[:30]:
        if isinstance(q, dict):
            q_list.append(f"- {q.get('question', q.get('text', str(q)))} (Priority: {q.get('priority', 'Medium')})")
        else:
            q_list.append(f"- {q}")
    q_text = '\n'.join(q_list)

    prompt = f"""You are an experienced {subject} professor who sets exam papers.
From this question bank, select the {n} questions most likely to appear in a real university exam.

Questions:
{q_text}

Student level: {level}
Days to exam: {days}

Consider:
- Topics that appear multiple times = higher probability
- Foundational concepts always appear
- Higher-order questions (analyze/evaluate) are common at advanced level

Return ONLY valid JSON:
{{
  "predicted": [
    {{
      "question": "question text",
      "probability": "High|Medium",
      "reason": "one sentence why this is likely",
      "topic": "topic name",
      "priority": "High|Medium|Low"
    }}
  ]
}}"""

    result = call_ai(prompt, temperature=0.5, max_tokens=2048)
    if result and 'predicted' in result:
        return result

    # Local fallback: pick high priority questions
    high_qs = [q for q in questions if isinstance(q, dict) and q.get('priority') == 'High']
    if not high_qs:
        high_qs = questions[:n]

    predicted = []
    for q in high_qs[:n]:
        if isinstance(q, dict):
            predicted.append({
                'question': q.get('question', q.get('text', str(q))),
                'probability': 'High',
                'reason': 'Core concept frequently tested in exams',
                'topic': q.get('topic', 'General'),
                'priority': q.get('priority', 'High')
            })
        else:
            predicted.append({
                'question': str(q),
                'probability': 'Medium',
                'reason': 'Important topic area',
                'topic': 'General',
                'priority': 'Medium'
            })

    return {'predicted': predicted}
