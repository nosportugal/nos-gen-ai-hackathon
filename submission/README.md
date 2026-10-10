# 🕵️‍♂️ The *-Files: Anonymisation Pipeline

**Team Submission for NOS - JunctionX Lisbon 2026**

This repository contains our complete, end-to-end solution for the NOS Generative AI Hackathon. We have built an LLM-based system that identifies and masks sensitive/personal data in a document while perfectly preserving the document's meaning and exact formatting.

## 💡 What it Does

Our pipeline takes a PDF document containing personal data and redacts sensitive information across 5 categories: Identity, Contact/Location, Official/Financial IDs, Health, and Sensitive Social Data.

**Our Core Philosophy: "LLMs find, Python masks."**
To guarantee zero hallucinated changes to layout, spacing, or accents, we decoupled the detection from the redaction:
1. **Gemini** is used strictly as a reasoning engine to identify *what* to mask and on what line.
2. **Plain Python** executes the actual text replacement, swapping each sensitive word for a single asterisk (`*`) while perfectly preserving the surrounding whitespace, punctuation, and line breaks.

## ✨ Core Features (The 4 Pillars)

1. **Detect (Context-Aware):** A multi-agent Gemini architecture (Detector, Context Checker, and Reviewer) reasons about the text. It doesn't just look for formats like emails; it understands context to drop false alarms and catch hidden identifiers.
2. **Mask:** Deterministic masking replaces each sensitive word with one `*` (e.g., `Ana Correia` becomes `* *`, and `Flores,` becomes `*,`).
3. **Preserve:** Using PyMuPDF, the original PDF layout, line breaks, and accents are perfectly mapped to plain text. Empty lines and trailing spaces are cleanly removed as requested.
4. **Validate (Human-in-the-loop):** We built a complete validation flow. The system outputs an explainability report (`outputs/report.md`), and our web API allows a frontend to present false positives/negatives to a user for instant, zero-LLM-cost re-masking.

## 🏗️ Architecture

Our solution orchestrates a multi-agent flow with at most **3 API calls per document** (highly optimized for cost and speed):

* **Extraction:** `anonymizer/extract.py` extracts text from the raw PDF.
* **Detector Agent:** Gemini scans the text to find sensitive data and categorizes it.
* **Context Checker Agent:** Gemini evaluates surrounding text to ensure no residual context gives the person away.
* **First Masking Pass:** `anonymizer/masking.py` applies the deterministic rule.
* **Reviewer Agent:** Gemini reads the *already-masked* text to spot any sensitive data leaks.
* **Final Masking & Output:** A final Python pass outputs `submission.txt` and `outputs/report.md`.

*(For detailed design decisions, please see `submission/docs/design.md`)*

## ⚙️ Setup Instructions

### 1. Prerequisites
* Python 3.10+
* A Google Gemini API Key ([Get one here](https://aistudio.google.com/))

### 2. Installation
Clone your team's fork and navigate to the submission folder:
```bash
git clone https://github.com/<your-account>/nos-gen-ai-hackathon.git
cd nos-gen-ai-hackathon/submission
```

Create and activate a virtual environment:
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

Install dependencies:
```bash
pip install -r requirements.txt
```

### 3. Environment Variables
Create a `.env` file inside the `submission/` directory:
```env
GEMINI_API_KEY=your_api_key_here
MAIN_MODEL=gemini-1.5-flash
DATA_GEN_MODEL=gemini-1.5-flash
VALIDATION_MODEL=gemini-1.5-flash
```

## 🚀 Usage

Run these commands from inside the `submission/` folder.

**1. Generate the Final Submission:**
Runs the full pipeline, reads the source PDF, and writes the masked text to `submission.txt` alongside the findings log in `outputs/report.md`.
```bash
python run.py
```

**2. Evaluate against Synthetic Data:**
Compares our pipeline's output with a known correct version to calculate precision, recall, and F1 scores.
```bash
python -m evaluate.score
```

**3. Run Test Suite:**
Runs our robust suite of 81 automated tests to ensure determinism in our masking logic and agent parsing.
```bash
pytest tests/
```

## 🌐 Running the API & Frontend (Optional Validation Step)

For the human-in-the-loop validation demo:
1. Start the backend API: `python -m api.main` (runs on `localhost:8000`)
2. Connect the Lovable frontend.
3. The UI will call `POST /anonymize` to process the document and display the `report.md` JSON.
4. Users can toggle false positives, which triggers `POST /remask` for an instant Python-only update.

## 📚 Open-Source Libraries Used

* **Google Generative AI SDK:** For seamless integration with Gemini models.
* **PyMuPDF (fitz):** Selected for its high-fidelity text extraction capabilities, ensuring PDF layout maps perfectly to plain text.
* **pytest:** For our extensive unit and integration testing.
* **flake8:** To ensure our codebase remains clean and adheres to PEP-8 standards.
* **FastAPI:** (Optional) For serving the validation UI endpoints.

---
*Built for JunctionX Lisbon 2026 by João Henriques, Rogério Soares, and Salvador Antunes.*
