"""
priority.py — Question priority classifier
Matches keywords to assign High / Medium / Low priority
"""

import re

# Keyword maps — order matters, High checked first
HIGH_KEYWORDS    = r'\b(define|list|state|name|what is|what are|identify|mention|give|write|label)\b'
MEDIUM_KEYWORDS  = r'\b(explain|describe|write about|outline|summarise|summarize|illustrate|discuss|show|how does|how do)\b'
LOW_KEYWORDS     = r'\b(analyze|analyse|compare|derive|evaluate|differentiate|contrast|justify|assess|examine|critically|elaborate)\b'

# Rough time estimates per priority (in minutes)
TIME_MAP = {
    'High':   '10–15 min',
    'Medium': '20–30 min',
    'Low':    '35–45 min',
}


def classify_question(question: str) -> dict:
    """
    Given a question string, return its priority and estimated study time.
    Returns: { "priority": str, "estimated_time": str }
    """
    text = question.lower().strip()

    if re.search(HIGH_KEYWORDS, text):
        priority = 'High'
    elif re.search(LOW_KEYWORDS, text):
        priority = 'Low'
    elif re.search(MEDIUM_KEYWORDS, text):
        priority = 'Medium'
    else:
        # Default fallback: Medium for anything unrecognised
        priority = 'Medium'

    return {
        'priority':       priority,
        'estimated_time': TIME_MAP[priority],
    }


def split_questions(raw: str) -> list[str]:
    """
    Split a multi-line question dump into individual question strings.
    Strips leading numbering like "1.", "Q1.", "a)", etc.
    """
    lines = raw.strip().split('\n')
    cleaned = []
    for line in lines:
        # Strip common prefixes: 1. / 1) / Q1. / a) / A.
        line = re.sub(r'^[\s]*(?:Q\d+\.?|\d+[.):]|[A-Za-z][.):])\s*', '', line, flags=re.IGNORECASE)
        line = line.strip()
        if len(line) > 3:   # ignore empty / too-short lines
            cleaned.append(line)
    return cleaned


def build_table(questions: list[str]) -> list[dict]:
    """
    Build the priority table sent to the frontend.
    Returns list of { question, priority, estimated_time }
    """
    table = []
    for q in questions:
        row = classify_question(q)
        row['question'] = q
        table.append(row)
    return table


def build_day_plan(table: list[dict], days: int) -> dict:
    """
    Distribute questions across available days.
    High-priority questions go to Day 1; the rest spread evenly.
    Returns { "Day 1": [...], "Day 2": [...], ... }
    """
    # Sort: High → Medium → Low
    order = {'High': 0, 'Medium': 1, 'Low': 2}
    sorted_qs = sorted(table, key=lambda r: order[r['priority']])

    # Chunk into days
    total = len(sorted_qs)
    per_day = max(1, -(-total // days))  # ceiling division

    day_plan = {}
    for i in range(days):
        chunk = sorted_qs[i * per_day:(i + 1) * per_day]
        if not chunk:
            break
        day_plan[f'Day {i + 1}'] = [row['question'] for row in chunk]

    return day_plan
