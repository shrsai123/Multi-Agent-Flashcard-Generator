# CardCraft: Multi-Agent Flashcard Generation System

CardCraft is a **teacher-in-the-loop flashcard generation app** that turns PDFs into study decks using a multi-stage AI pipeline. The project combines **content-aware chunking**, **LLM-based flashcard generation**, **LLM quality scoring**, **teacher review**, **FAISS-backed few-shot learning**, and **SM-2 spaced repetition** in a single **Streamlit** application. The public repository contains a Streamlit app (`app.py`), agent modules under `agents/`, core logic under `core/`, a FAISS store, providers, and deck/eval folders.

## Why this project?
Spaced repetition is effective, but many students avoid it because making high-quality cards takes effort. CardCraft reduces that setup friction by letting AI draft cards while keeping **human review and edit control** in the loop.

## What the app does
- Upload a PDF and extract text using native PDF parsing, with OCR fallback support in the content extraction module.
- Detect whether the source looks like **theory, code, math, or mixed** content and chunk it differently by type.
- Generate flashcards with **Bloom’s taxonomy guidance** and retrieve teacher-approved examples from **FAISS** as few-shot context.
- Run a **quality check** that scores cards on:
  - groundedness
  - clarity
  - uniqueness
  - difficulty calibration
- Route cards by score:
  - **>= 0.80** → auto-approve
  - **0.50–0.79** → human review
  - **< 0.50** → auto-reject
- Let teachers approve, edit, or reject cards, then store edits back into FAISS as future gold examples.
- Publish a finalized deck for students to study.
- Support student study mode with **SM-2 spaced repetition**, pre/post tests, and evaluation logging.

## Pipeline overview
1. **Content Extraction**  
   The extraction stage detects content type and applies content-aware chunking:
   - code → function/class boundaries
   - math → theorem/definition/proof-style boundaries
   - prose/theory → recursive character chunking

2. **Flashcard Generation**  
   The generation stage uses:
   - prompt engineering
   - Bloom’s taxonomy guidance
   - FAISS-retrieved teacher “gold” examples as few-shot context
   - JSON-constrained output for downstream parsing

3. **Quality Check**  
   The quality judge scores each flashcard on four dimensions:
   - groundedness × 0.4
   - clarity × 0.3
   - uniqueness × 0.2
   - difficulty calibration × 0.1

4. **Teacher Review**  
   Teachers can approve, edit, or reject cards through the app UI. Edited cards are stored back into FAISS to improve later runs.

## FAISS learning loop
A key idea in CardCraft is the **few-shot learning loop**:
- a teacher edits a card
- the edit is stored as a FAISS embedding
- future runs retrieve top-k similar gold examples
- prompts become richer over time
- generation quality can improve as the gold library grows

## Methodology and evaluation
CardCraft evaluates the system at three levels:

### 1) System-level
Logged for each run:
- quality scores
- routing decisions
- teacher actions
- pipeline efficiency

### 2) Learning process
Tracked during study:
- first-attempt recall
- completion rate
- review behavior
- session duration

### 3) Learning outcomes
Measured with:
- high-vs-low quality recall comparisons
- pre-test to post-test learning gain

The methodology described for the project includes:
- few-shot prompt engineering
- semantic/content-aware chunking
- SM-2 spaced repetition
- evaluation using composite quality, review effort, learning gain, and survey feedback

## Tech stack
- **Frontend:** Streamlit
- **Orchestration:** LangGraph
- **LLM providers:** Gemini and Hugging Face / Llama support
- **Vector store:** FAISS
- **Embeddings / retrieval:** sentence-transformers + FAISS tooling
- **PDF parsing:** pypdf, pdfplumber, pdf2image, pytesseract
- **Core Python stack:** pydantic, requests, python-dotenv

## Repository structure
```text
Multi-Agent-Flashcard-Generator/
├── .devcontainer/
├── .streamlit/
├── agents/
├── core/
├── eval_logs/
├── faiss_db/
├── providers/
├── published_decks/
├── app.py
├── cloud_save.py
├── requirements.txt
├── vector_store.py
└── .gitignore
```

## Installation
### 1) Clone the repo
```bash
git clone https://github.com/shrsai123/Multi-Agent-Flashcard-Generator.git
cd Multi-Agent-Flashcard-Generator
```

### 2) Create a virtual environment
```bash
python -m venv .venv
source .venv/bin/activate
```

On Windows:
```bash
.venv\Scripts\activate
```

### 3) Install dependencies
```bash
pip install -r requirements.txt
```

## Environment variables
Create a `.env` file in the project root.

### Required / common
```env
TEACHER_PASSWORD=your_teacher_password
STUDENT_PASSWORD=your_student_password
```

### Gemini
```env
GEMINI_API_KEY=your_gemini_key
```

You can also use:
```env
GOOGLE_API_KEY=your_google_api_key
```

### Hugging Face
```env
HF_TOKEN=your_huggingface_token
```

The app supports Gemini and Hugging Face providers through `providers/llm_provider.py`.

### Optional webhook for logging
```env
WEBHOOK_URL=https://your-webhook-url-here
```

If configured, `cloud_save.py` can POST evaluation and survey payloads to an external webhook.

## Running the app
```bash
python -m streamlit run app.py
```

Then open the local URL shown by Streamlit in your browser.

## App flow
### Teacher flow
1. Unlock teacher mode with the teacher password.
2. Upload a PDF.
3. Run the pipeline.
4. Review, edit, approve, or reject cards.
5. Publish the deck.
6. Store teacher edits as gold examples for future runs.

### Student flow
1. Enter student mode.
2. Load the published deck.
3. Study cards with flip-card interaction and SM-2 review scheduling.
4. Complete pre/post checks and optional survey.
5. Export or continue study.

## Current limitations
- LLM quota limits can affect generation and scoring for large documents or free-tier API usage.
- AI-based quality scoring can be circular if the generator and judge use the same model family.
- Longitudinal evaluation of the FAISS feedback loop needs more repeated sessions and larger samples.

## Future improvements
- stronger batching and retry logic for large textbooks
- more robust OCR handling for scanned PDFs
- validated trust scales and more human-rated quality labels
- student edit loops feeding back into FAISS
- richer analytics dashboards for study outcomes

## Credits
Developed as **CardCraft: Multi-Agent Flashcard Generation System with Teacher-in-the-Loop** by:
- Yashwanth Reddy Vutukoori
- Shreyas Sai Raman
- Umar Javeed Altaf


