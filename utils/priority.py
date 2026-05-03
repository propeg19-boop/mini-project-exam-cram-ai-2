import re

HIGH_KEYWORDS = ['define', 'state', 'list', 'name', 'identify', 'what is', 'what are',
                 'enumerate', 'mention', 'classify', 'distinguish']
MED_KEYWORDS = ['explain', 'describe', 'discuss', 'outline', 'elaborate', 'illustrate',
                'summarize', 'compare', 'contrast', 'differentiate']
LOW_KEYWORDS = ['analyze', 'evaluate', 'critically', 'synthesize', 'justify',
                'argue', 'assess', 'examine', 'investigate', 'propose']

def classify_question(text):
    """Classify a single question by priority based on keywords."""
    text_lower = text.lower()
    high_score = sum(1 for k in HIGH_KEYWORDS if k in text_lower)
    med_score = sum(1 for k in MED_KEYWORDS if k in text_lower)
    low_score = sum(1 for k in LOW_KEYWORDS if k in text_lower)

    if high_score > 0:
        return 'High'
    elif med_score > 0:
        return 'Medium'
    elif low_score > 0:
        return 'Low'
    else:
        # Default: medium for longer questions, high for short
        if len(text) < 60:
            return 'High'
        elif len(text) < 120:
            return 'Medium'
        return 'Low'

def estimate_time(text, priority):
    """Estimate time needed to answer a question."""
    base = {'High': 10, 'Medium': 20, 'Low': 35}
    length_factor = len(text) // 100
    return min(45, base.get(priority, 15) + length_factor * 5)

def build_table(questions):
    """Build a priority table from a list of question strings."""
    table = []
    for q in questions:
        if not q.strip():
            continue
        priority = classify_question(q)
        time_min = estimate_time(q, priority)
        table.append({
            'question': q,
            'priority': priority,
            'estimated_time': f'{time_min} min'
        })
    return table

def build_day_plan(table, days):
    """Distribute questions across days."""
    if not table or days < 1:
        return {}

    # Sort: High first, then Medium, then Low
    sorted_qs = sorted(table, key=lambda x: {'High': 0, 'Medium': 1, 'Low': 2}.get(x['priority'], 1))

    day_plan = {}
    per_day = max(1, len(sorted_qs) // days)

    for d in range(days):
        start = d * per_day
        end = start + per_day if d < days - 1 else len(sorted_qs)
        day_qs = sorted_qs[start:end]
        day_plan[f'Day {d+1}'] = [q['question'] for q in day_qs]

    return day_plan
