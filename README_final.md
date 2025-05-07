# PDF Anonymization with Google Gemini (Nos Gen AI Hackathon)

A step-by-step Jupyter Notebook pipeline that extracts text from PDFs, cleans it, and uses Google’s Gemini LLM to redact sensitive information according to RGPD. Ideal for healthcare documents, clinical reports, or any privacy-critical text.

## 🚀 Features

- PDF text extraction (PyMuPDF) with optional OCR fallback (Tesseract)  
- Unicode normalization and special-character removal  
- Chunking large documents for LLM context limits  
- Prompt engineering for precise RGPD-compliant redaction  
- REST call to Gemma `generateContent` endpoint  
- Markdown-friendly formatting of the redacted output  

## 🔧 Prerequisites

- Python 3.8+  
- Git CLI  
- A Google Cloud API key with GenAI permissions in `API_KEY`  
- (Windows only) Tesseract OCR installed and on your PATH  
