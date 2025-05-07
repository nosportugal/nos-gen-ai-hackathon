from flask import Flask, request, send_file, render_template_string
import os
from werkzeug.utils import secure_filename
import fitz  # PyMuPDF
import unicodedata
import re

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

class PDFTextExtractor:
    def __init__(self, pdf_path):
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        self.pdf_path = pdf_path
        self.raw_text = None
        self.cleaned_text = None

    def extract_text(self):
        if self.raw_text is None:
            text_list = []
            with fitz.open(self.pdf_path) as doc:
                for page in doc:
                    text_list.append(page.get_text())
            self.raw_text = ''.join(text_list)
        return self.raw_text

    def clean_text(self):
        if self.cleaned_text is None:
            if self.raw_text is None:
                self.extract_text()
            text = unicodedata.normalize("NFD", self.raw_text)
            text = text.encode("ascii", "ignore").decode("utf-8")
            text = re.sub(r"[^a-zA-Z0-9\s]", "", text)
            text = re.sub(r"\s+", " ", text)
            self.cleaned_text = text.strip()
        return self.cleaned_text

@app.route('/')
def index():
    return render_template_string('''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Upload PDF</title>
</head>
<body>
    <h1>Upload a PDF to Extract Text</h1>
    <form action="/upload" method="post" enctype="multipart/form-data">
        <input type="file" name="file" accept=".pdf">
        <input type="submit" value="Upload">
    </form>
</body>
</html>
''')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return "No file part", 400
    file = request.files['file']
    if file.filename == '':
        return "No selected file", 400
    if file and file.filename.endswith('.pdf'):
        filename = secure_filename(file.filename)
        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(pdf_path)
        
        extractor = PDFTextExtractor(pdf_path)
        extractor.extract_text()
        extractor.clean_text()
        
        txt_filename = filename.replace('.pdf', '.txt')
        txt_path = os.path.join(app.config['UPLOAD_FOLDER'], txt_filename)
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(extractor.cleaned_text)
        
        return send_file(txt_path, as_attachment=True)
    else:
        return "Invalid file type. Please upload a PDF.", 400

if __name__ == '__main__':
    app.run(debug=True)