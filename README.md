ExamCram AI v3.0
Drop your paper. Get your plan.
A redesigned, intelligent exam preparation assistant built with Flask. Upload any question paper, syllabus, or notes — and get a personalized study plan, AI-generated answers, predicted exam questions, and a Pomodoro-style focus timer.
What's New in v3.0
Complete Frontend Redesign
Flow-driven UX — Three clear phases: Input → Processing → Workspace
Zero-tab navigation — Everything flows naturally; no disconnected views
Dark glassmorphism UI — Purple/cyan/pink palette with backdrop blur
3-column sidebar — Session context, navigation, and settings
Mobile-first responsive — Bottom nav bar, bottom sheet answer panel
Intelligent Input Handling
Auto-detects document type — Question bank, syllabus, notes, or mixed
PDF text extraction — Client-side via pdf.js (no server processing needed)
Text file support — .txt files
4 processing paths:
Question Bank → Priority classification + study plan
Syllabus → Topic extraction → AI question generation → prediction → plan
Notes → Same as syllabus path
Mixed → Extracts existing questions AND generates new ones from topics
Answer Panel (Slide-in)
3 answer modes: Focused (deep), Quick (summary), Exam Ready (structured)
Diagram fetching — SerpAPI Google Images integration
Copy to clipboard
Bottom sheet on mobile
Predicted Exam Questions
AI predicts which questions are most likely to appear on the exam
Based on topic frequency, foundational concepts, and exam patterns
Focus Timer
Pomodoro-style 25-minute sessions with SVG ring
Question queue — Click to jump between questions
Auto-breaks — 5-minute breaks between sessions
Progress tracking — Visual completion bar
Ask Anything
Chat-style interface for any topic
Same 3 answer modes
Inline diagrams
One-click "Add to Timer"
Project Structure
plain
Copy
examcram/
├── app.py                    # Flask routes (10 endpoints)
├── requirements.txt          # Dependencies
├── .env.example              # Environment variables template
├── README.md                 # This file
├── utils/
│   ├── __init__.py
│   ├── ai_handler.py         # Gemini API with model fallback chain
│   ├── input_intelligence.py # Document classification, syllabus parsing, question generation, prediction
│   ├── priority.py           # Keyword-based priority classification + time estimation
│   └── image_fetcher.py      # SerpAPI Google Images integration
└── templates/
    └── index.html            # Complete single-page frontend (97 KB)
API Endpoints
Table
Endpoint	Method	Description
/	GET	Serves the frontend
/analyse-input	POST	Classifies document type (qb/syllabus/notes/mixed)
/parse-syllabus	POST	Extracts units and topics from syllabus
/generate-questions	POST	Generates exam questions from syllabus units
/predict-exam	POST	Predicts most likely exam questions
/generate-plan	POST	Creates day-wise study plan with priorities
/generate-answer	POST	Generates AI answer in 3 modes
/get-images	POST	Fetches diagram images for a topic
/save-queue	POST	Saves timer queue (IP-based)
/get-queue	GET	Retrieves saved timer queue
/clear-queue	POST	Clears timer queue
Setup
1. Install dependencies
bash
Copy
pip install -r requirements.txt
2. Configure environment variables
bash
Copy
cp .env.example .env
# Edit .env and add your API keys
Required:
GEMINI_API_KEY — Get from Google AI Studio
SERPAPI_KEY — Get from SerpAPI (optional, for diagrams)
3. Run
bash
Copy
python app.py
# or
flask run
The app runs on http://localhost:5000 by default.
Gemini Model Fallback Chain
If one model fails, the system automatically tries the next:
gemini-3.1-flash-lite-preview
gemini-2.5-flash-lite-preview-06-17
gemini-2.5-flash
gemini-3.0-flash
gemini-2.5-pro
gemma-3-27b-it
Design Tokens
Table
Token	Value
Background	#080810
Surface	rgba(14,14,26,0.5)
Card	rgba(19,19,31,0.65)
Border	rgba(255,255,255,0.08)
Purple	#9333ea
Cyan	#06b6d4
Pink	#ec4899
Green	#10b981
Font UI	Inter
Font Mono	JetBrains Mono
License
MIT
